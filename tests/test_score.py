import json

from tests.base_case import BaseCase

class TestUserScore(BaseCase):

    def test_update_score(self):
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

        # Get user score
        response = self.app.get('/api/user/getUserScore', headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"})
         # Then
        self.assertEqual(response.get_json()['score'], 0)

        # When
        payload = json.dumps({
            "score": 100
        })

        # create status
        response = self.app.post('/api/user/updateUserScore', headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"}, data=payload)

        # Then
        self.assertEqual(True, response.json['success'])
        self.assertEqual(200, response.status_code)

         # Get user score
        response = self.app.get('/api/user/getUserScore', headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"})
         # Then
        self.assertEqual(response.get_json()['score'], 100)


    
    
    