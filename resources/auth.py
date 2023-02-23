from flask import Response, request
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt_identity
from database.models import User
from flask_restful import Resource
from mongoengine.errors import FieldDoesNotExist, NotUniqueError, DoesNotExist
from resources.errors import SchemaValidationError, EmailAlreadyExistsError, UnauthorizedError, InternalServerError
import datetime
import json

class SignupApi(Resource):
    def post(self):
        try:
            body = request.get_json()
            user =  User(**body)
            user.hash_password()
            user.save()
            id = user.id
            return {'id': str(id)}, 200
        except FieldDoesNotExist:
            raise SchemaValidationError
        except NotUniqueError:
            raise EmailAlreadyExistsError
        except Exception as e:
            raise InternalServerError

class LoginApi(Resource):
    def post(self):
        try:
            body = request.get_json()
            user = User(**body)

            activeUser = User.objects.get(email = user.email)            
            authorized = activeUser.check_password(user.password)
            
            if not authorized:
                raise UnauthorizedError

            activeUser.password = ""                       
            access_token = create_access_token(identity = activeUser.to_json(), expires_delta = False, fresh = True)            
            refresh_token = create_refresh_token(identity = str(activeUser.id), expires_delta = False)
            return {'token': access_token, 'refresh_token': refresh_token}, 200
        except (UnauthorizedError, DoesNotExist):
            raise UnauthorizedError
        except Exception as e:
            raise InternalServerError

class TokenRefreshApi(Resource):
    @jwt_required(refresh=True)
    def post(self):
        try:            
            # retrive the user's identity from the refresh token using a Flask-JWT-Extended built-in method    
            userId = get_jwt_identity() 
            user = User.objects.get(id=userId)
            user.password = "" 
            # return a non-fresh token for the user
            new_token = create_access_token(identity=user.to_json(), fresh=False)
            return {'token': new_token}, 200
        except Exception as e:
            raise InternalServerError  
            
            
            