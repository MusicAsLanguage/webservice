import json
import os
from tests.base_case import BaseCase

class TestLessonsAPI(BaseCase):

    def test_create_lessons(self):
        # Given
        email = "AdminUser@mal.com"
        password = "mycoolpassword"
        payload = json.dumps({
            "name": "Jane Doe",
            "email": email,
            "password": password
        })
        response = self.app.post('/api/auth/signup', headers={"Content-Type": "application/json"}, data=payload)

        # When
        response = self.app.post('/api/auth/login', headers={"Content-Type": "application/json"}, data=payload)

        # Then
        token = response.json['token']

        # Given
        payload = self.read_file('data/programs.json')            
        
        # When
        response = self.app.post('/api/lesson/createLessons', headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"}, data=payload)

        # Then
        self.assertEqual(str, type(response.json['id']))
        self.assertEqual(200, response.status_code)

    def test_get_lessons(self):
        # Given
        email = "AdminUser@mal.com"
        password = "mycoolpassword"
        payload = json.dumps({
            "name": "Jane Doe",
            "email": email,
            "password": password
        })
        response = self.app.post('/api/auth/signup', headers={"Content-Type": "application/json"}, data=payload)

        # When
        response = self.app.post('/api/auth/login', headers={"Content-Type": "application/json"}, data=payload)

        # Then
        token = response.json['token']
        # Given
        payload = self.read_file('data/programs.json') 
        
        # When
        response = self.app.post('/api/lesson/createLessons', headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"}, data=payload)
        response = self.app.get('/api/lesson/getLessons')
        print(response.get_json())       
        self.assertTrue(len(response.json[0]['Songs']) > 0)
        # Then
        self.assertEqual(200, response.status_code)
