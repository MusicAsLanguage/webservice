from pathlib import Path

import yaml


WORKFLOWS = Path(__file__).resolve().parents[1] / ".github" / "workflows"


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
    assert 'docker run --rm --entrypoint python mal-service:ci -c "import whisper; import app"' in commands
    assert "--entrypoint ffmpeg mal-service:ci -version" in commands
    assert "--entrypoint gunicorn mal-service:ci --version" in commands
    assert "secrets." not in commands


def test_untrusted_prs_run_checks_without_deployment_secrets():
    workflow = read_workflow("workflow-test.yml")
    assert "secrets" not in workflow["jobs"]["checks"]
    guard = workflow["jobs"]["build"]["if"]
    assert "github.event.pull_request.head.repo.full_name == github.repository" in guard
    assert "dependabot[bot]" in guard
