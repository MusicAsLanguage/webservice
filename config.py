import os
import json
class BaseConfig(object):
    DEBUG = True
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