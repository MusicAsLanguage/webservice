import math
import re

from flask import request

from resources.errors import SchemaValidationError


LEGACY_RECORD_FIELDS = {"id", "_id", "User", "UpdateTime"}
LEGACY_USER_FIELDS = {"id", "_id", "name", "password", "score", "UpdateTime"}


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
    return unicode_text(value)


def password_value(value, minimum=6):
    if not isinstance(value, str) or not minimum <= len(value) <= 100:
        raise SchemaValidationError
    return unicode_text(value)


def unicode_text(value):
    try:
        value.encode("utf-8")
    except UnicodeEncodeError:
        raise SchemaValidationError from None
    return value


def integer(value, minimum=0, maximum=2**63 - 1):
    if isinstance(value, str):
        value = value.strip()
        if not re.fullmatch(r"[+-]?[0-9]+", value):
            raise SchemaValidationError
        digits = value.lstrip("+-").lstrip("0") or "0"
        if len(digits) > 19:
            raise SchemaValidationError
        value = int(("-" if value.startswith("-") else "") + digits)
    elif type(value) is float:
        if not math.isfinite(value) or not value.is_integer() or abs(value) > 2**53 - 1:
            raise SchemaValidationError
        value = int(value)
    if type(value) is not int or value < minimum or value > maximum:
        raise SchemaValidationError
    return value
