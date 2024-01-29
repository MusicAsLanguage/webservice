from flask import request
from flask_restful import Resource
from flask_jwt_extended import jwt_required, get_jwt_identity
import json
import logging
import logging.config
from database.models import User
from resources.errors import InternalServerError, FilePermissionError
import os
import tempfile
import whisper

logging.config.fileConfig("logging.conf")
logger = logging.getLogger("web")

model = whisper.load_model("tiny")

class SpeechScoreApi(Resource):

    @staticmethod
    
    def levenshtein_distance(s1, s2):
        if len(s1) < len(s2):
            return SpeechScoreApi.levenshtein_distance(s2, s1)

        # If one of the strings is empty
        if len(s2) == 0:
            return len(s1)

        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row

        return previous_row[-1]

    @staticmethod

    def score(expected_speech_text, actual_speech_text):
        length = max(len(expected_speech_text), len(actual_speech_text))
        # normalize by length, high score wins
        fDist = float(length - SpeechScoreApi.levenshtein_distance(expected_speech_text, actual_speech_text)) / float(length)
        word_count = len(expected_speech_text.split())
        return (int)(fDist * 10 * word_count)
    
    @jwt_required()
    def post(self):
        try:
            expected_speech_text = request.form["speech_text"]
            if expected_speech_text is None:
                return {'message': 'No speech_text in the request form'}, 400
            if 'music_file' not in request.files:
                return {'message': 'No music_file in the request form'}, 400
    
            file = request.files['music_file']
            if file is None or file.filename == '':
                return {'message': 'No selected file'}, 400

            # Create a temporary file within the Flask application context
            with tempfile.NamedTemporaryFile(delete=False) as temp:
                file.save(temp.name)
                result = model.transcribe(temp.name)
                score = SpeechScoreApi.score(expected_speech_text, result["text"])
                logger.info(f'Expected: {expected_speech_text}, Recognized: {result["text"]}, Similarity: {score}')
            # Clean up the temporary file after processing
            os.unlink(temp.name)
            # Update user score
            userId = json.loads(get_jwt_identity())
            user = User.objects.get(id=userId['_id']['$oid'])
            user.update(score=(user.score + score))
            return {'text': result["text"], 'score': score}, 200
        except PermissionError as e:
            raise FilePermissionError(e)
        except Exception as e:
            raise InternalServerError(e)