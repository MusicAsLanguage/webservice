from flask import request

from resources.errors import SchemaValidationError


def json_body(required, optional=()):
    body = request.get_json()
    if not isinstance(body, dict) or not set(required) <= body.keys():
        raise SchemaValidationError
    if body.keys() - set(required) - set(optional):
        raise SchemaValidationError
    return body


def text(value, maximum=100):
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise SchemaValidationError
    return value


def password_value(value):
    text(value)
    if len(value) < 6 or len(value.encode("utf-8")) > 72:
        raise SchemaValidationError
    return value


def integer(value, minimum=0, maximum=2**63 - 1):
    if type(value) is not int or value < minimum or value > maximum:
        raise SchemaValidationError
    return value
