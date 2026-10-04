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


def test_concurrent_speech_rewards_are_not_lost(app, login):
    headers, _, user_id = login()

    def award(_):
        with app.test_client() as client:
            return client.post("/api/user/speechScore", headers=headers, data=speech_data()).status_code

    with ThreadPoolExecutor(max_workers=8) as executor:
        assert list(executor.map(award, range(24))) == [200] * 24
    assert User.objects.get(id=user_id).score == 240
