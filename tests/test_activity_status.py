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

        # create status
        response = self.app.post('/api/activity/updateStatus', headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"}, data=payload)

        # Then
        self.assertEqual(str, type(response.json['id']))
        self.assertEqual(200, response.status_code)

        # Get activity status
        response = self.app.get('/api/activity/getStatus', headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"})

        # Then
        self.assertEqual(response.get_json()[0]['CompletionStatus'], 5)


        # When
        payload = json.dumps({
            "CompletionStatus": 6,
            "ActivityId": 1,
            "LessonId": 1,
            "Repeats": 1
        })
        
        # update status
        response = self.app.post('/api/activity/updateStatus', headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"}, data=payload)

        # Then
        self.assertEqual(str, type(response.json['id']))
        self.assertEqual(200, response.status_code)

        # Get activity status
        response = self.app.get('/api/activity/getStatus', headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"})

        # Then
        self.assertEqual(response.get_json()[0]['CompletionStatus'], 6)
        self.assertEqual(response.get_json()[0]['Repeats'], 1)
        self.assertEqual(200, response.status_code)
    
    def test_update_song_status(self):
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

        # Then
        self.assertEqual(str, type(response.json['id']))
        self.assertEqual(200, response.status_code)

        # Get activity status
        response = self.app.get('/api/activity/getSongPlayingStatus', headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"})

        # Then
        self.assertEqual(response.get_json()[0]['CompletionStatus'], 5)


        # When
        payload = json.dumps({            
            "SongName": "Lovely Day - Loop",
            "Category": "Beginner",
            "CompletionStatus": 6,
            "Repeats": 1,
        })
        
        # update status
        response = self.app.post('/api/activity/updateSongPlayingStatus', headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"}, data=payload)

        # Then
        self.assertEqual(str, type(response.json['id']))
        self.assertEqual(200, response.status_code)

        # Get activity status
        response = self.app.get('/api/activity/getSongPlayingStatus', headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"})

        # Then
        self.assertEqual(response.get_json()[0]['CompletionStatus'], 6)
        self.assertEqual(response.get_json()[0]['Repeats'], 1)
        self.assertEqual(200, response.status_code)
    