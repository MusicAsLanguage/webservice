from flask import request, render_template
from flask_jwt_extended import create_access_token
from database.models import User
from flask_restful import Resource
import datetime
from resources.errors import SchemaValidationError, InternalServerError, \
    EmailDoesnotExistsError, BadTokenError
from jwt.exceptions import DecodeError, InvalidTokenError
from services.mail_service import send_email
from database.utils import db_reset_pwd
import os

env = os.getenv('APP_ENV', 'test')
class ForgotPassword(Resource):
    def post(self):
        url = request.host_url + 'resetPwd/'
        if env == 'prod':
            url = url.replace("http:", "https:")
        try:
            body = request.get_json()
            email = body.get('email')
            if not email:
                raise SchemaValidationError

            user = User.objects.get(email=email)
            if not user:
                raise EmailDoesnotExistsError

            expires = datetime.timedelta(hours=24)
            reset_token = create_access_token(str(user.id), expires_delta=expires)

            send_email('[MusicAsLanguage] Reset Your Password',
                              sender='musicaslanguage@sf-ns.org',
                              recipients=[user.email],
                              text_body=render_template('email/reset_password.txt',
                                                        url=url + reset_token),
                              html_body=render_template('email/reset_password.html',
                                                        url=url + reset_token))
            return {'status': 'Password reset email has been sent to ' + email}, 200
        except SchemaValidationError:
            raise SchemaValidationError
        except EmailDoesnotExistsError:
            raise EmailDoesnotExistsError
        except Exception as e:
            raise InternalServerError

class ResetPassword(Resource):
    def post(self):
        try:
            body = request.get_json()
            reset_token = body.get('reset_token')
            password = body.get('password')

            if not reset_token or not password:
                raise SchemaValidationError

            db_reset_pwd(reset_token, password)            
            return {'status': 'Password reset was successful!'}, 200
        except SchemaValidationError:
            raise SchemaValidationError
        except (DecodeError, InvalidTokenError):
            raise BadTokenError
        except Exception as e:
            raise InternalServerError