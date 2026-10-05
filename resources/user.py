from flask_jwt_extended import current_user, jwt_required
from flask_restful import Resource

from services.user_service import delete_account


class DeleteUserAndDataApi(Resource):
    @jwt_required()
    def delete(self):
        delete_account(current_user.id)
        return {"success": True}, 200
