from flask import request
from flask_restful import Resource
from flask_jwt_extended import jwt_required, get_jwt_identity
import logging
import logging.config
from resources.errors import InternalServerError, SchemaValidationError
from mongoengine.errors import FieldDoesNotExist
from database.models import ActivityStatus, User, SongPlayingStatus
import json

logging.config.fileConfig("logging.conf")
logger = logging.getLogger("web")


class DeleteUserAndDataApi(Resource):
    @jwt_required()
    def delete(self):
        try:
            userId = json.loads(get_jwt_identity())
            user = User.objects.get(id=userId['_id']['$oid'])
            activityStatus = ActivityStatus.objects(User = user)
            if activityStatus:
                for status in activityStatus:
                    status.delete()
            songPlayingStatus = SongPlayingStatus.objects(User = user)
            if songPlayingStatus:
                for song in songPlayingStatus:
                    song.delete()
            user.delete()
            return {'success': True}, 200
        except FieldDoesNotExist:
            raise SchemaValidationError
        except Exception as e:
            raise InternalServerError