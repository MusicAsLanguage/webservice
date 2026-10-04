from database.models import ActivityStatus, IncomeMessage, SongPlayingStatus, User


def test_deletion_removes_all_owned_data_only(client, login):
    headers, _, user_id = login()
    _, _, other_id = login("other@example.test")
    for user in User.objects:
        ActivityStatus(User=user, ActivityId=1, LessonId=1, CompletionStatus=1).save()
        SongPlayingStatus(User=user, SongName="Song", Category="Beginner", CompletionStatus=1).save()
        IncomeMessage(User=user, Msg="Saved message").save()
    assert client.delete("/api/user/deleteUserAndData", headers=headers).status_code == 200
    assert User.objects(id=user_id).first() is None
    other = User.objects.get(id=other_id)
    for model in (ActivityStatus, SongPlayingStatus, IncomeMessage):
        assert model.objects.count() == 1
        assert model.objects.first().User == other


def test_message_delivery_failure_is_logged_and_message_is_retained(client, case, login, caplog):
    headers, _, _ = login()
    case.mail.side_effect = RuntimeError("provider unavailable")
    response = client.post("/api/msg/send", headers=headers, json={"Msg": "<p>Hello</p>"})
    assert response.status_code == 200
    assert IncomeMessage.objects.count() == 1
    assert case.mail.call_args.kwargs["html_body"] == "&lt;p&gt;Hello&lt;/p&gt;"
    assert "Message saved but notification failed" in caplog.text
