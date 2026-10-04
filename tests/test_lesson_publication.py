from copy import deepcopy

import pytest
from mongoengine.queryset import QuerySet

from database.models import Program


def test_publish_invalidates_warmed_cache(client, login):
    headers, _, _ = login("AdminUser@mal.com")
    assert client.get("/api/lesson/getLessons").json == []
    payload = [{"_id": 1, "Name": "Original"}]
    assert client.post("/api/lesson/createLessons", headers=headers, json=payload).status_code == 200
    assert client.get("/api/lesson/getLessons").json[0]["Name"] == "Original"
    payload[0]["Name"] = "Updated"
    assert client.post("/api/lesson/createLessons", headers=headers, json=payload).status_code == 200
    assert client.get("/api/lesson/getLessons").json[0]["Name"] == "Updated"
    assert Program.objects.count() == 1


@pytest.mark.parametrize("invalid", [
    {"_id": 1}, {"_id": 1, "Name": "Broken", "Unknown": True},
    {"_id": 1, "Name": "Broken", "Songs": [{"Name": "Missing required fields"}]},
])
def test_invalid_replacement_keeps_existing_program(client, login, invalid):
    headers, _, _ = login("AdminUser@mal.com")
    assert client.post("/api/lesson/createLessons", headers=headers, json=[
        {"_id": 1, "Name": "Original"},
    ]).status_code == 200
    response = client.post("/api/lesson/createLessons", headers=headers, json=[invalid])
    assert response.status_code == 400
    assert Program.objects.get(_id=1).Name == "Original"


def test_entire_batch_is_validated_before_any_write(client, login):
    headers, _, _ = login("AdminUser@mal.com")
    original = [{"_id": 1, "Name": "Original"}]
    assert client.post("/api/lesson/createLessons", headers=headers, json=original).status_code == 200
    batch = deepcopy(original)
    batch[0]["Name"] = "Changed"
    batch.append({"_id": 2})
    assert client.post("/api/lesson/createLessons", headers=headers, json=batch).status_code == 400
    assert Program.objects.get(_id=1).Name == "Original"
    assert Program.objects.count() == 1


@pytest.mark.parametrize("payload", [
    {}, [1], [{"_id": 1, "Name": "One"}, {"_id": 1, "Name": "Two"}],
    [{"_id": 1, "Name": "Same"}, {"_id": 2, "Name": "Same"}],
])
def test_invalid_batches_are_rejected(client, login, payload):
    headers, _, _ = login("AdminUser@mal.com")
    assert client.post("/api/lesson/createLessons", headers=headers, json=payload).status_code == 400
    assert Program.objects.count() == 0


def test_partial_database_failure_clears_cache_and_keeps_old_documents(client, login, monkeypatch):
    headers, _, _ = login("AdminUser@mal.com")
    payload = [{"_id": 1, "Name": "One"}, {"_id": 2, "Name": "Two"}]
    assert client.post("/api/lesson/createLessons", headers=headers, json=payload).status_code == 200
    assert len(client.get("/api/lesson/getLessons").json) == 2
    original = QuerySet.modify

    def fail_second_program(query, **kwargs):
        if kwargs.get("set__Name") == "Changed Two":
            raise RuntimeError("Database write failed")
        return original(query, **kwargs)

    monkeypatch.setattr(QuerySet, "modify", fail_second_program)
    updated = [{"_id": 1, "Name": "Changed One"}, {"_id": 2, "Name": "Changed Two"}]
    assert client.post("/api/lesson/createLessons", headers=headers, json=updated).status_code == 500
    names = {item["Name"] for item in client.get("/api/lesson/getLessons").json}
    assert names == {"Changed One", "Two"}
