from flask import Response, request
from flask_jwt_extended import current_user, jwt_required
from flask_restful import Resource

from cache import cache
from database.models import ActivityStatus, Program, SongPlayingStatus
from resources.errors import SchemaValidationError
from resources.validation import integer, json_body, text
from services.auth_service import require_admin
from services.progress_service import update_progress


@cache.cached(key_prefix="lesson_metadata")
def get_lesson_metadata():
    return Program.objects().to_json()


class GetLessonsApi(Resource):
    def get(self):
        return Response(get_lesson_metadata(), mimetype="application/json")


class CreateLessonsApi(Resource):
    @jwt_required()
    def post(self):
        require_admin()
        body = request.get_json()
        if not isinstance(body, list) or any(not isinstance(p, dict) for p in body):
            raise SchemaValidationError
        programs = [Program(**p) for p in body]
        for program in programs:
            program.validate()
        if len({p._id for p in programs}) != len(programs):
            raise SchemaValidationError
        if len({p.Name for p in programs}) != len(programs):
            raise SchemaValidationError
        for program in programs:
            if Program.objects(_id__ne=program._id, Name=program.Name).first():
                raise SchemaValidationError
        try:
            for program in programs:
                Program.objects(_id=program._id).modify(
                    upsert=True,
                    set__Name=program.Name,
                    set__Description=program.Description,
                    set__Songs=program.Songs,
                    set__Phases=program.Phases,
                    set__RewardConfig=program.RewardConfig,
                )
        finally:
            # A database failure can leave a partially applied batch; never keep its old cache.
            cache.delete("lesson_metadata")
        return {"id": str([p._id for p in programs])}, 200


class GetActivityStatusApi(Resource):
    @jwt_required()
    def get(self):
        statuses = ActivityStatus.objects(User=current_user._get_current_object())
        return Response(statuses.to_json(), mimetype="application/json")


class UpdateActivityStatusApi(Resource):
    @jwt_required()
    def post(self):
        body = json_body({"CompletionStatus", "ActivityId", "LessonId"}, {"Repeats"})
        status = ActivityStatus(
            User=current_user._get_current_object(),
            CompletionStatus=integer(body["CompletionStatus"], maximum=10),
            ActivityId=integer(body["ActivityId"]),
            LessonId=integer(body["LessonId"]),
            Repeats=integer(body.get("Repeats", 0)),
        )
        status.validate()
        saved = update_progress(status, ("User", "ActivityId", "LessonId"))
        return {"id": str(saved.id)}, 200


class GetSongPlayingStatusApi(Resource):
    @jwt_required()
    def get(self):
        statuses = SongPlayingStatus.objects(User=current_user._get_current_object())
        return Response(statuses.to_json(), mimetype="application/json")


class UpdateSongPlayingStatusApi(Resource):
    @jwt_required()
    def post(self):
        body = json_body({"CompletionStatus", "SongName", "Category"}, {"Repeats"})
        status = SongPlayingStatus(
            User=current_user._get_current_object(),
            CompletionStatus=integer(body["CompletionStatus"], maximum=10),
            SongName=text(body["SongName"], 128),
            Category=text(body["Category"], 50),
            Repeats=integer(body.get("Repeats", 0)),
        )
        status.validate()
        saved = update_progress(status, ("User", "SongName"))
        return {"id": str(saved.id)}, 200
