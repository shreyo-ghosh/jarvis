"""
bot.py — AWS Lambda handler for Telegram webhook.
Replaces the polling-based bot.py from the Railway version.
API Gateway POST → Lambda → this handler → Orchestrator → response.
"""

import json
import os
import asyncio
import logging

import boto3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot
from telegram.ext import Application

from agents.orchestrator import Orchestrator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _get_secret(name: str, required: bool = True) -> str:
    """Pull secret from SSM Parameter Store (set by deploy.sh)."""
    val = os.environ.get(name, "")
    if val:
        return val
    try:
        ssm = boto3.client("ssm", region_name=os.environ.get("AWS_REGION", "ap-south-1"))
        response = ssm.get_parameter(Name=f"/shreyo-agent/{name}", WithDecryption=True)
        return response["Parameter"]["Value"]
    except Exception as e:
        if required:
            raise RuntimeError(f"Cannot load secret {name}: {e}")
        return ""


def _load_runtime_secrets() -> tuple[str, str]:
    """Load runtime secrets defensively so import-time failures are easier to debug."""
    telegram_token = _get_secret("TELEGRAM_TOKEN")
    allowed_user_id = _get_secret("ALLOWED_USER_ID", required=False)
    return telegram_token, allowed_user_id


TELEGRAM_TOKEN, ALLOWED_USER_ID = _load_runtime_secrets()

# Reuse orchestrator across warm Lambda invocations
_orchestrator = None


def get_orchestrator() -> Orchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = Orchestrator()
    return _orchestrator


def lambda_handler(event: dict, context) -> dict:
    """
    AWS Lambda entry point.
    API Gateway sends Telegram webhook POST bodies here.
    """
    # Health check from API Gateway
    if event.get("requestContext", {}).get("http", {}).get("method") == "GET":
        return {"statusCode": 200, "body": "Jarvis online."}

    try:
        body = json.loads(event.get("body", "{}"))
    except json.JSONDecodeError:
        return {"statusCode": 400, "body": "Bad JSON"}

    # Run async handler in Lambda's sync context
    try:
        asyncio.get_event_loop().run_until_complete(_process_update(body))
    except RuntimeError:
        asyncio.run(_process_update(body))

    # Always return 200 to Telegram immediately (prevents retries)
    return {"statusCode": 200, "body": "ok"}


async def _process_update(body: dict):
    """Parse Telegram update and dispatch to orchestrator."""
    bot = Bot(token=TELEGRAM_TOKEN)

    # Handle callback queries (inline button presses)
    if "callback_query" in body:
        cq = body["callback_query"]
        chat_id = cq["message"]["chat"]["id"]
        uid = str(cq["from"]["id"])

        if ALLOWED_USER_ID and uid != ALLOWED_USER_ID:
            return

        result = await get_orchestrator().handle_callback(cq["data"], uid)
        await bot.send_message(chat_id=chat_id, text=result, parse_mode="Markdown")
        await bot.answer_callback_query(callback_query_id=cq["id"])
        return

    # Handle regular messages
    message = body.get("message", {})
    if not message:
        return

    chat_id = message["chat"]["id"]
    uid = str(message["from"]["id"])
    text = message.get("text", "")

    if ALLOWED_USER_ID and uid != ALLOWED_USER_ID:
        await bot.send_message(chat_id=chat_id, text="⛔ Unauthorized.")
        return

    if not text:
        return

    # Commands
    if text == "/start":
        await bot.send_message(chat_id=chat_id, parse_mode="Markdown", text=(
            "🤖 *Jarvis Online — 4-Agent System*\n\n"
            "Your autonomous business command centre:\n\n"
            "🧠 *Orchestrator* — routes decisions, generates daily briefs\n"
            "📈 *Market Agent* — Nifty/Sensex, stocks, MF data, watchlists\n"
            "📡 *Tech Agent* — LaunchLayer content, @launchlayer IG, newsletter, LinkedIn\n"
            "💰 *Finance Agent* — @launchlayerfinance IG, MO outreach, WhatsApp/email\n\n"
            "Try: _'What should I focus on today?'_\n"
            "Type /help for more examples."
        ))
        return

    if text == "/help":
        await bot.send_message(chat_id=chat_id, parse_mode="Markdown", text=(
            "*Example commands:*\n\n"
            "`What should I focus on today?` — daily brief\n"
            "`What's Nifty doing today?` — market update\n"
            "`Add RELIANCE to my watchlist` — track stocks\n"
            "`Write this week's LaunchLayer newsletter` — newsletter draft\n"
            "`LinkedIn post about AI for CA firms` — post for Shreyo's page\n"
            "`Instagram post for @launchlayer about chatbots` — IG caption + Canva brief\n"
            "`Post on @launchlayerfinance about SIP vs FD` — finance IG content\n"
            "`WhatsApp messages for MO leads` — 2 broadcast templates\n"
            "`Draft outreach email for restaurant owner` — cold email\n"
            "`Log ₹8000 from LaunchLayer client ABC` — revenue tracker\n"
            "`Show revenue summary` — totals by source\n"
            "`Log task: call Priya about SIP, high priority` — task tracker\n"
            "`Show pending tasks` — task list\n"
            "`Mark task #2 as done` — complete task\n"
            "`What's on my calendar today?` — calendar view\n"
            "`Add meeting with Rahul tomorrow 3pm — MF review` — add event\n"
        ))
        return

    if text == "/agents":
        await bot.send_message(chat_id=chat_id, parse_mode="Markdown", text=(
            "🤖 *Agent Status*\n\n"
            "🧠 Orchestrator — *Online*\n"
            "📈 Market Agent — *Online*\n"
            "📡 Tech Agent — *Online*\n"
            "💰 Finance Agent — *Online*\n\n"
            "_Stack: Groq Llama 3.3 70B + Gemini Flash search_\n"
            "_Infra: AWS Lambda + DynamoDB + SSM_\n"
            "_Cost: ~₹0/day_"
        ))
        return

    # Show typing action
    await bot.send_chat_action(chat_id=chat_id, action="typing")

    try:
        result = await get_orchestrator().handle(text, uid)

        if isinstance(result, dict):
            reply_text = result.get("text", "")
            buttons = result.get("buttons", [])
            markup = None
            if buttons:
                keyboard = [[InlineKeyboardButton(b["label"], callback_data=b["data"])] for b in buttons]
                markup = InlineKeyboardMarkup(keyboard)

            for i, chunk in enumerate(_split(reply_text)):
                if i == len(_split(reply_text)) - 1 and markup:
                    await bot.send_message(chat_id=chat_id, text=chunk,
                                           parse_mode="Markdown", reply_markup=markup)
                else:
                    await bot.send_message(chat_id=chat_id, text=chunk, parse_mode="Markdown")
        else:
            for chunk in _split(str(result)):
                await bot.send_message(chat_id=chat_id, text=chunk, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Handler error: {e}", exc_info=True)
        await bot.send_message(chat_id=chat_id,
                               text=f"⚠️ Error: {str(e)[:200]}\n\nTry rephrasing.")


def _split(text: str, limit: int = 4000) -> list:
    if len(text) <= limit:
        return [text]
    return [text[i:i + limit] for i in range(0, len(text), limit)]
