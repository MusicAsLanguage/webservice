from datetime import timedelta

from flask import current_app, render_template, request
from flask_jwt_extended import create_access_token
from flask_restful import Resource

from database.models import User
from database.utils import db_reset_pwd
from resources.errors import EmailDoesnotExistsError
from resources.validation import LEGACY_USER_FIELDS, json_body, password_value, text
from services.mail_service import send_email


class ForgotPassword(Resource):
    def post(self):
        body = json_body({"email"}, LEGACY_USER_FIELDS)
        email = text(body["email"])
        user = User.objects(email=email, deletion_started__ne=True).first()
        if user is None:
            raise EmailDoesnotExistsError
        token = create_access_token(
            str(user.id),
            expires_delta=timedelta(hours=24),
            additional_claims={"purpose": "password_reset", "version": user.auth_version},
        )
        base_url = current_app.config["PUBLIC_BASE_URL"] or request.host_url
        url = base_url.rstrip("/") + "/resetPwd/" + token
        send_email(
            "[MusicAsLanguage] Reset Your Password",
            sender="musicaslanguage@sf-ns.org",
            recipients=[user.email],
            text_body=render_template("email/reset_password.txt", url=url),
            html_body=render_template("email/reset_password.html", url=url),
        )
        return {"status": "Password reset email has been sent to " + email}, 200


class ResetPassword(Resource):
    def post(self):
        body = json_body({"reset_token", "password"}, LEGACY_USER_FIELDS | {"email"})
        db_reset_pwd(text(body["reset_token"], 8192), password_value(body["password"]))
        return {"status": "Password reset was successful!"}, 200
