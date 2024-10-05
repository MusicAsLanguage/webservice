import os
import json
class BaseConfig(object):
    DEBUG = True
    SECRET_KEY = os.getenv('SECRET_KEY', 'DefaultKey')
class DevelopmentConfig(BaseConfig):
    MONGODB_SETTINGS = json.loads(os.getenv('MONGODB_SETTINGS', '{"host": "localhost", "db": "MusicAsLanguage", "port": 27017, "username":"maluser","password":"Mal123!"}'))
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 't1NP63m4wnBg8nyHYKfmc2TpCOGI4nss')
class TestingConfig(BaseConfig):
    DEBUG = False    
    MONGODB_SETTINGS = json.loads(os.getenv('MONGODB_SETTINGS', '{"host": "localhost", "db": "testdb", "port": 27017,"username":"maluser","password":"Mal123!"}'))
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'DefaultKey')
class ProductionConfig(BaseConfig):
    DEBUG = False
    if os.getenv('MONGODB_SETTINGS'):
        MONGODB_SETTINGS = json.loads(os.getenv('MONGODB_SETTINGS'))
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'DefaultKey')