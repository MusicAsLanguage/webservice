import os
import subprocess
import sys
from unittest.mock import Mock, patch

import pytest
from mongoengine import get_db

from app import create_app
from config import load_config
from tests.base_case import BaseCase


def test_import_does_not_connect_or_import_whisper():
    result = subprocess.run([
        sys.executable, "-c",
        "import sys; import app; from mongoengine.connection import _connections; "
        "assert not _connections; assert 'whisper' not in sys.modules; "
        "assert 'torch' not in sys.modules",
    ], capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr


def test_configuration_is_read_at_factory_time(monkeypatch):
    monkeypatch.setenv("ADMIN_USERS", "first@example.test")
    assert load_config("test")["ADMIN_USERS"] == "first@example.test"
    monkeypatch.setenv("ADMIN_USERS", "second@example.test")
    assert load_config("test")["ADMIN_USERS"] == "second@example.test"


def test_unknown_environment_fails_clearly():
    with pytest.raises(ValueError, match="APP_ENV"):
        create_app("typo")


@pytest.mark.parametrize("key", ["SECRET_KEY", "JWT_SECRET_KEY", "MONGODB_SETTINGS", "PUBLIC_BASE_URL"])
def test_production_requires_explicit_configuration(monkeypatch, key):
    settings = {
        "SECRET_KEY": "s" * 32,
        "JWT_SECRET_KEY": "j" * 32,
        "MONGODB_SETTINGS": "mongodb://localhost/service",
        "PUBLIC_BASE_URL": "https://example.test",
    }
    for name, value in settings.items():
        monkeypatch.setenv(name, value)
    monkeypatch.delenv(key)
    with patch("app.initialize_db") as connect:
        with pytest.raises(ValueError, match=key):
            create_app("prod")
        connect.assert_not_called()


def test_readiness_and_transcriber_injection(app, client, case):
    assert app.extensions["transcriber"] is case.transcriber
    assert client.get("/health/ready").json == {"status": "ready"}


def test_readiness_fails_when_database_is_unavailable(client, monkeypatch):
    monkeypatch.setattr("app.get_db", Mock(side_effect=RuntimeError("offline")))
    assert client.get("/health/ready").status_code == 500


def test_cleanup_refuses_database_not_owned_by_fixture(case):
    original = case.database_name
    case.database_name = "not-owned"
    try:
        with pytest.raises(RuntimeError, match="Refusing"):
            case.clean_database()
        assert get_db().name == original
    finally:
        case.database_name = original


def test_suite_fixtures_reconnect_and_ignore_application_database(monkeypatch):
    monkeypatch.setenv("MONGODB_SETTINGS", "mongodb://unreachable.invalid/production")
    names = []
    for _ in range(2):
        case = BaseCase()
        case.setUp()
        try:
            names.append(get_db().name)
            assert case.app.get("/health/ready").status_code == 200
        finally:
            assert case.doCleanups()
    assert names[0] != names[1]
    assert all(name.startswith("mal_test_") for name in names)


def test_integration_uri_must_not_name_a_database(monkeypatch):
    monkeypatch.setenv("TEST_MONGODB_URI", "mongodb://localhost/production")
    with pytest.raises(ValueError, match="must not contain a database"):
        BaseCase().setUp()


def test_ci_can_select_real_mongodb(case):
    if os.getenv("TEST_MONGODB_URI"):
        assert get_db().client.__class__.__module__.startswith("pymongo.")
    else:
        assert get_db().client.__class__.__module__.startswith("mongomock.")


def test_index_preparation_is_repeatable(app):
    runner = app.test_cli_runner()
    for _ in range(2):
        result = runner.invoke(args=["prepare-indexes"])
        assert result.exit_code == 0, result.output


def test_index_preparation_refuses_duplicates_without_deleting_data(app):
    collection = get_db()["activity_status"]
    collection.insert_many([
        {"User": "same", "ActivityId": 1, "LessonId": 1},
        {"User": "same", "ActivityId": 1, "LessonId": 1},
    ])
    result = app.test_cli_runner().invoke(args=["prepare-indexes"])
    assert result.exit_code != 0
    assert "duplicate progress keys" in result.output
    assert collection.count_documents({}) == 2
