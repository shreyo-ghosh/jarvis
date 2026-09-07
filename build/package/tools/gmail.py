"""
tools/gmail.py — Gmail draft/send via the Gmail API (optional).
"""
import base64
import json
from email.mime.text import MIMEText

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from tools.ssm import get_secret


def _get_service():
    token_info = json.loads(get_secret("GMAIL_TOKEN_JSON"))
    creds = Credentials.from_authorized_user_info(token_info)
    return build("gmail", "v1", credentials=creds)


def draft_email(to: str, subject: str, body: str) -> str:
    service = _get_service()
    message = MIMEText(body)
    message["to"] = to
    message["subject"] = subject
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    draft = service.users().drafts().create(
        userId="me", body={"message": {"raw": raw}}
    ).execute()
    return f"Draft created (id: {draft['id']})"


def send_email(to: str, subject: str, body: str) -> str:
    service = _get_service()
    message = MIMEText(body)
    message["to"] = to
    message["subject"] = subject
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    sent = service.users().messages().send(
        userId="me", body={"raw": raw}
    ).execute()
    return f"Email sent (id: {sent['id']})"
