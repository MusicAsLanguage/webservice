import json
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

import bcrypt
import pytest
from bson import ObjectId
from flask_jwt_extended import create_access_token, create_refresh_token, decode_token

from database.models import User
from tests.test_legacy_contracts import bearer
from tests.test_reset_password import reset_token


@pytest.mark.parametrize("password", [
    "x" * 72, "x" * 73, "x" * 100, "\u00e9" * 60, "\U0001f600" * 100, " " * 6,
])
def test_new_and_reset_passwords_compare_the_entire_legacy_character_range(app, client, password):
    payload = {"name": "Jane", "email": "jane@example.test", "password": password}
    signup = client.post("/api/auth/signup", json=payload)
    assert signup.status_code == 200
    user_id = signup.json["id"]
    user = User.objects.get(id=user_id)
    assert user.password.startswith("$bcrypt-sha256$")
    assert user.check_password(password)
    assert not user.check_password(password[:-1] + "y")
    login = client.post("/api/auth/login", json=payload)
    assert login.status_code == 200
    with app.app_context():
        identity = json.loads(decode_token(login.json["token"])["sub"])
    assert identity["password"] == ""
    assert not {"auth_version", "active_writes", "deletion_started", "password_scheme"} & identity.keys()
    changed = password[:-1] + "z"
    assert client.post("/api/auth/resetPwd", json={
        "reset_token": reset_token(app, user_id), "password": changed,
    }).status_code == 200
    user.reload()
    assert user.check_password(changed) and not user.check_password(password)
    assert client.post("/api/auth/login", json={**payload, "password": password}).status_code == 401


@pytest.mark.parametrize("password", ["x", " " * 8, "x" * 100, "\u00e9" * 37, "\U0001f600" * 30])
def test_historical_bcrypt_hashes_and_whitespace_credentials_still_verify(app, client, password):
    user_id = ObjectId()
    hashed = bcrypt.hashpw(password.encode("utf-8")[:72], bcrypt.gensalt(rounds=4)).decode()
    User._get_collection().insert_one({
        "_id": user_id, "name": "Legacy", "email": "legacy@example.test", "password": hashed, "score": 0,
    })
    payload = {"email": "legacy@example.test", "password": password}
    response = client.post("/api/auth/login", json=payload)
    assert response.status_code == 200
    assert client.post("/api/auth/login", json={
        **payload, "password": "!" + password[1:],
    }).status_code == 401
    assert User.objects.get(id=user_id).password == hashed
    if len(password.encode("utf-8")) > 72:
        assert User.objects.get(id=user_id).check_password(password + "suffix")
    assert client.post("/api/auth/resetPwd", json={
        "reset_token": reset_token(app, str(user_id)), "password": "new-password",
    }).status_code == 200
    assert client.get("/api/user/getUserScore", headers=bearer(response.json["token"])).status_code == 401


def test_unicode_passwords_are_not_normalized_or_prefix_compared(client):
    payload = {"name": "Jane", "email": "jane@example.test", "password": "\u00e9" * 40}
    assert client.post("/api/auth/signup", json=payload).status_code == 200
    assert client.post("/api/auth/login", json={**payload, "password": "e\u0301" * 40}).status_code == 401


def test_reset_never_persists_plaintext(app, client, login, monkeypatch):
    _, _, user_id = login()
    collection = User._get_collection()
    original = type(collection).update_one
    writes = []

    def observe(target, query, update, **kwargs):
        if target.name == collection.name:
            writes.append(update)
        return original(target, query, update, **kwargs)

    monkeypatch.setattr(type(collection), "update_one", observe)
    password = "\u00e9" * 80
    assert client.post("/api/auth/resetPwd", json={
        "reset_token": reset_token(app, user_id), "password": password,
    }).status_code == 200
    password_writes = [write["$set"]["password"] for write in writes if "password" in write.get("$set", {})]
    assert len(password_writes) == 1 and password_writes[0].startswith("$bcrypt-sha256$")
    assert all(password not in str(write) for write in writes)


