import io
from concurrent.futures import ThreadPoolExecutor

import pytest

from database.models import User
from services.speech_service import levenshtein_distance, score_speech


@pytest.mark.parametrize("expected,actual,score", [
    ("", "", 0), ("hello", "", 0), ("", "hello", 0),
    ("hello", "hello", 10), ("hello world", "hello world", 20),
])
def test_scoring_empty_and_matching_text(expected, actual, score):
    assert score_speech(expected, actual) == score


def test_edit_distance():
    assert levenshtein_distance("kitten", "sitting") == 3
    assert levenshtein_distance("", "abc") == 3


def speech_data(text="hello"):
    return {"speech_text": text, "music_file": (io.BytesIO(b"audio"), "audio.wav")}


def test_speech_updates_score_and_cleans_file(client, case, login):
    headers, _, user_id = login()
    paths = []

    def transcribe(path, maximum):
        assert path.read_bytes() == b"audio"
        assert maximum == 120
        paths.append(path)
        return "hello"

    case.transcriber.side_effect = transcribe
    response = client.post("/api/user/speechScore", headers=headers, data=speech_data())
    assert response.status_code == 200
    assert response.json == {"text": "hello", "score": 10}
    assert User.objects.get(id=user_id).score == 10
    assert all(not path.parent.exists() for path in paths)


def test_transcription_failure_cleans_file_and_preserves_score(client, case, login):
    headers, _, user_id = login()
    paths = []

    def fail(path, maximum):
        paths.append(path)
        raise RuntimeError("inference failed")

    case.transcriber.side_effect = fail
    assert client.post("/api/user/speechScore", headers=headers, data=speech_data()).status_code == 500
    assert paths and all(not path.parent.exists() for path in paths)
    assert User.objects.get(id=user_id).score == 0


@pytest.mark.parametrize("form", [{}, {"speech_text": "hello"}])
def test_missing_speech_fields(client, case, login, form):
    headers, _, _ = login()
    assert client.post("/api/user/speechScore", headers=headers, data=form).status_code == 400
    case.transcriber.assert_not_called()


@pytest.mark.parametrize("text", ["", " " * 10, "x" * 2001])
def test_speech_text_limits(client, case, login, text):
    headers, _, _ = login()
    assert client.post("/api/user/speechScore", headers=headers, data=speech_data(text)).status_code == 400
    case.transcriber.assert_not_called()


def test_upload_size_is_limited(app, client, case, login):
    headers, _, _ = login()
    app.config["MAX_CONTENT_LENGTH"] = 100
    assert client.post("/api/user/speechScore", headers=headers, data=speech_data()).status_code == 413
    case.transcriber.assert_not_called()


@pytest.mark.parametrize("size", [500_001, 10 * 1024 * 1024 - 1024])
def test_large_audio_is_not_rejected_by_non_file_field_limit(app, client, case, login, size):
    headers, _, user_id = login()
    assert app.config["MAX_FORM_MEMORY_SIZE"] == 500_000
    assert app.config["MAX_SPEECH_UPLOAD_BYTES"] == 10 * 1024 * 1024
    audio = b"a" * size
    paths = []

    def transcribe(path, maximum):
        assert path.read_bytes() == audio
        paths.append(path)
        return "hello"

    case.transcriber.side_effect = transcribe
    form = {"speech_text": "hello", "music_file": (io.BytesIO(audio), "audio.wav")}
    response = client.post("/api/user/speechScore", headers=headers, data=form)
    assert response.status_code == 200
    assert response.json == {"text": "hello", "score": 10}
    assert User.objects.get(id=user_id).score == 10
    case.transcriber.assert_called_once()
    assert all(not path.parent.exists() for path in paths)


@pytest.mark.parametrize("limit", ["field", "parts", "request"])
def test_default_multipart_limits_return_json_without_scoring(app, client, case, login, limit):
    headers, _, user_id = login()
    form = speech_data()
    if limit == "field":
        assert app.config["MAX_FORM_MEMORY_SIZE"] == 500_000
        form["speech_text"] = "x" * 500_001
    elif limit == "parts":
        assert app.config["MAX_FORM_PARTS"] == 1000
        form.update({f"extra_{index}": "x" for index in range(999)})
    else:
        assert app.config["MAX_SPEECH_UPLOAD_BYTES"] == 10 * 1024 * 1024
        form["music_file"] = (io.BytesIO(b"a" * (10 * 1024 * 1024)), "audio.wav")

    response = client.post("/api/user/speechScore", headers=headers, data=form)
    assert response.status_code == 413
    assert response.json == {"message": "The data value transmitted exceeds the capacity limit."}
    case.transcriber.assert_not_called()
    assert User.objects.get(id=user_id).score == 0


def test_speech_text_limit_counts_unicode_characters(client, case, login):
    headers, _, _ = login()
    text = "\u00e9" * 2000
    case.transcriber.return_value = text
    response = client.post("/api/user/speechScore", headers=headers, data=speech_data(text))
    assert response.status_code == 200
    assert response.json == {"text": text, "score": 10}


def test_concurrent_speech_rewards_are_not_lost(app, login):
    headers, _, user_id = login()

    def award(_):
        with app.test_client() as client:
            return client.post("/api/user/speechScore", headers=headers, data=speech_data()).status_code

    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(award, range(24)))
    assert set(results) <= {200, 503}
    assert results.count(200) > 0
    assert User.objects.get(id=user_id).score == results.count(200) * 10


def test_busy_speech_request_is_rejected_before_parsing_upload(app, client, case, login):
    headers, _, _ = login()
    app.extensions["speech_lock"].acquire()
    try:
        response = client.post("/api/user/speechScore", headers=headers, data=b"malformed")
        assert response.status_code == 503
        case.transcriber.assert_not_called()
    finally:
        app.extensions["speech_lock"].release()
    assert client.post("/api/user/speechScore", headers=headers, data=speech_data()).status_code == 200


@pytest.mark.parametrize("actual,status", [(None, 500), ("x" * 2001, 400), ("", 200)])
def test_transcriber_output_validation_releases_lock_and_cleans_audio(
    app, client, case, login, actual, status,
):
    headers, _, user_id = login()
    paths = []

    def transcribe(path, _):
        paths.append(path)
        return actual

    case.transcriber.side_effect = transcribe
    response = client.post("/api/user/speechScore", headers=headers, data=speech_data())
    assert response.status_code == status
    assert User.objects.get(id=user_id).score == 0
    assert not app.extensions["speech_lock"].locked()
    assert all(not path.parent.exists() for path in paths)


def test_speech_increment_does_not_overflow_storage(client, login):
    headers, _, user_id = login()
    User.objects(id=user_id).update_one(set__score=2**63 - 1)
    assert client.post("/api/user/speechScore", headers=headers, data=speech_data()).status_code == 400
    assert User.objects.get(id=user_id).score == 2**63 - 1


def test_speech_increment_preserves_default_score_on_legacy_documents(client, login):
    headers, _, user_id = login()
    User.objects(id=user_id).update_one(unset__score=1)
    assert client.post("/api/user/speechScore", headers=headers, data=speech_data()).status_code == 200
    assert User.objects.get(id=user_id).score == 10


def test_speech_never_logs_transcript(client, case, login, caplog):
    headers, _, _ = login()
    case.transcriber.return_value = "private recognized phrase"
    response = client.post("/api/user/speechScore", headers=headers, data=speech_data("private input"))
    assert response.status_code == 200
    assert "private recognized phrase" not in caplog.text and "private input" not in caplog.text
