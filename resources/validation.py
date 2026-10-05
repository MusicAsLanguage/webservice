import math
import re

from flask import current_app, request
from werkzeug.exceptions import RequestEntityTooLarge

from resources.errors import SchemaValidationError


LEGACY_RECORD_FIELDS = {"id", "_id", "User", "UpdateTime"}
LEGACY_USER_FIELDS = {"id", "_id", "name", "password", "score", "UpdateTime"}


def limit_request_body(maximum):
    configured_limit = request.max_content_length
    request.max_content_length = (
        maximum if configured_limit is None else min(configured_limit, maximum)
    )
    if request.content_length in (None, 0) and request.environ.get("wsgi.input_terminated"):
        # Probe one extra byte: Werkzeug can otherwise silently truncate an unknown-length stream.
        limit = request.max_content_length
        request.max_content_length = limit + 1
        try:
            data = request.get_data()
        finally:
            request.max_content_length = limit
        if len(data) > limit:
            raise RequestEntityTooLarge


def json_body(required, optional=()):
    limit_request_body(current_app.config["MAX_JSON_BODY_BYTES"])
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
