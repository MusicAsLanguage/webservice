from flask_jwt_extended import current_user, jwt_required
from flask_restful import Resource

from resources.validation import integer, json_body


class GetUserScoreApi(Resource):
    @jwt_required()
    def get(self):
        return {"score": current_user.score}, 200


class UpdateUserScoreApi(Resource):
    @jwt_required()
    def post(self):
        body = json_body({"score"})
        current_user.update(set__score=integer(body["score"]))
        return {"success": True}, 200
