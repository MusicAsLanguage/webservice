from datetime import datetime, timezone

from flask import current_app
from flask_bcrypt import generate_password_hash
from flask_jwt_extended import decode_token
from flask_jwt_extended.exceptions import JWTExtendedException
from jwt import PyJWTError

from database.models import User
from resources.errors import BadTokenError
from resources.validation import password_value
from services.auth_service import identity_id
from services.mail_service import send_email


def db_reset_pwd(reset_token, password):
    password_value(password)
    try:
        claims = decode_token(reset_token)
    except (PyJWTError, JWTExtendedException) as error:
        raise BadTokenError from error
    user_id = identity_id(claims.get("sub"))
    if claims.get("purpose") != "password_reset" or claims.get("type") != "access" or not user_id:
        raise BadTokenError
    user = User.objects(id=user_id).first()
    if user is None or claims.get("version") != user.auth_version:
        raise BadTokenError
    hashed_password = generate_password_hash(password).decode("utf-8")
    # Comparing the old hash also makes concurrent uses of the same reset token single-use.
    updated = User.objects(id=user.id, password=user.password).update_one(
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
