from html import escape

from flask import current_app
from flask_jwt_extended import current_user, jwt_required
from flask_restful import Resource

from database.models import IncomeMessage
from resources.validation import json_body, text
from services.mail_service import send_email


class SendMsgApi(Resource):
    @jwt_required()
    def post(self):
        body = json_body({"Msg"})
        user = current_user._get_current_object()
        message = IncomeMessage(Msg=text(body["Msg"], 10000), User=user).save()
        try:
            send_email(
                "Message from " + user.name + "<" + user.email + ">",
                sender="musicaslanguage@sf-ns.org",
                recipients=["musicaslanguage@sf-ns.org"],
                text_body=message.Msg,
                html_body=escape(message.Msg),
            )
        except Exception:
            current_app.logger.exception("Message saved but notification failed: %s", message.id)
        return {"id": str(message.id)}, 200
