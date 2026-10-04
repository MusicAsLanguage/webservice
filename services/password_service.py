from hashlib import sha256

from flask_bcrypt import check_password_hash as bcrypt_check
from flask_bcrypt import generate_password_hash as bcrypt_hash


PREFIX = b"$bcrypt-sha256$"


def generate_password_hash(password):
    # Hash the entire UTF-8 password before bcrypt's 72-byte boundary.
    return PREFIX + bcrypt_hash(sha256(password.encode("utf-8")).hexdigest())


def check_password_hash(hashed, password):
    if hashed.startswith(PREFIX.decode("ascii")):
        return bcrypt_check(hashed[len(PREFIX):], sha256(password.encode("utf-8")).hexdigest())
    # Historical bcrypt hashes cannot distinguish suffixes beyond byte 72.
    return bcrypt_check(hashed, password.encode("utf-8")[:72])
