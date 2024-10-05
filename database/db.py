from mongoengine import connect

def initialize_db(app):
    connect(
        app.config['MONGODB_SETTINGS']['db']
    )
