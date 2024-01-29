import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

send_grid_key = os.getenv('SEND_GRID_KEY', 'DefaultKey')
def send_email(subject, sender, recipients, text_body, html_body):
    if send_grid_key != "":
        sendgrid_email(subject, sender, recipients, html_body)

def sendgrid_email(subject, sender, recipients, html_body):
    message = Mail(
        from_email=sender,
        to_emails=recipients,
        subject=subject,
        html_content=html_body)    
    sg = SendGridAPIClient(send_grid_key)
    response = sg.send(message)
    #print(response.status_code)
    #print(response.body)
    #print(response.headers)
    