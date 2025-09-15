from flask_mail import Message
from flask import current_app
from app.extensions import mail

def send_email(subject, recipients, body):
    msg = Message(
        subject=subject,
        recipients=recipients,
        body=body,
        sender=current_app.config.get("MAIL_USERNAME")
    )
    mail.send(msg)
