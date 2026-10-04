import logging
import os

from flask import Flask, Response, current_app, flash, render_template, request
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager, jwt_required
from mongoengine import get_db

from cache import cache
from config import load_config, validate_config
from database.db import initialize_db
from database.maintenance import prepare_indexes
from database.utils import db_reset_pwd
from resources.errors import ApiError, ServiceApi, error_response
from resources.reset_pwd_form import PasswordResetForm
from resources.routes import initialize_routes
from services.auth_service import initialize_jwt, require_admin
from services.speech_service import WhisperTranscriber


def create_app(environment=None, overrides=None):
    environment = environment or os.getenv("APP_ENV", "dev")
    app = Flask(__name__)
    app.config.from_mapping(load_config(environment))
    app.config.update(overrides or {})
    validate_config(app, environment)

    Bcrypt(app)
    initialize_jwt(JWTManager(app))
    initialize_db(app.config["MONGODB_SETTINGS"])
    cache.init_app(app)
    app.extensions["transcriber"] = app.config.get("TRANSCRIBER") or WhisperTranscriber()
    initialize_routes(ServiceApi(app))
    app.cli.add_command(prepare_indexes)
    app.register_error_handler(Exception, error_response)

    @app.get("/health/ready")
    def ready():
        get_db().command("ping")
        return {"status": "ready"}

    @app.get("/clearCache")
    @jwt_required()
    def clear_cache():
        require_admin()
        cache.clear()
        return Response("Cache cleared!", status=200, mimetype="application/json")

    @app.get("/resetPwd/<token>")
    def reset_pwd_form(token):
        form = PasswordResetForm(reset_token=token)
        return render_template("web/pwd_reset.html", form=form)

    @app.post("/resetPwd")
    def reset_pwd_action():
        form = PasswordResetForm(request.form)
        if form.validate():
            try:
                db_reset_pwd(form.reset_token.data, form.password.data)
            except ApiError as error:
                flash(f"Error: {error.message}")
            except Exception:
                current_app.logger.exception("Password reset failed")
                flash("Error: Unknown server error, please request password reset again in the app.")
            else:
                flash("Password has been reset!")
        else:
            flash("Error: A reset token and a password of 6 to 100 characters are required.")
        return render_template("web/pwd_reset.html", form=form)

    return app


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    create_app().run(host="0.0.0.0", port=8000)
