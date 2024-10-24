from mongoengine import Document, StringField, EmailField, IntField, URLField, EmbeddedDocument, \
      EmbeddedDocumentField, EmbeddedDocumentListField, DateTimeField, BooleanField, ReferenceField, FloatField
from flask_bcrypt import generate_password_hash, check_password_hash
from datetime import datetime


class User(Document):
    name = StringField(required=True, max_length=100)
    email = EmailField(required=True, unique=True, max_length=100)
    password = StringField(required=True, min_length=6, max_length=100)
    score = IntField(required=False, default=0)
    UpdateTime = DateTimeField(required=False, default=datetime.utcnow)

    def hash_password(self):
        self.password = generate_password_hash(self.password).decode('utf8')

    def check_password(self, password):
        return check_password_hash(self.password, password)

class Video(EmbeddedDocument):
    _id = IntField(required=True)
    Name = StringField(required=True, max_length=128)
    Url = URLField(required=True)
    Description = StringField(required=False, max_length=1024)
    LengthInSeconds = IntField()

class Activity(EmbeddedDocument):
    _id = IntField(required=True)
    Name = StringField(required=True, max_length=128)
    Description = StringField(required=False, max_length=1024)
    BackgroundColor = StringField(required=False, max_length=30)
    ImageUrl = URLField(required=False)
    Videos = EmbeddedDocumentListField(Video)
    Instructions = StringField(required=False, max_length=10240)
    Score = IntField(required=True)
    PracticeMode = BooleanField(required=False, default=False)

class Lesson(EmbeddedDocument):
    _id = IntField(required=True)
    Name = StringField(required=True, max_length=128)
    Description = StringField(required=False, max_length=1024)
    ImageUrl = URLField(required=False)
    IntroVideo = EmbeddedDocumentField(Video)
    Activities = EmbeddedDocumentListField(Activity)

class Phase(EmbeddedDocument):
    _id = IntField(required=True)
    Name = StringField(required=True, max_length=128)
    Description = StringField(required=False, max_length=1024)
    Lessons = EmbeddedDocumentListField(Lesson)

class Song(EmbeddedDocument):
    _id = IntField(required=True)
    Name = StringField(required=True, max_length=128)
    Url = URLField(required=True)
    CaptionUrl = URLField(required=False)
    Description = StringField(required=False, max_length=1024)
    LengthInSeconds = IntField()
    #Instruction/Metronome/Beginner/Intermediate/Superstar/Legend
    Category = StringField(max_length=50)
    Score = IntField(required=True)

class Trophy(EmbeddedDocument):
    _id = IntField(required=True)
    Name = StringField(required=True, max_length=128)
    Url = URLField(required=True)
    Description = StringField(required=False, max_length=1024)
    ScoreThrehold = IntField(required=True)

class RewardConfig(EmbeddedDocument):
    _id = IntField(required=True)
    ActivityRepeat = FloatField(required=False)
    SongRepeat = FloatField(required=False)
    Trophies = EmbeddedDocumentListField(Trophy)

class Program(Document):
    _id = IntField(required=True)
    Name = StringField(required=True, unique=True, max_length=128)
    Description = StringField(required=False, max_length=1024)
    Songs = EmbeddedDocumentListField(Song)
    Phases = EmbeddedDocumentListField(Phase)
    RewardConfig = EmbeddedDocumentField(RewardConfig)

class ActivityStatus(Document):
    #scale 0-10, 0 means not started, 10 means completed
    CompletionStatus = IntField(required=True)
    User = ReferenceField(User, required=True, dbref=True)
    ActivityId = IntField(required=True)
    LessonId = IntField(required=True)
    Repeats = IntField(required=False, default=0)
    UpdateTime = DateTimeField(required=False, default=datetime.utcnow)

class SongPlayingStatus(Document):   
    User = ReferenceField(User, required=True, dbref=True)
    SongName = StringField(required=True, max_length=128)
    Category = StringField(required=True, max_length=50)
    #scale 0-10, 0 means not started, 10 means completed
    CompletionStatus = IntField(required=True)
    Repeats = IntField(required=False, default=0)
    UpdateTime = DateTimeField(required=False, default=datetime.utcnow)

class IncomeMessage(Document):
    Msg = StringField(required=True)
    User = ReferenceField(User, required=True, dbref=True)
    