import json

from bson import ObjectId
from flask import current_app, request
from flask_jwt_extended import current_user
from mongoengine import Q

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
        if user_id is None or not session_claims(claims):
            return None
        user = User.objects(id=user_id).first()
        if user is None or user.auth_version != claims.get("version", 0):
            return None
        if user.deletion_started and request.endpoint != "deleteuseranddataapi":
            return None
        return user


def session_claims(claims):
    if "purpose" in claims or "version" in claims:
        return (
            claims.get("purpose") == "session"
            and type(claims.get("version")) is int
            and claims["version"] >= 0
        )
    identity = claims.get("sub", "")
    return (
        claims.get("type") == "access" and identity.startswith("{")
        or claims.get("type") == "refresh" and ObjectId.is_valid(identity)
    )


def reset_claims(claims):
    identity = claims.get("sub")
    if not isinstance(identity, str) or not ObjectId.is_valid(identity):
        return False
    issued, expires = claims.get("iat"), claims.get("exp")
    if (
        claims.get("type") != "access"
        or type(issued) is not int or type(expires) is not int
        or not 0 < expires - issued <= 86400
    ):
        return False
    if "purpose" in claims or "version" in claims:
        return (
            claims.get("purpose") == "password_reset"
            and type(claims.get("version")) is int
            and claims["version"] >= 0
        )
    # Only the old reset issuer used plain-ID access tokens with this exact lifetime.
    return expires - issued == 86400 and claims.get("fresh") is False


def version_query(version):
    if version == 0:
        return Q(auth_version=0) | Q(auth_version__exists=False)
    return Q(auth_version=version)


def user_claims(user):
    return {"purpose": "session", "version": user.auth_version}


def access_identity(user):
    data = json.loads(user.to_json())
    data["password"] = ""
    for key in ("auth_version", "deletion_started", "active_writes"):
        data.pop(key, None)
    return json.dumps(data)


def require_admin():
    if current_user.email.lower() not in current_app.config["ADMIN_USERS"]:
        raise UnauthorizedError
