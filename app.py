from flask import Flask, request, Response, jsonify
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager
from flask_restful import Api

import logging
import logging.config
import os
from database.db import initialize_db
from resources.routes import initialize_routes
from cache import cache
import config

logging.config.fileConfig("logging.conf")
logger = logging.getLogger("web")

app = Flask(__name__)

configs = {
    "dev": config.DevelopmentConfig,
    "test": config.TestingConfig,
    "prod": config.ProductionConfig
}

#get APP_ENV from environment setting, dev/test/prod, default to dev if not set
env = os.getenv('APP_ENV', 'dev')
logger.info("Running mode:" + env)
app.config.from_object(configs[env])

api = Api(app)
bcrypt = Bcrypt(app)
jwt = JWTManager(app)

initialize_db(app)
initialize_routes(api)

app.config['CACHE_TYPE'] = 'simple'
cache.init_app(app)

@app.route("/clearCache")
def clear_cache():
    with app.app_context():
        cache.clear()
    return Response("Cache cleared!", status=200, mimetype='application/json')

if __name__ == "__main__":
    logger.info("server starts at port 5000")
    app.run()