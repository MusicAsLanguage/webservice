from database.models import User
from flask_jwt_extended import decode_token
from services.mail_service import send_email

def db_reset_pwd(reset_token, password):
    user_id = decode_token(reset_token)['sub']
    user = User.objects.get(id=user_id)

    user.modify(password=password)
    user.hash_password()
    user.save()

    send_email('[MusicAsLanguage] Password reset successful',
                    sender='musicaslanguage@sf-ns.org',
                    recipients=[user.email],
                    text_body='Password reset was successful',
                    html_body='<p>Password reset was successful</p>')