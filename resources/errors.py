from flask import current_app, jsonify
from flask_jwt_extended.exceptions import JWTExtendedException
from flask_restful import Api
from jwt import PyJWTError
from mongoengine.errors import FieldDoesNotExist, NotUniqueError, ValidationError
from pymongo.errors import DuplicateKeyError
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


class ConflictError(ApiError):
    status = 409
    message = "Account deletion is waiting for in-flight writes; retry deletion"


def error_response(error):
    legacy_envelope = True
    if isinstance(error, ApiError):
        status, message = error.status, error.message
    elif isinstance(error, (FieldDoesNotExist, ValidationError)):
        status, message = 400, SchemaValidationError.message
    elif isinstance(error, (NotUniqueError, DuplicateKeyError)):
        status, message = 409, "A record with these identifiers already exists"
    elif isinstance(error, (JWTExtendedException, PyJWTError)):
        status, message = 401, "Invalid or missing token"
        legacy_envelope = False
    elif isinstance(error, HTTPException):
        status, message = error.code, error.description
        legacy_envelope = False
    else:
        status, message = 500, InternalServerError.message
    if status >= 500:
        current_app.logger.error("Request failed", exc_info=error)
    body = {"message": message}
    if legacy_envelope:
        body["status"] = status
    return jsonify(body), status


class ServiceApi(Api):
    def handle_error(self, error):
        return current_app.make_response(error_response(error))
