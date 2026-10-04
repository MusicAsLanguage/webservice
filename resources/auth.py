from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    current_user,
    jwt_required,
)
from flask_restful import Resource
from mongoengine.errors import NotUniqueError

from database.models import User
from resources.errors import EmailAlreadyExistsError, UnauthorizedError
from resources.validation import json_body, password_value, text
from services.auth_service import access_identity, user_claims


class SignupApi(Resource):
    def post(self):
        body = json_body({"name", "email", "password"})
        user = User(
            name=text(body["name"]),
            email=text(body["email"]),
            password=password_value(body["password"]),
        )
        user.validate()
        user.hash_password()
        try:
            user.save()
        except NotUniqueError as error:
            raise EmailAlreadyExistsError from error
        return {"id": str(user.id)}, 200


class LoginApi(Resource):
    def post(self):
        body = json_body({"email", "password"}, {"name"})
        email, password = text(body["email"]), text(body["password"])
        user = User.objects(email=email).first()
        if user is None or len(password.encode("utf-8")) > 72 or not user.check_password(password):
            raise UnauthorizedError
        claims = user_claims(user)
        return {
            "token": create_access_token(
                identity=access_identity(user), fresh=True, additional_claims=claims
            ),
            "refresh_token": create_refresh_token(
                identity=str(user.id), additional_claims=claims
            ),
        }, 200


class TokenRefreshApi(Resource):
    @jwt_required(refresh=True)
    def post(self):
        return {
            "token": create_access_token(
                identity=access_identity(current_user),
                fresh=False,
                additional_claims=user_claims(current_user),
            )
        }, 200
