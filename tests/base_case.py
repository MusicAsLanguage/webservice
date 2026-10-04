import os
import unittest
from pathlib import Path
from unittest.mock import Mock
from uuid import uuid4

import mongomock
from mongoengine import disconnect, get_connection, get_db
from pymongo.uri_parser import parse_uri

from app import create_app
from cache import cache


class BaseCase(unittest.TestCase):
    def setUp(self):
        self.database_name = "mal_test_" + uuid4().hex
        uri = os.getenv("TEST_MONGODB_URI")
        if uri:
            if parse_uri(uri)["database"]:
                raise ValueError("TEST_MONGODB_URI must not contain a database name")
            settings = {"db": self.database_name, "host": uri}
        else:
            settings = {
                "db": self.database_name,
                "host": "mongodb://localhost",
                "mongo_client_class": mongomock.MongoClient,
            }
        self.mail = Mock()
        self.transcriber = Mock(return_value="hello")
        self.flask_app = create_app("test", {
            "MONGODB_SETTINGS": settings,
            "SECRET_KEY": "test-session-key-not-for-production",
            "JWT_SECRET_KEY": "test-signing-key-not-for-production",
            "ADMIN_USERS": "AdminUser@mal.com",
            "MAIL_SENDER": self.mail,
            "TRANSCRIBER": self.transcriber,
            "BCRYPT_LOG_ROUNDS": 4,
            "PUBLIC_BASE_URL": "https://example.test",
        })
        self.addCleanup(self.clean_database)
        self.app = self.flask_app.test_client()

    def clean_database(self):
        database = get_db()
        if database.name != self.database_name or not database.name.startswith("mal_test_"):
            raise RuntimeError("Refusing to clean a database not owned by this test")
        try:
            get_connection().drop_database(self.database_name)
            with self.flask_app.app_context():
                cache.clear()
        finally:
            disconnect()

    def read_file(self, path):
        return (Path(__file__).resolve().parents[1] / path).read_text(encoding="utf-8")
