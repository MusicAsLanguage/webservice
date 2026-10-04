import json
from datetime import timedelta

import pytest
from flask_jwt_extended import create_access_token, decode_token

from database.models import User


def test_tokens_expire_and_do_not_contain_password_hash(app, client, login):
    headers, tokens, user_id = login()
    with app.app_context():
        access = decode_token(tokens["token"])
        refresh = decode_token(tokens["refresh_token"])
    assert access["exp"] - access["iat"] == 3600
    assert refresh["exp"] - refresh["iat"] == 30 * 24 * 3600
    assert json.loads(access["sub"])["password"] == ""
    assert "auth_version" not in json.loads(access["sub"])
    assert User.objects.get(id=user_id).check_password("test-password")
    assert client.get("/api/user/getUserScore", headers=headers).status_code == 200


@pytest.mark.parametrize("identity", ["not-an-id", "{}", "[]", '{"_id": null}'])
def test_invalid_token_identity_is_rejected(app, client, identity):
    with app.app_context():
        token = create_access_token(identity=identity)
    assert client.get(
        "/api/user/getUserScore", headers={"Authorization": "Bearer " + token}
    ).status_code == 401


def test_expired_missing_and_wrong_type_tokens(app, client, login):
    headers, tokens, user_id = login()
    with app.app_context():
        expired = create_access_token(user_id, expires_delta=timedelta(seconds=-1))
    for token in ("garbage", expired, tokens["refresh_token"]):
        response = client.get("/api/user/getUserScore", headers={"Authorization": "Bearer " + token})
        assert response.status_code == 401
    assert client.get("/api/user/getUserScore").status_code == 401
    assert client.post("/api/auth/tokenRefresh", headers=headers).status_code == 401


def test_legacy_access_identity_remains_supported(app, client, login):
    _, _, user_id = login()
    with app.app_context():
        legacy = create_access_token(identity=json.dumps({"_id": {"$oid": user_id}}))
    assert client.get(
        "/api/user/getUserScore", headers={"Authorization": "Bearer " + legacy}
    ).status_code == 200


def test_admin_membership_is_exact_and_case_insensitive(client, login):
    substring_headers, _, _ = login("User@mal.com")
    admin_headers, _, _ = login("ADMINUSER@mal.com")
    assert client.post("/api/lesson/createLessons", headers=substring_headers, json=[]).status_code == 401
    assert client.get("/clearCache", headers=substring_headers).status_code == 401
    assert client.get("/clearCache").status_code == 401
    assert client.post("/api/lesson/createLessons", headers=admin_headers, json=[]).status_code == 200
    assert client.get("/clearCache", headers=admin_headers).status_code == 200


def test_deleted_user_cannot_access_or_refresh(client, login):
    headers, tokens, _ = login()
    assert client.delete("/api/user/deleteUserAndData", headers=headers).status_code == 200
    assert client.get("/api/user/getUserScore", headers=headers).status_code == 401
    assert client.post("/api/auth/tokenRefresh", headers={
        "Authorization": "Bearer " + tokens["refresh_token"],
    }).status_code == 401
