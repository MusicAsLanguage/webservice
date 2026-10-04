from flask_jwt_extended import current_user, jwt_required
from flask_restful import Resource

from resources.validation import LEGACY_RECORD_FIELDS, LEGACY_USER_FIELDS, integer, json_body
from services.user_service import user_write


class GetUserScoreApi(Resource):
    @jwt_required()
    def get(self):
        return {"score": current_user.score}, 200


class UpdateUserScoreApi(Resource):
    @jwt_required()
    def post(self):
        body = json_body({"score"}, LEGACY_RECORD_FIELDS | LEGACY_USER_FIELDS | {"email"})
        score = integer(body["score"])
        with user_write(current_user):
            current_user.update(set__score=score)
        return {"success": True}, 200
