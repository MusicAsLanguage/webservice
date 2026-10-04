from concurrent.futures import ThreadPoolExecutor

import pytest
from mongoengine.errors import NotUniqueError
from mongoengine.queryset import QuerySet

from database.models import ActivityStatus, SongPlayingStatus, User


@pytest.mark.parametrize("endpoint,model,payload", [
    ("/api/activity/updateStatus", ActivityStatus, {"ActivityId": 1, "LessonId": 1}),
    ("/api/activity/updateSongPlayingStatus", SongPlayingStatus, {"SongName": "Song", "Category": "Beginner"}),
])
def test_concurrent_progress_writes_are_unique(app, login, endpoint, model, payload):
    headers, _, _ = login()
    model.ensure_indexes()

    def write(index):
        with app.test_client() as client:
            return client.post(endpoint, headers=headers, json={
                **payload, "CompletionStatus": index % 11, "Repeats": index,
            })

    with ThreadPoolExecutor(max_workers=8) as executor:
        responses = list(executor.map(write, range(24)))
    assert all(response.status_code == 200 for response in responses)
    assert len({response.json["id"] for response in responses}) == 1
    assert model.objects.count() == 1
    saved = model.objects.first()
    assert saved.CompletionStatus == saved.Repeats % 11


@pytest.mark.parametrize("value", [-1, 11, "5", 5.5, True, None])
def test_progress_bounds(client, login, value):
    headers, _, _ = login()
    for endpoint, payload in [
        ("/api/activity/updateStatus", {"ActivityId": 1, "LessonId": 1}),
        ("/api/activity/updateSongPlayingStatus", {"SongName": "Song", "Category": "Beginner"}),
    ]:
        assert client.post(endpoint, headers=headers, json={
            **payload, "CompletionStatus": value,
        }).status_code == 400
    assert ActivityStatus.objects.count() == SongPlayingStatus.objects.count() == 0


def test_progress_noop_preserves_time_and_rejects_negative_repeats(client, login):
    headers, _, _ = login()
    payload = {"CompletionStatus": 5, "ActivityId": 1, "LessonId": 1}
    first = client.post("/api/activity/updateStatus", headers=headers, json=payload)
    before = ActivityStatus.objects.first().UpdateTime
    again = client.post("/api/activity/updateStatus", headers=headers, json=payload)
    assert first.json == again.json
    assert ActivityStatus.objects.first().UpdateTime == before
    assert client.post("/api/activity/updateStatus", headers=headers, json={
        **payload, "Repeats": -1,
    }).status_code == 400


def test_progress_is_scoped_to_user_and_category_updates(client, login):
    first_headers, _, first_id = login()
    second_headers, _, _ = login("other@example.test")
    payload = {"SongName": "Song", "Category": "Beginner", "CompletionStatus": 1}
    first = client.post("/api/activity/updateSongPlayingStatus", headers=first_headers, json=payload)
    assert client.get("/api/activity/getSongPlayingStatus", headers=second_headers).json == []
    second = client.post("/api/activity/updateSongPlayingStatus", headers=second_headers, json=payload)
    assert first.json["id"] != second.json["id"]
    assert client.post("/api/activity/updateSongPlayingStatus", headers=first_headers, json={
        **payload, "Category": "Intermediate",
    }).status_code == 200
    assert SongPlayingStatus.objects(User=User.objects.get(id=first_id)).first().Category == "Intermediate"


def test_unique_progress_indexes_prevent_duplicate_records(login):
    _, _, user_id = login()
    user = User.objects.get(id=user_id)
    values = {"User": user, "ActivityId": 1, "LessonId": 1, "CompletionStatus": 5}
    ActivityStatus(**values).save()
    with pytest.raises(NotUniqueError):
        ActivityStatus(**values).save()


def test_concurrent_insert_collision_retries_existing_record(client, login, monkeypatch):
    headers, _, _ = login()
    original = QuerySet.modify
    attempts = []

    def competing_insert(query, **kwargs):
        result = original(query, **kwargs)
        attempts.append(kwargs.get("upsert", False))
        if kwargs.get("upsert"):
            raise NotUniqueError("Concurrent request inserted this key")
        return result

    monkeypatch.setattr(QuerySet, "modify", competing_insert)
    response = client.post("/api/activity/updateStatus", headers=headers, json={
        "ActivityId": 1, "LessonId": 1, "CompletionStatus": 5,
    })
    assert response.status_code == 200
    assert attempts == [True, False]
    assert ActivityStatus.objects.count() == 1


def test_unresolved_insert_collision_is_not_reported_as_success(client, login, monkeypatch):
    headers, _, _ = login()

    def conflict(query, **kwargs):
        if kwargs.get("upsert"):
            raise NotUniqueError("Conflicting key")
        return None

    monkeypatch.setattr(QuerySet, "modify", conflict)
    response = client.post("/api/activity/updateStatus", headers=headers, json={
        "ActivityId": 1, "LessonId": 1, "CompletionStatus": 5,
    })
    assert response.status_code == 409
