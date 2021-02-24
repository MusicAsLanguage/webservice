from flask_restful import Resource
from flask_jwt_extended import jwt_required
import logging
import logging.config
import json
import traceback
from cache import cache
from resources.errors import InternalServerError

logging.config.fileConfig("logging.conf")
logger = logging.getLogger("web")


@cache.cached(timeout=0, key_prefix='lesson_metadata')
def get_lesson_metadata():
    with open('data/programs.json') as f:
        logger.info("reading from data/programs.json")
        lesson_metadata = json.load(f)
    return lesson_metadata

class GetLessonsApi(Resource):
    def get(self):
        try:
            result = get_lesson_metadata()
            #logger.info("lessons: " + result)
            return result, 200
        except Exception:
            error = traceback.format_exc()
            logger.info(error)
            raise InternalServerError

