"""
tools/calendar_tool.py — Google Calendar read/write (optional).
"""
import json
import datetime

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from tools.ssm import get_secret


def _get_service():
    token_info = json.loads(get_secret("GMAIL_TOKEN_JSON"))
    creds = Credentials.from_authorized_user_info(token_info)
    return build("calendar", "v3", credentials=creds)


def list_today_events() -> str:
    service = _get_service()
    now = datetime.datetime.utcnow()
    start = now.replace(hour=0, minute=0, second=0).isoformat() + "Z"
    end = now.replace(hour=23, minute=59, second=59).isoformat() + "Z"
    events_result = service.events().list(
        calendarId="primary", timeMin=start, timeMax=end,
        singleEvents=True, orderBy="startTime"
    ).execute()
    events = events_result.get("items", [])
    if not events:
        return "No events today."
    lines = [f"{e['start'].get('dateTime', e['start'].get('date'))} — {e['summary']}" for e in events]
    return "\n".join(lines)


def add_event(summary: str, start_iso: str, end_iso: str) -> str:
    service = _get_service()
    event = {
        "summary": summary,
        "start": {"dateTime": start_iso},
        "end": {"dateTime": end_iso},
    }
    created = service.events().insert(calendarId="primary", body=event).execute()
    return f"Event created: {created.get('htmlLink')}"
