from datetime import timedelta
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from flask_jwt_extended import create_access_token

from database.models import User
from database import utils


def reset_token(app, user_id, **claims):
    with app.app_context():
        return create_access_token(user_id, additional_claims={
            "purpose": "password_reset", "version": 0, **claims,
        })


def test_password_reset_is_single_use_and_revokes_sessions(app, client, login):
    headers, tokens, user_id = login()
    token = reset_token(app, user_id)
    payload = {"reset_token": token, "password": "new-password"}
    assert client.post("/api/auth/resetPwd", json=payload).status_code == 200
    user = User.objects.get(id=user_id)
    assert user.check_password("new-password")
    assert not user.check_password("test-password")
    assert user.auth_version == 1
    assert client.post("/api/auth/resetPwd", json=payload).status_code == 403
    assert client.get("/api/user/getUserScore", headers=headers).status_code == 401
    assert client.post("/api/auth/tokenRefresh", headers={
        "Authorization": "Bearer " + tokens["refresh_token"],
    }).status_code == 401
    assert client.post("/api/auth/login", json={
        "email": user.email, "password": "new-password",
    }).status_code == 200


def test_reset_token_is_not_a_session_token(app, client, login):
    _, _, user_id = login()
    token = reset_token(app, user_id)
    assert client.get(
        "/api/user/getUserScore", headers={"Authorization": "Bearer " + token}
    ).status_code == 401


def test_session_tokens_cannot_reset_password(client, login):
    _, tokens, user_id = login()
    for token in tokens.values():
        assert client.post("/api/auth/resetPwd", json={
            "reset_token": token, "password": "new-password",
        }).status_code == 403
    assert User.objects.get(id=user_id).check_password("test-password")


@pytest.mark.parametrize("password", ["short", "", "x" * 101, None])
def test_reset_validates_before_mutating(app, client, login, password):
    _, _, user_id = login()
    assert client.post("/api/auth/resetPwd", json={
        "reset_token": reset_token(app, user_id), "password": password,
    }).status_code == 400
    assert User.objects.get(id=user_id).check_password("test-password")


def test_invalid_and_expired_reset_tokens(app, client, login):
    _, _, user_id = login()
    with app.app_context():
        expired = create_access_token(
            user_id, expires_delta=timedelta(seconds=-1),
            additional_claims={"purpose": "password_reset", "version": 0},
        )
    for token in ("invalid", expired):
        assert client.post("/api/auth/resetPwd", json={
            "reset_token": token, "password": "new-password",
        }).status_code == 403


def test_form_failure_does_not_flash_success(client):
    response = client.post("/resetPwd", data={"password": "new-password", "reset_token": "invalid"})
    assert b"Invalid token" in response.data
    assert b"Password has been reset!" not in response.data
    assert client.post("/resetPwd", data={}).status_code == 200


def test_form_success(app, client, login):
    _, _, user_id = login()
    token = reset_token(app, user_id)
    assert client.get("/resetPwd/" + token).status_code == 200
    response = client.post("/resetPwd", data={"password": "new-password", "reset_token": token})
    assert b"Password has been reset!" in response.data
    assert User.objects.get(id=user_id).check_password("new-password")


def test_forgot_password_handles_missing_user_and_provider_failure(client, case, login):
    assert client.post("/api/auth/forgotPwd", json={"email": "absent@example.test"}).status_code == 400
    login()
    response = client.post("/api/auth/forgotPwd", json={"email": "jane@example.test"})
    assert response.status_code == 200
    assert "https://example.test/resetPwd/" in case.mail.call_args.kwargs["text_body"]
    case.mail.side_effect = RuntimeError("mail unavailable")
    assert client.post("/api/auth/forgotPwd", json={"email": "jane@example.test"}).status_code == 500


def test_confirmation_failure_does_not_undo_password_reset(app, client, case, login, caplog):
    _, _, user_id = login()
    case.mail.side_effect = RuntimeError("mail unavailable")
    assert client.post("/api/auth/resetPwd", json={
        "reset_token": reset_token(app, user_id), "password": "new-password",
    }).status_code == 200
    assert User.objects.get(id=user_id).check_password("new-password")
    assert "confirmation email failed" in caplog.text


def test_concurrent_reset_token_reuse_has_exactly_one_winner(app, login, monkeypatch):
    _, _, user_id = login()
    token = reset_token(app, user_id)
    original = utils.generate_password_hash
    barrier = Barrier(2)

    def synchronize_hash(password):
        hashed = original(password)
        barrier.wait(timeout=10)
        return hashed

    monkeypatch.setattr(utils, "generate_password_hash", synchronize_hash)

    def reset(_):
        with app.test_client() as client:
            return client.post("/api/auth/resetPwd", json={
                "reset_token": token, "password": "new-password",
            }).status_code

    with ThreadPoolExecutor(max_workers=2) as executor:
        assert sorted(executor.map(reset, range(2))) == [200, 403]
    assert User.objects.get(id=user_id).auth_version == 1
