import click
from mongoengine import get_db

from database.models import ActivityStatus, SongPlayingStatus


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
