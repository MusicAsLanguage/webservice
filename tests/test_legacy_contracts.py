import io
import json
from copy import deepcopy
from pathlib import Path

import pytest
from bson import ObjectId
from flask_jwt_extended import decode_token

from database.models import ActivityStatus, Program, SongPlayingStatus, User
from tests.test_reset_password import reset_token


CONTRACT = json.loads((Path(__file__).parent / "fixtures" / "legacy_contracts.json").read_text())


def bearer(token):
    return {"Authorization": "Bearer " + token}


def test_all_legacy_methods_and_new_readiness_are_registered(app):
    actual = {
        rule.rule: rule.methods - {"HEAD", "OPTIONS"}
        for rule in app.url_map.iter_rules() if rule.rule != "/static/<path:filename>"
    }
    expected = {path: {method} for path, method in CONTRACT["routes"].items()}
    assert actual == {**expected, "/health/ready": {"GET"}}


@pytest.mark.parametrize("path,method", CONTRACT["routes"].items())
def test_legacy_routes_keep_options_and_reject_unsupported_methods(client, path, method):
    path = path.replace("<token>", "example")
    response = client.options(path)
    assert response.status_code == 200
    assert method in response.headers["Allow"]
    response = client.patch(path)
    assert response.status_code == 405
    assert set(response.json) == {"message"}


def test_every_legacy_endpoint_success_contract(app, client, case):
    visited = set()

    def call(path, **kwargs):
        template = "/resetPwd/<token>" if path.startswith("/resetPwd/") else path
        visited.add(template)
        response = client.open(path, method=CONTRACT["routes"][template], **kwargs)
        assert response.status_code == 200, (path, response.json if response.is_json else response.data)
        return response

    payload = {"name": "Jane", "email": "jane@example.test", "password": "test-password"}
    response = call("/api/auth/signup", json={**payload, "id": "507f1f77bcf86cd799439011"})
    assert set(response.json) == {"id"}
    user_id = response.json["id"]
    assert ObjectId.is_valid(user_id)
    assert user_id != "507f1f77bcf86cd799439011"
    tokens = call("/api/auth/login", json={**payload, "score": "999", "UpdateTime": 0}).json
    assert set(tokens) == {"token", "refresh_token"}
    headers = bearer(tokens["token"])
    with app.app_context():
        identity = json.loads(decode_token(tokens["token"])["sub"])
    assert identity["_id"] == {"$oid": user_id}
    assert type(identity["UpdateTime"]["$date"]) is int
    identity["_id"], identity["UpdateTime"] = CONTRACT["user"]["_id"], CONTRACT["user"]["UpdateTime"]
    assert identity == CONTRACT["user"]
    assert set(call("/api/auth/tokenRefresh", headers=bearer(tokens["refresh_token"])).json) == {"token"}
    assert call("/api/user/getUserScore", headers=headers).json == {"score": 0}
    assert call("/api/user/updateUserScore", headers=headers, json={"score": "100"}).json == {
        "success": True,
    }
    assert call("/api/user/getUserScore", headers=headers).json == {"score": 100}
    assert call("/api/user/updateUserScore", headers=headers, json={"score": "2"}).json == {
        "success": True,
    }
    assert call("/api/user/getUserScore", headers=headers).json == {"score": 2}
    for kind, post_path, get_path, payload in [
        ("activity", "/api/activity/updateStatus", "/api/activity/getStatus",
         {"ActivityId": "1", "LessonId": "2", "CompletionStatus": "5"}),
        ("song", "/api/activity/updateSongPlayingStatus", "/api/activity/getSongPlayingStatus",
         {"SongName": "Song", "Category": "Beginner", "CompletionStatus": "5"}),
    ]:
        assert call(get_path, headers=headers).json == []
        response = call(post_path, headers=headers, json=payload)
        record_id = response.json["id"]
        assert set(response.json) == {"id"} and ObjectId.is_valid(record_id)
        records = call(get_path, headers=headers).json
        assert len(records) == 1
        record = records[0]
        assert record["_id"] == {"$oid": record_id}
        assert record["User"] == {"$ref": "user", "$id": {"$oid": user_id}}
        assert type(record["UpdateTime"]["$date"]) is int
        for field in ("_id", "User", "UpdateTime"):
            record[field] = CONTRACT[kind][field]
        assert record == CONTRACT[kind]
        again = call(post_path, headers=headers, json=payload)
        assert again.json == {"id": record_id}
    assert set(call("/api/msg/send", headers=headers, json={"Msg": "Hello"}).json) == {"id"}
    assert call("/api/user/speechScore", headers=headers, data={
        "speech_text": "hello", "music_file": (io.BytesIO(b"audio"), "audio.wav"),
    }).json == {"text": "hello", "score": 10}
    assert User.objects.get(id=user_id).score == 12
    User.objects(id=user_id).update_one(set__email="AdminUser@mal.com")
    assert call("/api/lesson/getLessons").json == []
    assert call("/api/lesson/createLessons", headers=headers, json=[
        {"_id": "1", "Name": "Replacement"},
    ]).json == {"id": "[1]"}
    assert call("/api/lesson/getLessons").json == [CONTRACT["program_replacement"]]
    cleared = call("/clearCache", headers=headers)
    assert cleared.data == b"Cache cleared!" and cleared.mimetype == "application/json"
    assert call("/api/auth/forgotPwd", json={"email": "AdminUser@mal.com", "name": "Ignored"}).json == {
        "status": "Password reset email has been sent to AdminUser@mal.com",
    }
    token = reset_token(app, user_id)
    form = call("/resetPwd/" + token)
    assert form.mimetype == "text/html" and token.encode() in form.data
    assert call("/api/auth/resetPwd", json={
        "reset_token": token, "password": "new-password", "email": "ignored@example.test",
    }).json == {"status": "Password reset was successful!"}
    token = reset_token(app, user_id, version=1)
    assert b"Password has been reset!" in call("/resetPwd", data={
        "reset_token": token, "password": "final-password",
    }).data
    tokens = call("/api/auth/login", json={
        "email": "AdminUser@mal.com", "password": "final-password",
    }).json
    assert call("/api/user/deleteUserAndData", headers=bearer(tokens["token"])).json == {"success": True}
    assert visited == set(CONTRACT["routes"])
    assert client.get("/health/ready").json == {"status": "ready"}


