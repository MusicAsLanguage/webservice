from flask import Flask, request, Response
from flask_caching import Cache
import logging
import logging.config
import json
import traceback

logging.config.fileConfig("logging.conf")
logger = logging.getLogger("web")

app = Flask(__name__)
cache = Cache(app, config={'CACHE_TYPE': 'simple'})

@app.route("/")
def index():
    return "Welcome to Music As Language!"

@app.route("/getLessons")
def get_lessons():
    try:
        result  = json.dumps(get_lesson_metadata())
        #logger.info("lessons: " + result)
        return success_response(result)
    except Exception:
        error = traceback.format_exc()
        logger.info(error)
        return error_response(json.dumps({"error": error}))

@app.route("/clearCache")
def clear_cache():
    with app.app_context():
        cache.clear()
    return success_response("Cache cleared!")

@cache.cached(timeout=0, key_prefix='lesson_metadata')
def get_lesson_metadata():
    with open('data/programs.json') as f:
        logger.info("reading from data/programs.json")
        lesson_metadata = json.load(f)
    return lesson_metadata

def success_response(content):
    """
    Generate successful HTTP response for all APIs

    Args:
        content(string): Json content to be included in a response

    Returns:
        Response: The HTTP Response object
    """
    resp = Response(content, status=200, mimetype='application/json')
    return resp


def error_response(content):
    """
    Generate failed HTTP response for all APIs

    Args:
        content(string): Json content to be included in a response

    Returns:
        Response: The HTTP Response object

    """
    resp = Response(content, status=555, mimetype='application/json')
    return resp

if __name__ == "__main__":
    logger.info("server starts at port 5000")
    app.run()