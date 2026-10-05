from datetime import datetime, timezone

from mongoengine.errors import NotUniqueError
from resources.errors import SchemaValidationError


def update_progress(status, key_fields):
    query = type(status).objects(**{field: getattr(status, field) for field in key_fields})
    values = {"CompletionStatus": status.CompletionStatus, "Repeats": status.Repeats}
    missing_category = hasattr(status, "Category") and status.Category is None
    if hasattr(status, "Category") and not missing_category:
        values["Category"] = status.Category
    unchanged = query.filter(**values).first()
    if unchanged is not None:
        return unchanged
    updates = {f"set__{key}": value for key, value in values.items()}
    updates["set__UpdateTime"] = datetime.now(timezone.utc)
    try:
        saved = query.modify(upsert=not missing_category, new=True, **updates)
        if saved is None:
            raise SchemaValidationError
        return saved
    except NotUniqueError:
        # Another request may have inserted this unique progress key after our read.
        saved = query.modify(new=True, **updates)
        if saved is None:
            raise
        return saved
