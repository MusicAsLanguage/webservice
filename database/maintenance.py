import click
from bson import ObjectId
from mongoengine import get_db

from database.models import ActivityStatus, SongPlayingStatus, User
from services.user_service import delete_account


@click.command("prepare-indexes")
def prepare_indexes():
    """Refuse ambiguous progress records before creating unique indexes."""
    for model, fields in (
        (ActivityStatus, ("User", "ActivityId", "LessonId")),
        (SongPlayingStatus, ("User", "SongName")),
    ):
        collection = get_db()[model._get_collection_name()]
        duplicates = list(collection.aggregate([
            {"$group": {"_id": {field: "$" + field for field in fields}, "count": {"$sum": 1}}},
            {"$match": {"count": {"$gt": 1}}},
            {"$limit": 1},
        ]))
        if duplicates:
            raise click.ClickException(
                f"{collection.name} has duplicate progress keys; back up and reconcile them first"
            )
    ActivityStatus.ensure_indexes()
    SongPlayingStatus.ensure_indexes()
    click.echo("Progress indexes are ready")


@click.command("recover-deletion")
@click.option("--user-id", required=True)
@click.option("--writers-stopped", is_flag=True, help="Confirm ALL service writers are stopped.")
def recover_deletion(user_id, writers_stopped):
    """Recover one interrupted deletion, only during a confirmed writer outage."""
    if not writers_stopped:
        raise click.ClickException("Stop ALL service writers, then pass --writers-stopped")
    if not ObjectId.is_valid(user_id):
        raise click.ClickException("A valid user ID is required")
    user = User.objects(id=user_id, deletion_started=True).modify(new=True, set__active_writes=0)
    if user is None:
        raise click.ClickException("No deleting account has this ID; nothing was changed")
    delete_account(user.id)
    click.echo("Account deletion completed")
