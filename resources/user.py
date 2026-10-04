from flask_jwt_extended import current_user, jwt_required
from flask_restful import Resource

from database.models import ActivityStatus, IncomeMessage, SongPlayingStatus


class DeleteUserAndDataApi(Resource):
    @jwt_required()
    def delete(self):
        user = current_user._get_current_object()
        for model in (ActivityStatus, SongPlayingStatus, IncomeMessage):
            model.objects(User=user).delete()
        user.delete()
        return {"success": True}, 200
