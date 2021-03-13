import json

from tests.base_case import BaseCase

class TestUserLogin(BaseCase):

    def test_successful_login(self):
        # Given
        email = "jane@gmail.com"
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
        self.assertEqual(str, type(response.json['token']))
        self.assertEqual(200, response.status_code)

    def test_login_with_invalid_email(self):
        # Given
        email = "jane@gmail.com"
        password = "mycoolpassword"
        payload = {
            "email": email,
            "password": password
        }
        response = self.app.post('/api/auth/signup', headers={"Content-Type": "application/json"}, data=json.dumps(payload))

        # When
        payload['email'] = "jane1@gmail.com"
        response = self.app.post('/api/auth/login', headers={"Content-Type": "application/json"}, data=json.dumps(payload))

        # Then
        self.assertEqual("Invalid username or password", response.json['message'])
        self.assertEqual(401, response.status_code)

    def test_login_with_invalid_password(self):
        # Given
        email = "jane@gmail.com"
        password = "mycoolpassword"
        payload = {
            "email": email,
            "password": password
        }
        response = self.app.post('/api/auth/signup', headers={"Content-Type": "application/json"}, data=json.dumps(payload))

        # When
        payload['password'] = "myverycoolpassword"
        response = self.app.post('/api/auth/login', headers={"Content-Type": "application/json"}, data=json.dumps(payload))

        # Then
        self.assertEqual("Invalid username or password", response.json['message'])
        self.assertEqual(401, response.status_code)