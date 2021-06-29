import json

from tests.base_case import BaseCase

class TestSendMsg(BaseCase):

    def test_send_msg(self):
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
        
        # When
        payload = json.dumps({
            "Msg": "This is a Test"           
        })

        # create status
        response = self.app.post('/api/msg/send', headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"}, data=payload)

        # Then
        self.assertEqual(str, type(response.json['id']))
        self.assertEqual(200, response.status_code)

    