@pytest.mark.parametrize("value,expected", [
    ("100", 100), (" +0007 ", 7), (7.0, 7), (0, 0), ("0", 0),
    (str(2**63 - 1), 2**63 - 1),
])
def test_safe_legacy_score_encodings(client, login, value, expected):
    headers, _, _ = login()
    assert client.post("/api/user/updateUserScore", headers=headers, json={
        "score": value, "User": "untrusted", "UpdateTime": {"$date": 0},
    }).json == {"success": True}
    assert client.get("/api/user/getUserScore", headers=headers).json == {"score": expected}


@pytest.mark.parametrize("value", ["1.5", "1e3", "NaN", "1_000", "", True, -1, 1.5, 2**63,
                                        "9" * 5000, float("inf"), float("nan"), float(2**53)])
def test_numeric_boundaries_reject_ambiguous_or_unsafe_encodings(client, login, value):
    headers, _, _ = login()
    for path, payload in [
        ("/api/user/updateUserScore", {"score": value}),
        ("/api/activity/updateStatus", {"ActivityId": value, "LessonId": 1, "CompletionStatus": 1}),
        ("/api/activity/updateSongPlayingStatus", {
            "SongName": "Song", "Category": "Beginner", "CompletionStatus": 1, "Repeats": value,
        }),
    ]:
        assert client.post(path, headers=headers, json=payload).status_code == 400
    assert ActivityStatus.objects.count() == SongPlayingStatus.objects.count() == 0


