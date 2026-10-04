import pytest

from database.models import User


@pytest.mark.parametrize("payload", [
    None, [], {}, {"email": "bad"}, {"name": "Jane", "email": "bad", "password": "123456"},
    {"name": "Jane", "email": "jane@example.test", "password": "short"},
    {"name": "Jane", "email": "jane@example.test", "password": "x" * 101},
    {"name": "Jane", "email": "jane@example.test", "password": 123456},
    {"name": "", "email": "jane@example.test", "password": "password"},
    {"name": "Jane", "email": "jane@example.test", "password": "password", "score": 100},
    {"name": "Jane", "email": "jane@example.test", "password": "password", "auth_version": 1},
])
def test_invalid_signup_does_not_create_user(client, payload):
    response = client.post("/api/auth/signup", json=payload) if payload is not None else (
        client.post("/api/auth/signup", data="null", content_type="application/json")
    )
    assert response.status_code == 400
    assert User.objects.count() == 0


@pytest.mark.parametrize("value", [-1, "100.5", 1.5, True, None, 2**63])
def test_score_rejects_invalid_values(client, login, value):
    headers, _, user_id = login()
    response = client.post("/api/user/updateUserScore", headers=headers, json={"score": value})
    assert response.status_code == 400
    assert User.objects.get(id=user_id).score == 0


@pytest.mark.parametrize("path", [
    "/api/activity/updateStatus", "/api/activity/updateSongPlayingStatus",
    "/api/user/updateUserScore", "/api/msg/send", "/api/auth/resetPwd",
])
def test_missing_fields_are_client_errors(client, login, path):
    headers, _, _ = login()
    assert client.post(path, headers=headers, json={}).status_code == 400


def test_malformed_json_and_content_type(client):
    assert client.post("/api/auth/login", data="{", content_type="application/json").status_code == 400
    assert client.post("/api/auth/login", data="not json").status_code == 415


def test_unexpected_errors_are_logged_without_exposing_details(client, login, monkeypatch, caplog):
    headers, _, _ = login()

    def fail(*args, **kwargs):
        raise RuntimeError("private database details")

    monkeypatch.setattr(User, "update", fail)
    response = client.post("/api/user/updateUserScore", headers=headers, json={"score": 1})
    assert response.status_code == 500
    assert response.json == {"message": "Something went wrong", "status": 500}
    assert "private database details" in caplog.text
