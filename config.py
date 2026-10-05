import os
from datetime import timedelta


def load_config(environment):
    if environment not in {"dev", "test", "prod"}:
        raise ValueError("APP_ENV must be dev, test, or prod")
    settings = {
        "TESTING": environment == "test",
        "DEBUG": environment == "dev",
        "SECRET_KEY": os.getenv("SECRET_KEY"),
        "JWT_SECRET_KEY": os.getenv("JWT_SECRET_KEY"),
        "MONGODB_SETTINGS": os.getenv("MONGODB_SETTINGS"),
        "SEND_GRID_KEY": os.getenv("SEND_GRID_KEY"),
        "ADMIN_USERS": os.getenv("ADMIN_USERS", "AdminUser@mal.com"),
        "JWT_ACCESS_TOKEN_EXPIRES": timedelta(hours=1),
        "JWT_REFRESH_TOKEN_EXPIRES": timedelta(days=30),
        "CACHE_TYPE": "SimpleCache",
        "CACHE_DEFAULT_TIMEOUT": 60,
        "MAX_JSON_BODY_BYTES": 256 * 1024,
        "MAX_LESSON_BODY_BYTES": 16 * 1024 * 1024,
        "MAX_SPEECH_UPLOAD_BYTES": 10 * 1024 * 1024,
        "MAX_SPEECH_TEXT_LENGTH": 2000,
        "MAX_AUDIO_SECONDS": 120,
        "PUBLIC_BASE_URL": os.getenv("PUBLIC_BASE_URL"),
    }
    if environment != "prod":
        settings["SECRET_KEY"] = settings["SECRET_KEY"] or "local-development-session-key-only"
        settings["JWT_SECRET_KEY"] = settings["JWT_SECRET_KEY"] or "local-development-signing-key-only"
        settings["MONGODB_SETTINGS"] = settings["MONGODB_SETTINGS"] or (
            "mongodb://localhost:27017/MusicAsLanguage"
        )
    return settings


def validate_config(app, environment):
    if environment == "prod":
        for key in ("SECRET_KEY", "JWT_SECRET_KEY"):
            if not isinstance(app.config[key], str) or len(app.config[key]) < 32:
                raise ValueError(f"{key} must be explicitly configured with at least 32 characters")
        if not app.config["MONGODB_SETTINGS"]:
            raise ValueError("MONGODB_SETTINGS must be explicitly configured")
        if not (app.config["PUBLIC_BASE_URL"] or "").startswith("https://"):
            raise ValueError("PUBLIC_BASE_URL must be the public HTTPS URL")
    app.config["ADMIN_USERS"] = {
        email.strip().lower() for email in app.config["ADMIN_USERS"].split(",") if email.strip()
    }
