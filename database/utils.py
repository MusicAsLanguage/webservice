from datetime import datetime, timezone

from flask import current_app
from flask_jwt_extended import decode_token
from flask_jwt_extended.exceptions import JWTExtendedException
from jwt import PyJWTError

from database.models import User
from resources.errors import BadTokenError
from resources.validation import password_value
from services.auth_service import reset_claims, version_query
from services.mail_service import send_email
from services.password_service import generate_password_hash


def db_reset_pwd(reset_token, password):
    password_value(password)
    try:
        claims = decode_token(reset_token)
    except (PyJWTError, JWTExtendedException) as error:
        raise BadTokenError from error
    if not reset_claims(claims):
        raise BadTokenError
    user = User.objects(id=claims["sub"], deletion_started__ne=True).first()
    version = claims.get("version", 0)
    if user is None or version != user.auth_version:
        raise BadTokenError
    hashed_password = generate_password_hash(password).decode("utf-8")
    # Comparing the old hash also makes concurrent uses of the same reset token single-use.
    updated = User.objects(
        version_query(version), id=user.id, password=user.password, deletion_started__ne=True,
    ).update_one(
        set__password=hashed_password,
        inc__auth_version=1,
        set__UpdateTime=datetime.now(timezone.utc),
    )
    if updated != 1:
        raise BadTokenError
    try:
        send_email(
            "[MusicAsLanguage] Password reset successful",
            sender="musicaslanguage@sf-ns.org",
            recipients=[user.email],
            text_body="Password reset was successful",
            html_body="<p>Password reset was successful</p>",
        )
    except Exception:
        # The password is already changed; notification failure must not imply rollback.
        current_app.logger.exception("Password changed but confirmation email failed")
