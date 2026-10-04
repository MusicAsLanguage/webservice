import io
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event

import pytest
from mongoengine.queryset import QuerySet

from database.models import ActivityStatus, IncomeMessage, SongPlayingStatus, User
from resources.errors import UnauthorizedError
from services.user_service import delete_account, user_write


def owned_data(user):
    ActivityStatus(User=user, ActivityId=1, LessonId=1, CompletionStatus=1).save()
    SongPlayingStatus(User=user, SongName="Song", Category="Beginner", CompletionStatus=1).save()
    IncomeMessage(User=user, Msg="Message").save()


def test_deletion_waits_for_admitted_write_and_rejects_new_writes(app, client, login, monkeypatch):
    headers, _, user_id = login()
    user = User.objects.get(id=user_id)
    admitted, release = Event(), Event()
    original = QuerySet.modify

    def pause_progress(query, **kwargs):
        if query._document is ActivityStatus:
            admitted.set()
            assert release.wait(timeout=10)
        return original(query, **kwargs)

    monkeypatch.setattr(QuerySet, "modify", pause_progress)

    def write():
        with app.test_client() as writer:
            return writer.post("/api/activity/updateStatus", headers=headers, json={
                "ActivityId": 1, "LessonId": 1, "CompletionStatus": 5,
            })

    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(write)
        try:
            assert admitted.wait(timeout=10)
            response = client.delete("/api/user/deleteUserAndData", headers=headers)
            assert response.status_code == 409
            assert User.objects.get(id=user_id).active_writes == 1
            assert User.objects.get(id=user_id).deletion_started
            assert client.get("/api/user/getUserScore", headers=headers).status_code == 401
            assert client.post("/api/msg/send", headers=headers, json={"Msg": "no"}).status_code == 401
            with pytest.raises(UnauthorizedError):
                with user_write(user):
                    pytest.fail("Stale lookups must not admit a write")
        finally:
            release.set()
        assert future.result(timeout=10).status_code == 200
    assert User.objects.get(id=user_id).active_writes == 0
    assert client.delete("/api/user/deleteUserAndData", headers=headers).json == {"success": True}
    assert User.objects.count() == ActivityStatus.objects.count() == 0


@pytest.mark.parametrize("failed_model", [ActivityStatus, SongPlayingStatus, IncomeMessage, User])
def test_partial_cleanup_failure_is_retryable_and_isolated(client, login, monkeypatch, failed_model):
    headers, _, user_id = login()
    _, _, other_id = login("other@example.test")
    for user in User.objects:
        owned_data(user)
    original = QuerySet.delete

    def fail_cleanup(query, *args, **kwargs):
        if query._document is failed_model:
            raise RuntimeError("cleanup unavailable")
        return original(query, *args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(QuerySet, "delete", fail_cleanup)
        response = client.delete("/api/user/deleteUserAndData", headers=headers)
    assert response.status_code == 500
    assert User.objects.get(id=user_id).deletion_started
    assert client.post("/api/user/updateUserScore", headers=headers, json={"score": 5}).status_code == 401
    assert client.delete("/api/user/deleteUserAndData", headers=headers).status_code == 200
    assert User.objects.count() == 1
    for model in (ActivityStatus, SongPlayingStatus, IncomeMessage):
        assert model.objects.count() == 1 and str(model.objects.first().User.id) == other_id


def test_handled_write_error_releases_admission(client, login, monkeypatch):
    headers, _, user_id = login()
    original = IncomeMessage.save

    def fail(*args, **kwargs):
        raise RuntimeError("write failed")

    monkeypatch.setattr(IncomeMessage, "save", fail)
    assert client.post("/api/msg/send", headers=headers, json={"Msg": "hello"}).status_code == 500
    assert User.objects.get(id=user_id).active_writes == 0
    monkeypatch.setattr(IncomeMessage, "save", original)
    assert client.delete("/api/user/deleteUserAndData", headers=headers).status_code == 200


def test_concurrent_authenticated_delete_retries_are_idempotent(app, login, monkeypatch):
    headers, _, user_id = login()
    owned_data(User.objects.get(id=user_id))
    barrier = Barrier(2)

    def synchronize(user_id):
        barrier.wait(timeout=10)
        delete_account(user_id)

    monkeypatch.setattr("resources.user.delete_account", synchronize)

    def delete(_):
        with app.test_client() as client:
            return client.delete("/api/user/deleteUserAndData", headers=headers).status_code

    with ThreadPoolExecutor(max_workers=2) as executor:
        assert list(executor.map(delete, range(2))) == [200, 200]
    assert User.objects.count() == 0
    assert all(model.objects.count() == 0 for model in (ActivityStatus, SongPlayingStatus, IncomeMessage))


def test_interrupted_writer_requires_scoped_explicit_outage_recovery(app, client, login):
    headers, _, user_id = login()
    _, _, other_id = login("other@example.test")
    owned_data(User.objects.get(id=user_id))
    User.objects(id=user_id).update_one(set__active_writes=1)
    assert client.delete("/api/user/deleteUserAndData", headers=headers).status_code == 409
    runner = app.test_cli_runner()
    for arguments in [
        ["--user-id", user_id],
        ["--user-id", "invalid", "--writers-stopped"],
        ["--user-id", other_id, "--writers-stopped"],
    ]:
        assert runner.invoke(args=["recover-deletion", *arguments]).exit_code != 0
        assert User.objects.get(id=user_id).active_writes == 1
        assert User.objects.get(id=other_id).deletion_started is False
    result = runner.invoke(args=["recover-deletion", "--user-id", user_id, "--writers-stopped"])
    assert result.exit_code == 0, result.output
    assert User.objects(id=user_id).count() == 0 and User.objects(id=other_id).count() == 1
    assert all(model.objects.count() == 0 for model in (ActivityStatus, SongPlayingStatus, IncomeMessage))


def test_no_admission_is_held_during_transcription_or_email(client, case, login):
    headers, _, user_id = login()

    def assert_idle(*args, **kwargs):
        assert User.objects.get(id=user_id).active_writes == 0
        return "hello"

    case.transcriber.side_effect = case.mail.side_effect = assert_idle
    assert client.post("/api/msg/send", headers=headers, json={"Msg": "hello"}).status_code == 200
    assert client.post("/api/user/speechScore", headers=headers, data={
        "speech_text": "hello", "music_file": (io.BytesIO(b"audio"), "audio.wav"),
    }).status_code == 200


def test_deletion_during_inference_does_not_recreate_user_or_award_score(client, case, login):
    headers, _, user_id = login()

    def transcribe(*args):
        assert User.objects.get(id=user_id).active_writes == 0
        delete_account(user_id)
        return "hello"

    case.transcriber.side_effect = transcribe
    assert client.post("/api/user/speechScore", headers=headers, data={
        "speech_text": "hello", "music_file": (io.BytesIO(b"audio"), "audio.wav"),
    }).status_code == 401
    assert User.objects.count() == 0
