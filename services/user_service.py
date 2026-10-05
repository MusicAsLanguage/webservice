from contextlib import contextmanager

from database.models import ActivityStatus, IncomeMessage, SongPlayingStatus, User
from resources.errors import ConflictError, UnauthorizedError
from services.auth_service import version_query


@contextmanager
def user_write(user):
    # Admission and deletion marking contend on the same MongoDB document.
    admitted = User.objects(
        version_query(user.auth_version), id=user.id, deletion_started__ne=True,
    ).update_one(inc__active_writes=1)
    if admitted != 1:
        raise UnauthorizedError
    try:
        yield
    finally:
        User.objects(id=user.id).update_one(__raw__={"$inc": {"active_writes": -1}})


def delete_account(user_id):
    user = User.objects(id=user_id).modify(new=True, set__deletion_started=True)
    if user is None:
        return
    if user.active_writes:
        raise ConflictError
    for model in (ActivityStatus, SongPlayingStatus, IncomeMessage):
        model.objects(User=user).delete()
    User.objects(id=user.id).delete()
