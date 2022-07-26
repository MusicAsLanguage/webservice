from .db import db
from flask_bcrypt import generate_password_hash, check_password_hash


class User(db.Document):
    name = db.StringField(required=True, max_length=100)
    email = db.EmailField(required=True, unique=True, max_length=100)
    password = db.StringField(required=True, min_length=6, max_length=100)
    score = db.IntField(required=False, default=0)

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
    Score = db.IntField(required=True)
    PracticeMode = db.BooleanField(required=False, default=False)

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

class Song(db.EmbeddedDocument):
    _id = db.IntField(required=True)
    Name = db.StringField(required=True, max_length=128)
    Url = db.URLField(required=True)
    Description = db.StringField(required=False, max_length=1024)
    LengthInSeconds = db.IntField()
    #Instruction/Metronome/Beginner/Intermediate/Superstar/Legend
    Category = db.StringField(max_length=50)
    Score = db.IntField(required=True)

class Trophy(db.EmbeddedDocument):
    _id = db.IntField(required=True)
    Name = db.StringField(required=True, max_length=128)
    Url = db.URLField(required=True)
    Description = db.StringField(required=False, max_length=1024)
    ScoreThrehold = db.IntField(required=True)

class RewardConfig(db.EmbeddedDocument):
    _id = db.IntField(required=True)
    ActivityRepeat = db.FloatField(required=False)
    SongRepeat = db.FloatField(required=False)
    Trophies = db.ListField(db.EmbeddedDocumentField("Trophy"))

class Program(db.Document):
    _id = db.IntField(required=True)
    Name = db.StringField(required=True, unique=True, max_length=128)
    Description = db.StringField(required=False, max_length=1024)
    Songs = db.ListField(db.EmbeddedDocumentField('Song'))
    Phases = db.ListField(db.EmbeddedDocumentField('Phase'))
    RewardConfig = db.EmbeddedDocumentField("RewardConfig")

class ActivityStatus(db.Document):
    #scale 0-10, 0 means not started, 10 means completed
    CompletionStatus = db.IntField(required=True)
    User = db.ReferenceField(User, required=True, dbref=True)
    ActivityId = db.IntField(required=True)
    LessonId = db.IntField(required=True)
    Repeats = db.IntField(required=False, default=0)

class SongPlayingStatus(db.Document):   
    User = db.ReferenceField(User, required=True, dbref=True)
    SongName = db.StringField(required=True, max_length=128)
    Category = db.StringField(required=True, max_length=50)
    #scale 0-10, 0 means not started, 10 means completed
    CompletionStatus = db.IntField(required=True)
    Repeats = db.IntField(required=False, default=0)

class IncomeMessage(db.Document):
    Msg = db.StringField(required=True)
    User = db.ReferenceField(User, required=True, dbref=True)
    