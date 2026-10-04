from flask import current_app
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

from resources.errors import ServiceUnavailableError


def send_email(subject, sender, recipients, text_body, html_body):
    sender_override = current_app.config.get("MAIL_SENDER")
    if sender_override is not None:
        return sender_override(
            subject=subject, sender=sender, recipients=recipients,
            text_body=text_body, html_body=html_body,
        )
    key = current_app.config["SEND_GRID_KEY"]
    if not key:
        raise ServiceUnavailableError("SEND_GRID_KEY is not configured")
    message = Mail(
        from_email=sender,
        to_emails=recipients,
        subject=subject,
        plain_text_content=text_body,
        html_content=html_body,
    )
    response = SendGridAPIClient(key).send(message)
    if not 200 <= response.status_code < 300:
        raise ServiceUnavailableError("Email provider rejected the message")
