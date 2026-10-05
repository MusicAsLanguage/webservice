import tempfile
from pathlib import Path

from flask import current_app, request
from flask_jwt_extended import current_user, jwt_required
from flask_restful import Resource
from mongoengine import Q

from database.models import User
from resources.errors import SchemaValidationError, ServiceUnavailableError
from resources.validation import limit_request_body, text
from services.speech_service import levenshtein_distance, score_speech
from services.user_service import user_write


class SpeechScoreApi(Resource):
    levenshtein_distance = staticmethod(levenshtein_distance)
    score = staticmethod(score_speech)

    @jwt_required()
    def post(self):
        lock = current_app.extensions["speech_lock"]
        if not lock.acquire(blocking=False):
            raise ServiceUnavailableError
        try:
            return self.transcribe()
        finally:
            lock.release()

    def transcribe(self):
        limit_request_body(current_app.config["MAX_SPEECH_UPLOAD_BYTES"])
        expected = text(request.form.get("speech_text"), current_app.config["MAX_SPEECH_TEXT_LENGTH"])
        audio = request.files.get("music_file")
        if audio is None or not audio.filename:
            raise SchemaValidationError
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "audio"
            audio.save(path)
            actual = current_app.extensions["transcriber"](
                path, current_app.config["MAX_AUDIO_SECONDS"]
            )
            if not isinstance(actual, str):
                raise TypeError("Transcriber must return text")
            if len(actual) > current_app.config["MAX_SPEECH_TEXT_LENGTH"]:
                raise SchemaValidationError
            score = score_speech(expected, actual)
        with user_write(current_user):
            score_range = Q(score__gte=0, score__lte=2**63 - 1 - score) | Q(score__exists=False)
            updated = User.objects(score_range, id=current_user.id).update_one(
                inc__score=score,
            )
            if updated != 1:
                raise SchemaValidationError
        return {"text": actual, "score": score}, 200
