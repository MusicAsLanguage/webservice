from flask import request
from flask_restful import Resource
from flask_jwt_extended import jwt_required, get_jwt_identity
from resources.errors import InternalServerError, SchemaValidationError
from mongoengine.errors import FieldDoesNotExist
from database.models import IncomeMessage, User
from services.mail_service import send_email
import json

class SendMsgApi(Resource):
    @jwt_required()
    def post(self):
        try:
            msg = request.get_json()
            msgObj = IncomeMessage(**msg)
            userId = json.loads(get_jwt_identity())
            user = User.objects.get(id=userId['_id']['$oid'])
            msgObj.User = user
            msgObj.save()
            try:
                send_email('Message from ' + user.name + '<' + user.email + '>',
                                sender='musicaslanguage@sf-ns.org',
                                recipients=['musicaslanguage@sf-ns.org'],
                                text_body=msgObj.Msg,
                                html_body=msgObj.Msg)
            except Exception as e:
                #ignore email error for now, 
                #TODO: need to revisit before move to production
                pass
            return {'id': str(msgObj.id)}, 200
        except FieldDoesNotExist:
            raise SchemaValidationError
        except Exception as e:
            raise InternalServerError