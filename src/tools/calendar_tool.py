"""
Google Calendar tool — reads OAuth token from SSM (same token as Gmail).
"""

import os
import json
import logging
from datetime import datetime, timedelta

import boto3

logger = logging.getLogger(__name__)
_svc = None


def _get_token_json() -> str:
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
        raise ValueError("Calendar not configured. See README Step 5.")
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    d = json.loads(token_json)
    creds = Credentials(
        token=d.get("token"),
        refresh_token=d.get("refresh_token"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=d.get("client_id"),
        client_secret=d.get("client_secret"),
        scopes=d.get("scopes", ["https://www.googleapis.com/auth/calendar"])
    )
    _svc = build("calendar", "v3", credentials=creds)
    return _svc


async def get_events(days_ahead: int = 3) -> str:
    try:
        svc = _get_service()
        now = datetime.utcnow()
        end = now + timedelta(days=days_ahead)
        result = svc.events().list(
            calendarId="primary",
            timeMin=now.isoformat() + "Z",
            timeMax=end.isoformat() + "Z",
            maxResults=10,
            singleEvents=True,
            orderBy="startTime"
        ).execute()

        events = result.get("items", [])
        if not events:
            return f"📅 No events in the next {days_ahead} days. Clear schedule."

        lines = [f"📅 *Calendar — next {days_ahead} days:*\n"]
        for e in events:
            start = e["start"].get("dateTime", e["start"].get("date", ""))
            try:
                dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
                fmt = dt.strftime("%a %d %b, %I:%M %p")
            except Exception:
                fmt = start
            lines.append(f"• *{e.get('summary', 'Untitled')}* — {fmt}")
            if e.get("description"):
                lines.append(f"  _{e['description'][:70]}_")
        return "\n".join(lines)
    except ValueError as e:
        return str(e)
    except Exception as e:
        return f"❌ Calendar error: {e}"


async def add_event(title: str, date: str, time: str = "10:00",
                    duration_minutes: int = 60, description: str = "") -> str:
    try:
        svc = _get_service()
        start_dt = datetime.fromisoformat(f"{date}T{time}:00")
        end_dt = start_dt + timedelta(minutes=duration_minutes)
        event = {
            "summary": title,
            "description": description,
            "start": {"dateTime": start_dt.isoformat(), "timeZone": "Asia/Kolkata"},
            "end": {"dateTime": end_dt.isoformat(), "timeZone": "Asia/Kolkata"},
        }
        created = svc.events().insert(calendarId="primary", body=event).execute()
        fmt = start_dt.strftime("%a %d %b at %I:%M %p")
        return (
            f"✅ *Event added:* {title}\n"
            f"📆 {fmt} IST ({duration_minutes} min)\n"
            f"🔗 {created.get('htmlLink', 'Check Google Calendar')}"
        )
    except ValueError as e:
        return str(e)
    except Exception as e:
        return f"❌ Failed to add event: {e}"