def legacy_tokens(app, user_id):
    with app.app_context():
        return (
            create_access_token(json.dumps({"_id": {"$oid": user_id}}), fresh=True, expires_delta=False),
            create_refresh_token(user_id, expires_delta=False),
            create_access_token(user_id, expires_delta=timedelta(hours=24)),
        )


def test_legacy_session_and_reset_purposes_are_distinct_and_revocable(app, client, login):
    _, _, user_id = login()
    access, refresh, reset = legacy_tokens(app, user_id)
    assert client.get("/api/user/getUserScore", headers=bearer(access)).status_code == 200
    assert client.post("/api/auth/tokenRefresh", headers=bearer(refresh)).status_code == 200
    for token in (access, refresh):
        assert client.post("/api/auth/resetPwd", json={
            "reset_token": token, "password": "new-password",
        }).status_code == 403
    for path, method in [
        ("/api/user/getUserScore", "get"), ("/api/auth/tokenRefresh", "post"),
        ("/api/activity/updateStatus", "post"), ("/api/msg/send", "post"),
        ("/api/user/deleteUserAndData", "delete"),
    ]:
        assert getattr(client, method)(path, headers=bearer(reset)).status_code == 401
    assert client.post("/api/auth/resetPwd", json={
        "reset_token": reset, "password": "new-password",
    }).status_code == 200
    assert client.post("/api/auth/resetPwd", json={
        "reset_token": reset, "password": "another-password",
    }).status_code == 403
    assert client.get("/api/user/getUserScore", headers=bearer(access)).status_code == 401
    assert client.post("/api/auth/tokenRefresh", headers=bearer(refresh)).status_code == 401


@pytest.mark.parametrize("lifetime", [False, timedelta(hours=1), timedelta(hours=25), timedelta(seconds=-1)])
def test_only_finite_original_24_hour_links_qualify_for_legacy_reset(app, client, login, lifetime):
    _, _, user_id = login()
    with app.app_context():
        token = create_access_token(user_id, expires_delta=lifetime)
    assert client.post("/api/auth/resetPwd", json={
        "reset_token": token, "password": "new-password",
    }).status_code == 403
    assert client.get("/api/user/getUserScore", headers=bearer(token)).status_code == 401


@pytest.mark.parametrize("claims", [
    {"purpose": None}, {"purpose": "session"}, {"version": 0},
    {"purpose": "password_reset"}, {"purpose": "password_reset", "version": False},
    {"purpose": "password_reset", "version": "0"}, {"purpose": "session", "version": False},
])
def test_partial_or_ill_typed_claims_do_not_fall_back_to_legacy(app, client, login, claims):
    _, _, user_id = login()
    with app.app_context():
        token = create_access_token(user_id, expires_delta=timedelta(hours=24), additional_claims=claims)
    assert client.get("/api/user/getUserScore", headers=bearer(token)).status_code == 401
    assert client.post("/api/auth/resetPwd", json={
        "reset_token": token, "password": "new-password",
    }).status_code == 403


def test_legacy_reset_is_single_use_under_concurrent_requests(app, login):
    _, _, user_id = login()
    _, _, token = legacy_tokens(app, user_id)

    def reset(_):
        with app.test_client() as client:
            return client.post("/api/auth/resetPwd", json={
                "reset_token": token, "password": "new-password",
            }).status_code

    with ThreadPoolExecutor(max_workers=2) as executor:
        assert sorted(executor.map(reset, range(2))) == [200, 403]


def test_deleted_legacy_account_invalidates_every_token_form(app, client, login):
    headers, _, user_id = login()
    access, refresh, reset = legacy_tokens(app, user_id)
    assert client.delete("/api/user/deleteUserAndData", headers=headers).status_code == 200
    assert client.get("/api/user/getUserScore", headers=bearer(access)).status_code == 401
    assert client.post("/api/auth/tokenRefresh", headers=bearer(refresh)).status_code == 401
    assert client.post("/api/auth/resetPwd", json={
        "reset_token": reset, "password": "new-password",
    }).status_code == 403
