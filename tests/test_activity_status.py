import json

from tests.base_case import BaseCase

class TestUserLogin(BaseCase):

    def test_update_activity_status(self):
        # Given
        email = "jane@gmail.com"
        password = "mycoolpassword"
        payload = json.dumps({
            "name": "Jane Doe",
            "email": email,
            "password": password
        })
        response = self.app.post('/api/auth/signup', headers={"Content-Type": "application/json"}, data=payload)

        response = self.app.post('/api/auth/login', headers={"Content-Type": "application/json"}, data=payload)

        token = response.json['token']

        payload = self.read_file('data/programs.json') 

        response = self.app.post('/api/lesson/createLessons', headers={"Content-Type": "application/json"}, data=payload)

        # When
        payload = json.dumps({
            "CompletionStatus": 5,
            "ActivityId": 1,
            "LessonId": 1
        })
        response = self.app.post('/api/activity/updateStatus', headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"}, data=payload)

        # Then
        self.assertEqual(str, type(response.json['id']))
        self.assertEqual(200, response.status_code)

        # Get activity status
        response = self.app.get('/api/activity/getStatus', headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"})

        # Then
        print(response.get_json())
        self.assertEqual(200, response.status_code)
    