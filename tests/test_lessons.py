import json
import os
from tests.base_case import BaseCase

class TestLessonsAPI(BaseCase):

    def test_create_lessons(self):
        # Given
        payload = self.read_file('data/programs.json')            
        
        # When
        response = self.app.post('/api/lesson/createLessons', headers={"Content-Type": "application/json"}, data=payload)

        # Then
        self.assertEqual(str, type(response.json['id']))
        self.assertEqual(200, response.status_code)

    def test_get_lessons(self):
        # Given
        payload = self.read_file('data/programs.json') 
        
        # When
        response = self.app.post('/api/lesson/createLessons', headers={"Content-Type": "application/json"}, data=payload)
        response = self.app.get('/api/lesson/getLessons')
        print(response.get_json())       
        self.assertEqual(8, len(response.json[0]['Songs']))
        # Then
        self.assertEqual(200, response.status_code)