@pytest.mark.parametrize("kind,model,post_path,get_path", [
    ("activity", ActivityStatus, "/api/activity/updateStatus", "/api/activity/getStatus"),
    ("song", SongPlayingStatus, "/api/activity/updateSongPlayingStatus", "/api/activity/getSongPlayingStatus"),
])
def test_serialized_progress_metadata_never_controls_ownership_or_timestamp(
    client, login, kind, model, post_path, get_path,
):
    headers, _, user_id = login()
    other_headers, _, _ = login("other@example.test")
    payload = deepcopy(CONTRACT[kind])
    payload["id"] = "507f1f77bcf86cd799439099"
    payload["Repeats"] = "2"
    response = client.post(post_path, headers=headers, json=payload)
    assert response.status_code == 200
    assert response.json["id"] not in {payload["id"], payload["_id"]["$oid"]}
    saved = model.objects.first()
    assert str(saved.User.id) == user_id and saved.Repeats == 2
    assert saved.UpdateTime.year != 2020
    assert client.get(get_path, headers=other_headers).json == []
    assert client.post(post_path, headers=headers, json=payload).json == response.json


def test_song_category_can_be_omitted_only_on_update(client, login):
    headers, _, _ = login()
    payload = {"SongName": "Song", "CompletionStatus": "5"}
    path = "/api/activity/updateSongPlayingStatus"
    assert client.post(path, headers=headers, json=payload).status_code == 400
    first = client.post(path, headers=headers, json={**payload, "Category": "Beginner"})
    assert client.post(path, headers=headers, json={**payload, "Repeats": "3"}).json == first.json
    assert SongPlayingStatus.objects.first().Category == "Beginner"
    assert client.post(path, headers=headers, json={**payload, "Category": "Intermediate"}).json == first.json
    assert SongPlayingStatus.objects.first().Category == "Intermediate"
    assert client.post(path, headers=headers, json={
        **payload, "Category": None, "Repeats": None,
    }).json == first.json
    saved = SongPlayingStatus.objects.first()
    assert saved.Category == "Intermediate" and saved.Repeats == 0


def test_explicit_null_repeats_retains_original_zero_default(client, login):
    headers, _, _ = login()
    payload = {"ActivityId": 1, "LessonId": 2, "CompletionStatus": 5, "Repeats": None}
    path = "/api/activity/updateStatus"
    first = client.post(path, headers=headers, json=payload)
    assert first.status_code == 200 and ActivityStatus.objects.first().Repeats == 0
    assert client.post(path, headers=headers, json={**payload, "Repeats": 3}).json == first.json
    assert client.post(path, headers=headers, json=payload).json == first.json
    assert ActivityStatus.objects.first().Repeats == 0


def test_forgot_and_score_ignore_harmless_full_user_dto_fields(client, login):
    headers, _, user_id = login()
    payload = deepcopy(CONTRACT["user"])
    payload["password"] = "unused-legacy-field"
    payload["score"] = "10"
    assert client.post("/api/auth/forgotPwd", json=payload).status_code == 200
    assert client.post("/api/user/updateUserScore", headers=headers, json=payload).status_code == 200
    user = User.objects.get(id=user_id)
    assert user.score == 10 and user.check_password("test-password")


def test_program_replacement_preserves_baseline_missing_fields_and_clears_stale_data(client, login):
    headers, _, _ = login("AdminUser@mal.com")
    path = "/api/lesson/createLessons"
    rich = {
        "_id": "1", "Name": "Original", "Description": "Old",
        "Songs": [{"_id": "2", "Name": "Song", "Url": "https://example.test/song", "Score": "10"}],
        "RewardConfig": {"_id": "1", "ActivityRepeat": 0.5},
        "Phases": [{"_id": "1", "Name": "Phase", "Lessons": [{
            "_id": "2", "Name": "Lesson", "Activities": [{"_id": "3", "Name": "Activity", "Score": "5"}],
        }]}],
    }
    assert client.post(path, headers=headers, json=[rich]).json == {"id": "[1]"}
    published = client.get("/api/lesson/getLessons").json[0]
    assert published["Songs"][0] == {
        "_id": 2, "Name": "Song", "Url": "https://example.test/song", "Score": 10,
    }
    assert published["Phases"][0]["Lessons"][0]["Activities"][0] == {
        "_id": 3, "Name": "Activity", "Videos": [], "Score": 5, "PracticeMode": False,
    }
    Program._get_collection().update_one({"_id": 1}, {"$set": {"obsolete": "old data"}})
    for optionals in ({}, {"Description": None, "RewardConfig": None, "Songs": None, "Phases": None}):
        assert client.post(path, headers=headers, json=[
            {"_id": 1, "Name": "Replacement", **optionals},
        ]).json == {"id": "[1]"}
        assert client.get("/api/lesson/getLessons").json == [CONTRACT["program_replacement"]]
        assert Program._get_collection().find_one() == CONTRACT["program_replacement"]


