from flask import Response, request
from flask_restful import Resource
from flask_jwt_extended import jwt_required, get_jwt_identity
import logging
import logging.config
from cache import cache
from resources.errors import InternalServerError, SchemaValidationError, UnauthorizedError
from mongoengine.errors import FieldDoesNotExist, NotUniqueError, DoesNotExist
from database.models import Program, ActivityStatus, User, SongPlayingStatus
from json import JSONEncoder
import json
import os

logging.config.fileConfig("logging.conf")
logger = logging.getLogger("web")

ADMIN_USERS = os.getenv('ADMIN_USERS', 'AdminUser@mal.com').lower()

@cache.cached(timeout=0, key_prefix='lesson_metadata')
def get_lesson_metadata():
    programs = Program.objects().to_json()
    return programs
class GetLessonsApi(Resource):
    def get(self):
        try:
            result = get_lesson_metadata()
            #logger.info("lessons: " + result)
            return Response(result, mimetype="application/json", status=200)
        except Exception:
            raise InternalServerError

class CreateLessonsApi(Resource):
    @jwt_required()
    def post(self):
        try:
            userId = json.loads(get_jwt_identity())
            user = User.objects.get(id=userId['_id']['$oid'])
            if user.email.lower() not in ADMIN_USERS:
                raise UnauthorizedError
                
            programs = request.get_json()
            ids = []
            if len(programs) > 0:
                for p in programs:
                    try:
                        exist_programs = Program.objects.get(_id = p['_id'])
                        if exist_programs:
                            exist_programs.delete()
                    except:
                        pass
                    program = Program(**p)
                    program.save()
                    ids.append(program._id)
            return {'id': str(ids)}, 200
        except UnauthorizedError as e:
            raise e
        except FieldDoesNotExist:
            raise SchemaValidationError
        except Exception as e:
            raise InternalServerError

class GetActivityStatusApi(Resource):
    @jwt_required()
    def get(self):
        try:
            userId = json.loads(get_jwt_identity())
            user = User.objects.get(id=userId['_id']['$oid'])
            activityStatus = ActivityStatus.objects(User = user)
            return Response(activityStatus.to_json(), mimetype="application/json", status=200)
        except Exception as e:
            raise InternalServerError

class UpdateActivityStatusApi(Resource):
    @jwt_required()
    def post(self):
        try:
            status = request.get_json()
            activityStatus = ActivityStatus(**status)
            userId = json.loads(get_jwt_identity())
            user = User.objects.get(id=userId['_id']['$oid'])
            activityId = activityStatus.ActivityId
            lessonId = activityStatus.LessonId                 
            try:
                existActivityStatus = ActivityStatus.objects.get(User = user, ActivityId = activityId, LessonId = lessonId)
                if existActivityStatus.CompletionStatus != activityStatus.CompletionStatus:
                    existActivityStatus.update(CompletionStatus = activityStatus.CompletionStatus)
                if existActivityStatus.Repeats != activityStatus.Repeats:
                    existActivityStatus.update(Repeats = activityStatus.Repeats)
                activityStatus = existActivityStatus
            except DoesNotExist:
                activityStatus.User = user
                activityStatus.save()
           
            return {'id': str(activityStatus.id)}, 200
        except FieldDoesNotExist:
            raise SchemaValidationError
        except Exception as e:
            raise InternalServerError

class GetSongPlayingStatusApi(Resource):
    @jwt_required()
    def get(self):
        try:
            userId = json.loads(get_jwt_identity())
            user = User.objects.get(id=userId['_id']['$oid'])
            songPlayingStatus = SongPlayingStatus.objects(User = user)
            return Response(songPlayingStatus.to_json(), mimetype="application/json", status=200)
        except Exception as e:
            raise InternalServerError

class UpdateSongPlayingStatusApi(Resource):
    @jwt_required()
    def post(self):
        try:
            status = request.get_json()
            songPlayingStatus = SongPlayingStatus(**status)
            userId = json.loads(get_jwt_identity())
            user = User.objects.get(id=userId['_id']['$oid'])
            songName = songPlayingStatus.SongName            
            try:
                existSongPlayingStatus = SongPlayingStatus.objects.get(User = user, SongName = songName)
                if existSongPlayingStatus.CompletionStatus != songPlayingStatus.CompletionStatus:
                    existSongPlayingStatus.update(CompletionStatus = songPlayingStatus.CompletionStatus)
                if existSongPlayingStatus.Repeats != songPlayingStatus.Repeats:
                    existSongPlayingStatus.update(Repeats = songPlayingStatus.Repeats)
                songPlayingStatus = existSongPlayingStatus
            except DoesNotExist:
                songPlayingStatus.User = user
                songPlayingStatus.save()
           
            return {'id': str(songPlayingStatus.id)}, 200
        except FieldDoesNotExist:
            raise SchemaValidationError
        except Exception as e:
            raise InternalServerError
