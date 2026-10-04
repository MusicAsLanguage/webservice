import tempfile
from pathlib import Path

from flask import current_app, request
from flask_jwt_extended import current_user, jwt_required
from flask_restful import Resource

from resources.errors import SchemaValidationError
from resources.validation import text
from services.speech_service import levenshtein_distance, score_speech


class SpeechScoreApi(Resource):
    levenshtein_distance = staticmethod(levenshtein_distance)
    score = staticmethod(score_speech)

    @jwt_required()
    def post(self):
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
        current_user.update(inc__score=score)
        return {"text": actual, "score": score}, 200
