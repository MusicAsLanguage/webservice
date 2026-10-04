from mongoengine import connect

def initialize_db(db_host):
    settings = {"host": db_host} if isinstance(db_host, str) else dict(db_host)
    settings.setdefault("serverSelectionTimeoutMS", 5000)
    return connect(**settings)
