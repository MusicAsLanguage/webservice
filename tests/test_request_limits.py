import io
import json
from unittest.mock import Mock

import pytest

from database.models import ActivityStatus, IncomeMessage, Program, SongPlayingStatus, User


JSON_LIMIT = 256 * 1024
LESSON_LIMIT = 16 * 1024 * 1024
TOO_LARGE = {"message": "The data value transmitted exceeds the capacity limit."}


def assert_too_large(response):
    assert response.status_code == 413
    assert json.loads(response.data) == TOO_LARGE


@pytest.mark.parametrize("path", [
    "/api/auth/signup", "/api/auth/login", "/api/auth/forgotPwd", "/api/auth/resetPwd",
    "/api/activity/updateStatus", "/api/activity/updateSongPlayingStatus",
    "/api/user/updateUserScore", "/api/msg/send",
])
def test_json_body_is_bounded_before_parsing(app, client, case, login, monkeypatch, path):
    headers, _, user_id = login()
    parse = Mock(wraps=app.json.loads)
    monkeypatch.setattr(app.json, "loads", parse)
    response = client.post(
        path, headers=headers, data=b"{" + b" " * JSON_LIMIT, content_type="application/json",
    )
    assert_too_large(response)
    parse.assert_not_called()
    case.mail.assert_not_called()
    assert User.objects.count() == 1
    assert User.objects.get(id=user_id).score == 0
    assert all(model.objects.count() == 0 for model in (
        ActivityStatus, SongPlayingStatus, IncomeMessage,
    ))


@pytest.mark.parametrize("global_limit,expected_status", [(None, 200), (0, 413), (1, 413)])
def test_json_exact_boundary_and_tighter_global_limit(app, client, global_limit, expected_status):
    app.config["MAX_CONTENT_LENGTH"] = global_limit
    payload = b'{"name":"Jane","email":"jane@example.test","password":"test-password"}'
    body = payload + b" " * (JSON_LIMIT - len(payload))
    response = client.post("/api/auth/signup", data=body, content_type="application/json")
    assert response.status_code == expected_status
    assert User.objects.count() == (1 if expected_status == 200 else 0)


@pytest.mark.parametrize("content_length", [None, "", "0"])
def test_streamed_json_without_content_length_still_obeys_limit(
    app, client, monkeypatch, content_length,
):
    parse = Mock(wraps=app.json.loads)
    monkeypatch.setattr(app.json, "loads", parse)
    response = client.post(
        "/api/auth/login",
        input_stream=io.BytesIO(b"{" + b" " * JSON_LIMIT),
        content_type="application/json",
        environ_overrides={"CONTENT_LENGTH": content_length, "wsgi.input_terminated": True},
    )
    assert_too_large(response)
    parse.assert_not_called()


@pytest.mark.parametrize("global_limit,status", [(None, 200), (0, 413)])
def test_streamed_json_exact_boundary_and_zero_limit(app, client, global_limit, status):
    app.config["MAX_CONTENT_LENGTH"] = global_limit
    payload = b'{"name":"Jane","email":"jane@example.test","password":"test-password"}'
    body = payload + b" " * (JSON_LIMIT - len(payload))
    response = client.post(
        "/api/auth/signup", input_stream=io.BytesIO(body), content_type="application/json",
        environ_overrides={"CONTENT_LENGTH": None, "wsgi.input_terminated": True},
    )
    assert response.status_code == status
    assert User.objects.count() == (1 if status == 200 else 0)


def test_maximum_unicode_message_still_fits_json_allowance(client, login):
    headers, _, _ = login()
    message = "\U0001f600" * 10000
    encoded = json.dumps({"Msg": message})
    assert len(encoded) > 64 * 1024
    response = client.post(
        "/api/msg/send", headers=headers, data=encoded, content_type="application/json",
    )
    assert response.status_code == 200
    assert IncomeMessage.objects.first().Msg == message


def test_lesson_body_has_separate_larger_finite_allowance(app, client, login, monkeypatch):
    headers, _, _ = login("AdminUser@mal.com")
    app.config["MAX_JSON_BODY_BYTES"] = 1
    app.config["MAX_SPEECH_UPLOAD_BYTES"] = 1
    payload = b'[{"_id":1,"Name":"Large program"}]'
    body = payload + b" " * (LESSON_LIMIT - len(payload))
    path = "/api/lesson/createLessons"
    assert client.get("/api/lesson/getLessons").json == []
    response = client.post(path, headers=headers, data=body, content_type="application/json")
    assert response.status_code == 200
    assert response.json == {"id": "[1]"}
    published = client.get("/api/lesson/getLessons").json
    assert published == [{"_id": 1, "Name": "Large program", "Songs": [], "Phases": []}]
    parse = Mock(wraps=app.json.loads)
    monkeypatch.setattr(app.json, "loads", parse)
    assert_too_large(client.post(
        path, headers=headers, data=body + b" ", content_type="application/json",
    ))
    parse.assert_not_called()
    assert Program.objects.get(_id=1).Name == "Large program"
    assert client.get("/api/lesson/getLessons").json == published


@pytest.mark.parametrize("global_limit", [0, 1, JSON_LIMIT])
def test_lesson_allowance_cannot_override_tighter_global_limit(app, client, login, global_limit):
    headers, _, _ = login("AdminUser@mal.com")
    app.config["MAX_CONTENT_LENGTH"] = global_limit
    body = b"[]" + b" " * JSON_LIMIT
    assert_too_large(client.post(
        "/api/lesson/createLessons", headers=headers, data=body, content_type="application/json",
    ))
    assert Program.objects.count() == 0


@pytest.mark.parametrize("global_limit", [None, 0])
def test_web_reset_form_is_bounded_before_form_parsing(app, client, case, monkeypatch, global_limit):
    app.config["MAX_CONTENT_LENGTH"] = global_limit
    reset = Mock()
    monkeypatch.setattr("app.db_reset_pwd", reset)
    assert_too_large(client.post(
        "/resetPwd",
        data=b"password=" + b"x" * JSON_LIMIT,
        content_type="application/x-www-form-urlencoded",
    ))
    reset.assert_not_called()
    case.mail.assert_not_called()


@pytest.mark.parametrize("global_limit", [None, 0, 100])
def test_speech_honors_explicit_zero_and_other_global_limits(app, client, case, login, global_limit):
    headers, _, user_id = login()
    app.config["MAX_CONTENT_LENGTH"] = global_limit
    response = client.post("/api/user/speechScore", headers=headers, data={
        "speech_text": "hello",
        "music_file": (io.BytesIO(b"audio"), "audio.wav"),
    })
    assert not app.extensions["speech_lock"].locked()
    if global_limit is None:
        assert response.status_code == 200
        case.transcriber.assert_called_once()
        assert User.objects.get(id=user_id).score == 10
    else:
        assert_too_large(response)
        case.transcriber.assert_not_called()
        assert User.objects.get(id=user_id).score == 0
