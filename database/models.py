from .db import db
from flask_bcrypt import generate_password_hash, check_password_hash


class User(db.Document):
    name = db.StringField(required=True, max_length=100)
    email = db.EmailField(required=True, unique=True, max_length=100)
    password = db.StringField(required=True, min_length=6, max_length=100)

    def hash_password(self):
        self.password = generate_password_hash(self.password).decode('utf8')

    def check_password(self, password):
        return check_password_hash(self.password, password)


class Video(db.EmbeddedDocument):
    _id = db.IntField(required=True)
    Name = db.StringField(required=True, max_length=128)
    Url = db.URLField(required=True)
    Description = db.StringField(required=False, max_length=1024)
    LengthInSeconds = db.IntField()

class Activity(db.EmbeddedDocument):
    _id = db.IntField(required=True)
    Name = db.StringField(required=True, max_length=128)
    Description = db.StringField(required=False, max_length=1024)
    BackgroundColor = db.StringField(required=False, max_length=30)
    ImageUrl = db.URLField(required=False)
    Videos = db.ListField(db.EmbeddedDocumentField('Video'))
    Instructions = db.StringField(required=False, max_length=10240)

class Lesson(db.EmbeddedDocument):
    _id = db.IntField(required=True)
    Name = db.StringField(required=True, max_length=128)
    Description = db.StringField(required=False, max_length=1024)
    ImageUrl = db.URLField(required=False)
    IntroVideo = db.EmbeddedDocumentField('Video')
    Activities = db.ListField(db.EmbeddedDocumentField('Activity'))

class Phase(db.EmbeddedDocument):
    _id = db.IntField(required=True)
    Name = db.StringField(required=True, max_length=128)
    Description = db.StringField(required=False, max_length=1024)
    Lessons = db.ListField(db.EmbeddedDocumentField('Lesson'))

class Program(db.Document):
    _id = db.IntField(required=True)
    Name = db.StringField(required=True, unique=True, max_length=128)
    Description = db.StringField(required=False, max_length=1024)
    Phases = db.ListField(db.EmbeddedDocumentField('Phase'))

class ActivityStatus(db.Document):
    #scale 0-10, 0 means not started, 10 means completed
    CompletionStatus = db.IntField(required=True)
    User = db.ReferenceField(User, required=True, dbref=True)
    ActivityId = db.IntField(required=True)
    LessonId = db.IntField(required=True)