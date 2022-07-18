import json

from tests.base_case import BaseCase

class TestUserDeletion(BaseCase):

    def test_user_deletion(self):
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
            "SongName": "Lovely Day - Loop",
            "Category": "Beginner",
            "CompletionStatus": 5
        })

        # create status
        response = self.app.post('/api/activity/updateSongPlayingStatus', headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"}, data=payload)

         # When
        payload = json.dumps({
            "CompletionStatus": 5,
            "ActivityId": 1,
            "LessonId": 1
        })

        # create status
        response = self.app.post('/api/activity/updateStatus', headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"}, data=payload)


        # delete user
        response = self.app.delete('/api/user/deleteUserAndData', headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"})

        self.assertEqual(True, response.json['success'])
        self.assertEqual(200, response.status_code)