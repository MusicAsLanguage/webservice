from pathlib import Path
import sys
import sysconfig
import tomllib

import yaml


WORKFLOWS = Path(__file__).resolve().parents[1] / ".github" / "workflows"
PYTHON_VERSION = (3, 14)


def read_workflow(name):
    # BaseLoader preserves GitHub Actions' YAML 1.2 "on" key as a string.
    return yaml.load((WORKFLOWS / name).read_text(), Loader=yaml.BaseLoader)


def test_deployments_depend_on_checks():
    for name, trigger in (("workflow.yml", "push"), ("workflow-test.yml", "pull_request")):
        workflow = read_workflow(name)
        assert trigger in workflow["on"]
        assert workflow["jobs"]["checks"]["uses"] == "./.github/workflows/checks.yml"
        assert workflow["jobs"]["build"]["needs"] == "checks"
        assert "always()" not in workflow["jobs"]["build"].get("if", "")


def test_quality_gate_requires_lint_both_databases_and_container_build():
    workflow = read_workflow("checks.yml")
    assert "workflow_call" in workflow["on"]
    jobs = workflow["jobs"]
    assert jobs["tests"]["strategy"]["matrix"]["database"] == ["mock", "mongodb"]
    assert jobs["gate"]["needs"] == ["lint", "tests", "container"]
    assert jobs["gate"]["if"] == "${{ always() }}"
    test_steps = [step.get("run", "") for step in jobs["tests"]["steps"]]
    assert any("pytest --cov" in step for step in test_steps)
    assert any("ruff check ." == step.get("run") for step in jobs["lint"]["steps"])
    gate_step = jobs["gate"]["steps"][0]
    assert gate_step["env"]["CONTAINER_RESULT"] == "${{ needs.container.result }}"
    assert 'test "$CONTAINER_RESULT" = success' in gate_step["run"]


def test_container_gate_builds_image_and_imports_real_speech_dependencies():
    container = read_workflow("checks.yml")["jobs"]["container"]
    commands = "\n".join(step.get("run", "") for step in container["steps"])
    assert "docker build --tag mal-service:ci ." in commands
    assert f"assert sys.version_info[:2] == {PYTHON_VERSION}" in commands
    assert "assert not sysconfig.get_config_var('Py_GIL_DISABLED')" in commands
    assert "--entrypoint python mal-service:ci -m pip check" in commands
    assert 'docker run --rm --entrypoint python mal-service:ci -c "import whisper; import app"' in commands
    assert "audio = np.zeros(16000, dtype=np.float32)" in commands
    assert "mel = whisper.log_mel_spectrogram(audio)" in commands
    assert "assert tuple(mel.shape) == (80, 100)" in commands
    assert "assert mel.isfinite().all()" in commands
    assert "--entrypoint ffmpeg mal-service:ci -version" in commands
    assert "--entrypoint gunicorn mal-service:ci --version" in commands
    assert "secrets." not in commands


def test_container_gate_serves_http_through_production_entrypoint():
    container = read_workflow("checks.yml")["jobs"]["container"]
    smoke = next(
        step["run"] for step in container["steps"]
        if step.get("name") == "Smoke-test Gunicorn HTTP startup"
    )
    assert "docker run --detach --name mal-service-smoke" in smoke
    assert "--entrypoint" not in smoke
    assert "--env APP_ENV=test" in smoke
    assert "--env MONGODB_SETTINGS=mongodb://127.0.0.1:27017/mal_runtime_smoke" in smoke
    assert "curl --fail" in smoke
    assert "--retry-connrefused --retry-all-errors" in smoke
    assert "--retry-max-time 30 --max-time 5" in smoke
    assert "http://127.0.0.1:8000/resetPwd/runtime-smoke" in smoke
    assert """grep -F 'value="runtime-smoke"'""" in smoke
    assert "trap 'docker logs mal-service-smoke; docker rm --force mal-service-smoke' EXIT" in smoke


def test_runtime_is_supported_standard_cpython():
    assert sys.implementation.name == "cpython"
    assert sys.version_info[:2] == PYTHON_VERSION
    assert not sysconfig.get_config_var("Py_GIL_DISABLED")


def test_development_ci_and_container_use_supported_python():
    root = WORKFLOWS.parents[1]
    version = ".".join(map(str, PYTHON_VERSION))
    assert (root / "Dockerfile").read_text().splitlines()[0] == f"FROM python:{version}-slim"
    config = tomllib.loads((root / "pyproject.toml").read_text())
    assert config["tool"]["ruff"]["target-version"] == "py" + version.replace(".", "")
    setup_script = (root / "setup_venv.bat").read_text()
    assert f"py -{version} -m venv .venv" in setup_script
    assert f"sys.version_info[:2] == {PYTHON_VERSION}" in setup_script
    assert "not sysconfig.get_config_var('Py_GIL_DISABLED')" in setup_script
    readme = (root / "README.md").read_text()
    for command in (
        f"py -{version} -m venv .venv",
        f"python{version} -m venv .venv",
        f"python:{version}-slim",
    ):
        assert command in readme
    jobs = read_workflow("checks.yml")["jobs"]
    for name in ("lint", "tests"):
        setup = [
            step for step in jobs[name]["steps"]
            if step.get("uses", "").startswith("actions/setup-python@")
        ]
        assert len(setup) == 1
        assert setup[0]["with"]["python-version"] == version


def test_untrusted_prs_run_checks_without_deployment_secrets():
    workflow = read_workflow("workflow-test.yml")
    assert "secrets" not in workflow["jobs"]["checks"]
    guard = workflow["jobs"]["build"]["if"]
    assert "github.event.pull_request.head.repo.full_name == github.repository" in guard
    assert "dependabot[bot]" in guard