@pytest.mark.parametrize("field", ["auth_version", "active_writes", "deletion_started", "is_admin", "unknown"])
def test_unsafe_and_unknown_fields_remain_explicit_errors(client, login, field):
    headers, _, _ = login()
    for path, payload in [
        ("/api/auth/login", {"email": "jane@example.test", "password": "test-password"}),
        ("/api/auth/forgotPwd", {"email": "jane@example.test"}),
        ("/api/auth/resetPwd", {"reset_token": "invalid", "password": "test-password"}),
        ("/api/user/updateUserScore", {"score": 5}),
        ("/api/msg/send", {"Msg": "hello"}),
        ("/api/activity/updateStatus", {"ActivityId": 1, "LessonId": 1, "CompletionStatus": 1}),
    ]:
        response = client.post(path, headers=headers, json={**payload, field: 1})
        assert response.status_code == 400
        assert response.json == CONTRACT["errors"]["schema"]


def test_original_domain_error_envelopes_and_intentional_jwt_errors(client, login):
    headers, _, _ = login()
    assert client.post("/api/auth/signup", json={
        "name": "Jane", "email": "jane@example.test", "password": "test-password",
    }).json == CONTRACT["errors"]["duplicate_email"]
    assert client.post("/api/auth/login", json={
        "email": "jane@example.test", "password": "wrong-password",
    }).json == CONTRACT["errors"]["login"]
    assert client.post("/api/auth/resetPwd", json={
        "reset_token": "invalid", "password": "test-password",
    }).json == CONTRACT["errors"]["reset_token"]
    assert client.get("/api/user/getUserScore").json == {"message": "Invalid or missing token"}
    assert client.get("/api/user/getUserScore").status_code == 401
    assert client.get("/api/user/getUserScore", headers=headers).json == {"score": 0}


def test_speech_limit_is_not_a_new_lesson_body_limit(app, client, login):
    headers, _, _ = login("AdminUser@mal.com")
    app.config["MAX_SPEECH_UPLOAD_BYTES"] = 100
    assert client.post("/api/lesson/createLessons", headers=headers, json=[
        {"_id": 1, "Name": "Program", "Description": "x" * 200},
    ]).status_code == 200
    assert client.post("/api/user/speechScore", headers=headers, data={
        "speech_text": "hello", "music_file": (io.BytesIO(b"audio"), "audio.wav"),
    }).status_code == 413


def test_documented_message_boundary(client, login):
    headers, _, _ = login()
    assert client.post("/api/msg/send", headers=headers, json={"Msg": "x" * 10000}).status_code == 200
    assert client.post("/api/msg/send", headers=headers, json={"Msg": "x" * 10001}).status_code == 400
    assert client.post("/api/msg/send", headers=headers, json={"Msg": "bad\ud800"}).status_code == 400


def test_score_and_message_ownership_cannot_be_selected_by_legacy_metadata(client, login):
    from database.models import IncomeMessage

    headers, _, user_id = login()
    other_headers, _, other_id = login("other@example.test")
    extras = {"User": other_id, "id": other_id, "_id": {"$oid": other_id}}
    assert client.post("/api/user/updateUserScore", headers=headers, json={
        **extras, "score": "10",
    }).status_code == 200
    assert client.get("/api/user/getUserScore", headers=other_headers).json == {"score": 0}
    assert client.post("/api/msg/send", headers=headers, json={**extras, "Msg": "hello"}).status_code == 200
    assert str(IncomeMessage.objects.first().User.id) == user_id
