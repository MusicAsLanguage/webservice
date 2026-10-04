import json

from bson import ObjectId
from flask import current_app
from flask_jwt_extended import current_user

from database.models import User
from resources.errors import UnauthorizedError


def identity_id(identity):
    if not isinstance(identity, str):
        return None
    # Keep accepting the serialized user identities issued to existing mobile clients.
    if identity.startswith("{"):
        try:
            identity = json.loads(identity)["_id"]["$oid"]
        except (ValueError, KeyError, TypeError):
            return None
    return identity if isinstance(identity, str) and ObjectId.is_valid(identity) else None


def initialize_jwt(jwt):
    @jwt.user_lookup_loader
    def load_user(header, claims):
        user_id = identity_id(claims.get("sub"))
        if user_id is None or claims.get("purpose", "session") != "session":
            return None
        user = User.objects(id=user_id).first()
        if user is None or user.auth_version != claims.get("version", 0):
            return None
        return user


def user_claims(user):
    return {"purpose": "session", "version": user.auth_version}


def access_identity(user):
    data = json.loads(user.to_json())
    data["password"] = ""
    data.pop("auth_version", None)
    return json.dumps(data)


def require_admin():
    if current_user.email.lower() not in current_app.config["ADMIN_USERS"]:
        raise UnauthorizedError
