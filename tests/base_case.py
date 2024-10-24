import os
import unittest

from app import app
from mongoengine import disconnect, get_db

class BaseCase(unittest.TestCase):

    def setUp(self):
        self.app = app.test_client()
        self.clean_database()
        print("Finish test setUp")

    def clean_database(self):
        # Get the database object
        db = get_db()
        # List all collections
        collections = db.list_collection_names()
        # Drop each collection
        for collection in collections:
            db.drop_collection(collection)

    def tearDown(self):
        self.clean_database()
        disconnect()
        print("Finish test tearDown")
    
    
    def read_file(self, path):
        directory_path = os.getcwd()
        with open(os.path.join(directory_path, path), 'r') as json_file:
            return json_file.read()