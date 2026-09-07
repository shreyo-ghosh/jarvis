"""
bot.py — AWS Lambda entrypoint for the Telegram webhook.
"""
import json
import os
import urllib.request

from agent import handle_message
from tools.ssm import get_secret


def _get_telegram_token() -> str:
    return os.environ.get("TELEGRAM_TOKEN") or get_secret("TELEGRAM_TOKEN")


def _get_allowed_user_id() -> str:
    return os.environ.get("ALLOWED_USER_ID") or get_secret("ALLOWED_USER_ID")


def send_message(chat_id: int, text: str, telegram_token: str | None = None) -> None:
    telegram_token = telegram_token or _get_telegram_token()
    api = f"https://api.telegram.org/bot{telegram_token}"
    url = f"{api}/sendMessage"
    data = json.dumps({
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
    }).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        print(f"Failed to send Telegram message: {e}")


def handler(event, context):
    telegram_token = _get_telegram_token()
    allowed_user_id = _get_allowed_user_id()

    try:
        body = json.loads(event.get("body", "{}"))
    except json.JSONDecodeError:
        return {"statusCode": 200, "body": "ignored"}

    message = body.get("message") or body.get("edited_message")
    if not message:
        return {"statusCode": 200, "body": "no message"}

    chat_id = message["chat"]["id"]
    user_id = str(message["from"]["id"])
    text = message.get("text", "").strip()

    if user_id != str(allowed_user_id):
        send_message(chat_id, "Unauthorized. This bot is private.", telegram_token)
        return {"statusCode": 200, "body": "unauthorized"}

    if text == "/start":
        send_message(chat_id, "Shreyo Agent is live on AWS. Try: `search for AI automation trends India 2026`", telegram_token)
        return {"statusCode": 200, "body": "ok"}

    if not text:
        return {"statusCode": 200, "body": "no text"}

    try:
        reply = handle_message(text)
    except Exception as e:
        reply = f"Something went wrong: {e}"

    send_message(chat_id, reply, telegram_token)
    return {"statusCode": 200, "body": "ok"}
