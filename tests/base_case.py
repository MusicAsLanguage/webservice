  
import os
import unittest

from app import app
from database.db import db


class BaseCase(unittest.TestCase):

    def setUp(self):
        self.app = app.test_client()
        self.db = db.get_db()

    def tearDown(self):
        # Delete Database collections after the test is complete
        for collection in self.db.list_collection_names():
            self.db.drop_collection(collection)
    
    def read_file(self, path):
        directory_path = os.getcwd()
        with open(os.path.join(directory_path, path), 'r') as json_file:
            return json_file.read()