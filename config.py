import os
import json
class BaseConfig(object):
    DEBUG = True
    # the following email configuration is only for dev purpose
    MAIL_SERVER = "smtp.gmail.com"
    MAIL_PORT = "465"
    MAIL_USE_SSL = True
    MAIL_USERNAME = "musicaslanguage.test@gmail.com"
    MAIL_PASSWORD = ""
    #send grid is used for email sending in production
    SEND_GRID_KEY = ""
class DevelopmentConfig(BaseConfig):
    MONGODB_SETTINGS = json.loads(os.getenv('MONGODB_SETTINGS', '{"host": "mongodb://localhost/MusicAsLanguage","username":"maluser","password":"Mal123!"}'))
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 't1NP63m4wnBg8nyHYKfmc2TpCOGI4nss')
class TestingConfig(BaseConfig):
    DEBUG = False    
    MONGODB_SETTINGS = json.loads(os.getenv('MONGODB_SETTINGS', '{"host": "mongodb://localhost/testdb","username":"maluser","password":"Mal123!"}'))
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'DefaultKey')
class ProductionConfig(BaseConfig):
    DEBUG = False
    if os.getenv('MONGODB_SETTINGS'):
        MONGODB_SETTINGS = json.loads(os.getenv('MONGODB_SETTINGS'))
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'DefaultKey')
    SEND_GRID_KEY = os.getenv('SEND_GRID_KEY', 'DefaultKey')