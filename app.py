from flask import Flask, request, Response, render_template, flash
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager
from flask_restful import Api

import logging
import logging.config
import os
from database.db import initialize_db
from resources.errors import errors
from resources.reset_pwd_form import PasswordResetForm
from jwt.exceptions import DecodeError, InvalidTokenError
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
env = os.getenv('APP_ENV', 'test')
logger.info("Running mode:" + env)
app.config.from_object(configs[env])

api = Api(app, errors=errors)
bcrypt = Bcrypt(app)
jwt = JWTManager(app)

initialize_db(app)
from resources.routes import initialize_routes
initialize_routes(api)

app.config['CACHE_TYPE'] = 'simple'
cache.init_app(app)

@app.route("/clearCache")
def clear_cache():
    with app.app_context():
        cache.clear()
    return Response("Cache cleared!", status=200, mimetype='application/json')

@app.route("/resetPwd/<token>", methods=["GET"])
def reset_pwd_form(token):
    form = PasswordResetForm(reset_token=token)
    return render_template('web/pwd_reset.html', form=form)

from database.utils import db_reset_pwd
@app.route("/resetPwd", methods=["POST"])
def reset_pwd_action():
    form = PasswordResetForm(request.form)    
    password = request.form['password']
    token = request.form['reset_token']
    if form.validate():
        try:
            db_reset_pwd(token, password)
        except (DecodeError, InvalidTokenError):
            flash('Error: Invalid reset token, please request password reset again in the app.')
        except Exception as e:
            flash('Error: Unknown server error, please request password reset again in the app.')
        # Save the comment here.
        flash('Password has been reset!')
    else:
        flash('Error: Password length must >= 6 and <= 100!')
    
    return render_template('web/pwd_reset.html', form=form)

if __name__ == "__main__":
    logger.info("server starts at port 8000")
    app.run(host='0.0.0.0', port=8000)