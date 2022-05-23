from flask import request
from flask_restful import Resource
from flask_jwt_extended import jwt_required, get_jwt_identity
import logging
import logging.config
from resources.errors import InternalServerError, SchemaValidationError
from mongoengine.errors import FieldDoesNotExist
from database.models import User
import json

logging.config.fileConfig("logging.conf")
logger = logging.getLogger("web")


class GetUserScoreApi(Resource):
    @jwt_required()
    def get(self):
        try:
            userId = json.loads(get_jwt_identity())
            user = User.objects.get(id=userId['_id']['$oid']) 
           
            return {'score': user.score}, 200
        except FieldDoesNotExist:
            raise SchemaValidationError
        except Exception as e:
            raise InternalServerError

class UpdateUserScoreApi(Resource):
    @jwt_required()
    def post(self):
        try:
            score = int(request.get_json()["score"])
            userId = json.loads(get_jwt_identity())
            user = User.objects.get(id=userId['_id']['$oid']) 
            user.update(score=score)
           
            return {'success': True}, 200
        except FieldDoesNotExist:
            raise SchemaValidationError
        except Exception as e:
            raise InternalServerError