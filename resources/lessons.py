from flask import Response, request
from flask_restful import Resource
from flask_jwt_extended import jwt_required
import logging
import logging.config
from cache import cache
from resources.errors import InternalServerError, SchemaValidationError
from mongoengine.errors import FieldDoesNotExist, NotUniqueError, DoesNotExist
from database.models import Program
import json
from json import JSONEncoder

logging.config.fileConfig("logging.conf")
logger = logging.getLogger("web")

class ProgramsEncoder(JSONEncoder):
        def default(self, o):
            return o.__dict__

@cache.cached(timeout=0, key_prefix='lesson_metadata')
def get_lesson_metadata():
    #with open('data/programs.json') as f:
    #    logger.info("reading from data/programs.json")
    #    lesson_metadata = json.load(f)
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
    def post(self):
        try:
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
        except FieldDoesNotExist:
            raise SchemaValidationError
        except Exception as e:
            raise InternalServerError

