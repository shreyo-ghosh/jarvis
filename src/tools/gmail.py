"""
Gmail tool — reads OAuth token from SSM Parameter Store.
Same OAuth flow as original README Step 5.
"""

import os
import json
import base64
import logging
from email.mime.text import MIMEText

import boto3

logger = logging.getLogger(__name__)
_svc = None


def _get_token_json() -> str:
    """Pull GMAIL_TOKEN_JSON from env or SSM."""
    val = os.environ.get("GMAIL_TOKEN_JSON", "")
    if val:
        return val
    try:
        ssm = boto3.client("ssm", region_name=os.environ.get("AWS_REGION", "ap-south-1"))
        resp = ssm.get_parameter(Name="/shreyo-agent/GMAIL_TOKEN_JSON", WithDecryption=True)
        return resp["Parameter"]["Value"]
    except Exception:
        return ""


def _get_service():
    global _svc
    if _svc:
        return _svc
    token_json = _get_token_json()
    if not token_json:
        raise ValueError(
            "Gmail not configured.\n"
            "Run `python scripts/setup_google_auth.py` then push token to SSM.\n"
            "See README Step 5."
        )
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    d = json.loads(token_json)
    creds = Credentials(
        token=d.get("token"),
        refresh_token=d.get("refresh_token"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=d.get("client_id"),
        client_secret=d.get("client_secret"),
        scopes=d.get("scopes", ["https://mail.google.com/"])
    )
    _svc = build("gmail", "v1", credentials=creds)
    return _svc


def draft_email(to: str, subject: str, body: str) -> str:
    """Return formatted draft — does NOT send."""
    return (
        f"📧 *Email Draft*\n\n"
        f"*To:* {to or '_(add recipient)_'}\n"
        f"*Subject:* {subject}\n\n"
        f"{body}\n\n"
        f"---\n"
        f"_Reply *'send this to [email]'* to send._"
    )


async def send_email(to: str, subject: str, body: str) -> str:
    try:
        svc = _get_service()
        msg = MIMEText(body)
        msg["to"] = to
        msg["subject"] = subject
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        svc.users().messages().send(userId="me", body={"raw": raw}).execute()
        return f"✅ Email sent to *{to}*\nSubject: _{subject}_"
    except ValueError as e:
        return str(e)
    except Exception as e:
        return f"❌ Email failed: {e}"


async def list_emails(max_results: int = 5) -> str:
    try:
        svc = _get_service()
        res = svc.users().messages().list(
            userId="me", maxResults=max_results, labelIds=["INBOX"]
        ).execute()
        msgs = res.get("messages", [])
        if not msgs:
            return "📭 Inbox empty."
        lines = [f"📬 *Last {len(msgs)} emails:*\n"]
        for m in msgs:
            d = svc.users().messages().get(
                userId="me", id=m["id"], format="metadata",
                metadataHeaders=["From", "Subject", "Date"]
            ).execute()
            h = {x["name"]: x["value"] for x in d["payload"]["headers"]}
            lines.append(f"• *{h.get('Subject', 'No subject')}*\n  From: {h.get('From', '?')}")
        return "\n".join(lines)
    except ValueError as e:
        return str(e)
    except Exception as e:
        return f"❌ Failed to read inbox: {e}"
