from mongoengine import connect

def initialize_db(db_host):
    connect(
        host=db_host
    )
