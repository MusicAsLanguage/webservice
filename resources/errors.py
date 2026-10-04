from flask import current_app, jsonify
from flask_jwt_extended.exceptions import JWTExtendedException
from flask_restful import Api
from jwt import PyJWTError
from mongoengine.errors import FieldDoesNotExist, NotUniqueError, ValidationError
from werkzeug.exceptions import HTTPException


class ApiError(Exception):
    status = 500
    message = "Something went wrong"


class InternalServerError(ApiError):
    pass


class SchemaValidationError(ApiError):
    status = 400
    message = "Request is missing required fields"


class EmailAlreadyExistsError(ApiError):
    status = 400
    message = "User with given email address already exists"


class UnauthorizedError(ApiError):
    status = 401
    message = "Invalid username or password"


class EmailDoesnotExistsError(ApiError):
    status = 400
    message = "Couldn't find the user with given email address"


class BadTokenError(ApiError):
    status = 403
    message = "Invalid token"


class ServiceUnavailableError(ApiError):
    status = 503
    message = "Service temporarily unavailable"


def error_response(error):
    if isinstance(error, ApiError):
        status, message = error.status, error.message
    elif isinstance(error, (FieldDoesNotExist, ValidationError)):
        status, message = 400, SchemaValidationError.message
    elif isinstance(error, NotUniqueError):
        status, message = 409, "A record with these identifiers already exists"
    elif isinstance(error, (JWTExtendedException, PyJWTError)):
        status, message = 401, "Invalid or missing token"
    elif isinstance(error, HTTPException):
        status, message = error.code, error.description
    else:
        status, message = 500, InternalServerError.message
    if status >= 500:
        current_app.logger.error("Request failed", exc_info=error)
    return jsonify(message=message), status


class ServiceApi(Api):
    def handle_error(self, error):
        return current_app.make_response(error_response(error))
