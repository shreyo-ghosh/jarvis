"""
agent.py — AI brain + tool routing.
Primary model: Groq (Llama 3.3 70B). Fallback: Google Gemini 1.5 Flash.
"""
import json
import os

from groq import Groq
import google.generativeai as genai

from tools.ssm import get_secret
from tools.search import web_search
from tools.linkedin import generate_linkedin_post
from tools.tracker import log_revenue, log_task, revenue_summary

SYSTEM_PROMPT = """You are Shreyo's personal business assistant, running on Telegram.
You help with: web search, drafting LinkedIn posts, logging revenue, logging tasks,
and answering questions about SIPs, mutual fund distribution, and small business
automation (LaunchLayer, Motilal Oswal franchise).
Be concise, direct, and practical. Use INR (₹) for money.
"""

GROQ_MODEL = "openai/gpt-oss-20b"
GEMINI_MODEL = "gemini-3.6-flash"

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web for current information.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_linkedin_post",
            "description": "Generate a LinkedIn post on a given topic.",
            "parameters": {
                "type": "object",
                "properties": {"topic": {"type": "string"}},
                "required": ["topic"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "log_revenue",
            "description": "Log a revenue entry.",
            "parameters": {
                "type": "object",
                "properties": {
                    "amount": {"type": "number"},
                    "source": {"type": "string"},
                },
                "required": ["amount", "source"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "log_task",
            "description": "Log a task or follow-up reminder.",
            "parameters": {
                "type": "object",
                "properties": {"description": {"type": "string"}},
                "required": ["description"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "revenue_summary",
            "description": "Get a summary of logged revenue.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]


def _execute_tool(name: str, args: dict) -> str:
    if name == "web_search":
        return web_search(args["query"])
    if name == "generate_linkedin_post":
        return generate_linkedin_post(args["topic"])
    if name == "log_revenue":
        return log_revenue(args["amount"], args["source"])
    if name == "log_task":
        return log_task(args["description"])
    if name == "revenue_summary":
        return revenue_summary()
    return f"Unknown tool: {name}"


def _get_groq_client():
    return Groq(api_key=get_secret("GROQ_API_KEY"))


def _get_gemini_model():
    gemini_api_key = get_secret("GEMINI_API_KEY")
    genai.configure(api_key=gemini_api_key)
    return genai.GenerativeModel(GEMINI_MODEL)


def _handle_with_groq(user_text: str) -> str:
    groq_client = _get_groq_client()
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_text},
    ]
    response = groq_client.chat.completions.create(
        model=GROQ_MODEL,
        messages=messages,
        tools=TOOLS,
        tool_choice="auto",
    )
    msg = response.choices[0].message

    if msg.tool_calls:
        messages.append(msg)
        for call in msg.tool_calls:
            args = json.loads(call.function.arguments)
            result = _execute_tool(call.function.name, args)
            messages.append({
                "role": "tool",
                "tool_call_id": call.id,
                "content": result,
            })
        followup = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=messages,
        )
        return followup.choices[0].message.content

    return msg.content


def _handle_with_gemini(user_text: str) -> str:
    prompt = f"{SYSTEM_PROMPT}\n\nUser: {user_text}"
    model = _get_gemini_model()
    response = model.generate_content(prompt)
    return response.text


def handle_message(user_text: str) -> str:
    try:
        return _handle_with_groq(user_text)
    except Exception as e:
        print(f"Groq failed, falling back to Gemini: {e}")
        try:
            return _handle_with_gemini(user_text)
        except Exception as e2:
            return f"Both AI providers failed: {e2}"
