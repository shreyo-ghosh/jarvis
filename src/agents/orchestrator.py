"""
Orchestrator Agent — The decision-making brain of Jarvis.

Routes Shreyo's messages to the right specialist agent(s).
Generates daily briefs from calendar + tasks + market + revenue data.
Runs agents in parallel for multi-domain requests.
"""

import os
import asyncio
import logging
from datetime import datetime
from groq import Groq

from agents.market_agent import MarketAgent
from agents.tech_agent import TechAgent
from agents.finance_agent import FinanceAgent
from tools.calendar_tool import get_events
from tools.tracker import get_summary, get_tasks

logger = logging.getLogger(__name__)

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL = "llama-3.3-70b-versatile"

SYSTEM = f"""You are the Orchestrator for Shreyo Ghosh's Jarvis — a 4-agent autonomous business system.

Shreyo's businesses:
1. LaunchLayer — AI automation agency. ₹3K–₹25K/project. Clients: Indian SMEs.
   Instagram: @launchlayer
2. Motilal Oswal Digital Franchise — MF distribution. AUM target: ₹5L in 90 days.
   Instagram: @launchlayerfinance

Your specialist agents:
- MARKET_AGENT — Indian stocks, Nifty/Sensex, MF NAV, macro news, watchlists
- TECH_AGENT — LaunchLayer content: newsletter, LinkedIn, @launchlayer Instagram, cold outreach
- FINANCE_AGENT — @launchlayerfinance Instagram, MO email/WhatsApp outreach, AUM campaigns

Rules:
1. Route by outputting exactly one of these lines (alone on its own line):
   ROUTE: MARKET_AGENT
   ROUTE: TECH_AGENT
   ROUTE: FINANCE_AGENT
   ROUTE: MULTI:[MARKET_AGENT,TECH_AGENT]
   ROUTE: MULTI:[TECH_AGENT,FINANCE_AGENT]
   ROUTE: MULTI:[MARKET_AGENT,FINANCE_AGENT]
   ROUTE: MULTI:[MARKET_AGENT,TECH_AGENT,FINANCE_AGENT]
   ROUTE: ORCHESTRATOR
2. After the ROUTE line, add one short sentence explaining what you're doing.
3. Handle directly (ROUTE: ORCHESTRATOR) for: task/revenue logging, calendar queries, general chat, "what should I focus on today".
4. Today: {datetime.now().strftime("%A %d %B %Y, %I:%M %p IST")}"""


class Orchestrator:
    def __init__(self):
        self.client = Groq(api_key=GROQ_API_KEY)
        self.market = MarketAgent()
        self.tech = TechAgent()
        self.finance = FinanceAgent()
        # Lightweight per-user history (Lambda is warm-reused, not persistent across cold starts)
        self._history: dict[str, list] = {}

    async def handle(self, message: str, user_id: str) -> dict | str:
        hist = self._history.setdefault(user_id, [])
        hist.append({"role": "user", "content": message})
        if len(hist) > 24:
            hist[:] = hist[-24:]

        lower = message.lower()

        # Fast-path: daily brief
        if any(k in lower for k in ["focus on today", "daily brief", "morning brief", "what's my plan", "what is my plan"]):
            result = await self._daily_brief()
            self._append_hist(hist, result)
            return result

        # Fast-path: revenue/task tracker (no LLM routing needed)
        if any(k in lower for k in ["log revenue", "log task", "show revenue", "revenue summary",
                                      "show task", "pending task", "mark task", "mark #"]):
            result = await self._handle_tracker(message)
            self._append_hist(hist, result)
            return result

        # Fast-path: calendar
        if any(k in lower for k in ["calendar", "schedule", "add meeting", "add event",
                                      "what's on my", "what is on my"]):
            result = await self._handle_calendar(message)
            self._append_hist(hist, result)
            return result

        # LLM routing for everything else
        route = self._get_route(message, hist)
        logger.info(f"Route for '{message[:60]}': {route}")

        result = await self._dispatch(route, message)
        self._append_hist(hist, result)
        return result

    def _get_route(self, message: str, hist: list) -> str:
        try:
            resp = self.client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[{"role": "system", "content": SYSTEM}] + hist[-6:],
                max_tokens=80,
                temperature=0.1,
            )
            content = resp.choices[0].message.content
            for line in content.split("\n"):
                line = line.strip()
                if line.startswith("ROUTE:"):
                    return line
        except Exception as e:
            logger.error(f"Routing error: {e}")
        return "ROUTE: ORCHESTRATOR"

    async def _dispatch(self, route: str, message: str) -> dict | str:
        if "MULTI:" in route:
            # Extract agents list from ROUTE: MULTI:[A,B]
            import re
            m = re.search(r'MULTI:\[(.+?)\]', route)
            agents_str = m.group(1) if m else ""
            agent_names = [a.strip() for a in agents_str.split(",")]
            return await self._run_multi(message, agent_names)

        if "MARKET_AGENT" in route:
            return await self.market.handle(message)
        if "TECH_AGENT" in route:
            return await self.tech.handle(message)
        if "FINANCE_AGENT" in route:
            return await self.finance.handle(message)

        # ORCHESTRATOR handles directly
        return await self._direct(message)

    async def _run_multi(self, message: str, agent_names: list) -> str:
        """Run multiple agents concurrently and stitch results."""
        tasks = []
        labels = []
        for name in agent_names:
            if name == "MARKET_AGENT":
                tasks.append(self.market.handle(message))
                labels.append("📈 Market Agent")
            elif name == "TECH_AGENT":
                tasks.append(self.tech.handle(message))
                labels.append("📡 Tech Agent")
            elif name == "FINANCE_AGENT":
                tasks.append(self.finance.handle(message))
                labels.append("💰 Finance Agent")

        results = await asyncio.gather(*tasks, return_exceptions=True)
        parts = []
        for label, r in zip(labels, results):
            if isinstance(r, Exception):
                parts.append(f"{label}\n\n⚠️ Error: {r}")
            elif isinstance(r, dict):
                parts.append(r.get("text", str(r)))
            else:
                parts.append(str(r))

        return "\n\n---\n\n".join(parts)

    async def _direct(self, message: str) -> str:
        """Orchestrator answers directly (general questions, chitchat)."""
        resp = self.client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": (
                    "You are Shreyo Ghosh's personal AI chief of staff. "
                    "He runs LaunchLayer (AI agency) and a Motilal Oswal MF franchise. "
                    "Be direct, practical, and action-focused. Use Telegram markdown."
                )},
                {"role": "user", "content": message}
            ],
            max_tokens=600,
            temperature=0.7,
        )
        return resp.choices[0].message.content.strip()

    async def _daily_brief(self) -> str:
        """Pull calendar + tasks + revenue + market → synthesise morning brief."""
        cal, tasks, rev, market = await asyncio.gather(
            _safe_async(get_events(2)),
            _safe_sync(get_tasks),
            _safe_sync(get_summary),
            self.market.daily_summary(),
        )

        prompt = f"""Generate Shreyo's daily action brief for {datetime.now().strftime("%A %d %B %Y")}.

CALENDAR (next 2 days):
{cal}

PENDING TASKS:
{tasks}

REVENUE THIS MONTH:
{rev}

MARKET PULSE:
{market}

Format (Telegram markdown):
🌅 *Daily Brief — [Day, Date]*

🎯 *Top 3 Actions Today* (sales-first — LaunchLayer closes + MO SIP conversions)
1. ...
2. ...
3. ...

📅 *Calendar*
[key meetings/events only]

📊 *Market Pulse*
[1 line]

✍️ *Content Task*
[one specific post or newsletter action]

💰 *Revenue Status*
[month total vs target, key gap]

Keep it under 250 words. Be specific, not generic. Shreyo needs to act, not read."""

        resp = self.client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
            temperature=0.5,
        )
        return resp.choices[0].message.content.strip()

    async def _handle_tracker(self, message: str) -> str:
        """Handle revenue/task tracker commands without LLM routing."""
        from tools.tracker import log_revenue, log_task, get_summary, get_tasks, mark_done
        lower = message.lower()

        if "log revenue" in lower or "log ₹" in lower or "log rs" in lower:
            # Parse: "log revenue: ₹8000 from LaunchLayer client ABC"
            import re
            amount_match = re.search(r'[₹rs\s]+(\d[\d,]*)', message, re.IGNORECASE)
            amount = float(amount_match.group(1).replace(",", "")) if amount_match else 0

            source = "LaunchLayer"
            for s in ["launchlayer", "motilal", "mo ", "fiverr", "consulting", "upwork"]:
                if s in lower:
                    source = s.title().replace("Mo ", "Motilal Oswal")
                    break

            return log_revenue(amount, source, message, "")

        elif "log task" in lower:
            priority = "high" if "high" in lower else ("low" if "low" in lower else "medium")
            task_text = message.replace("log task:", "").replace("log task", "").strip()
            import re
            due = re.search(r'due\s+(\S+)', lower)
            return log_task(task_text, priority, due.group(1) if due else "")

        elif "revenue summary" in lower or "show revenue" in lower:
            return get_summary()

        elif "pending task" in lower or "show task" in lower:
            return get_tasks()

        elif "mark task" in lower or "mark #" in lower:
            import re
            num = re.search(r'#?(\d+)', message)
            if num:
                return mark_done(int(num.group(1)))
            return "Which task number? E.g. 'mark task #3 as done'"

        return await self._direct(message)

    async def _handle_calendar(self, message: str) -> str:
        """Handle calendar queries."""
        from tools.calendar_tool import get_events, add_event
        lower = message.lower()

        if "add" in lower or "schedule" in lower or "create event" in lower:
            # Let LLM extract the event details
            prompt = f"""Extract calendar event details from: "{message}"

Output ONLY a JSON object:
{{"title": "...", "date": "YYYY-MM-DD", "time": "HH:MM", "duration_minutes": 60, "description": "..."}}

For relative dates: today is {datetime.now().strftime("%Y-%m-%d")}, tomorrow is {(datetime.now().replace(day=datetime.now().day+1)).strftime("%Y-%m-%d") if datetime.now().day < 28 else "next day"}.
Use 24-hour time. If no time given, use 10:00."""

            resp = self.client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=150, temperature=0.1,
            )
            import json, re
            raw = resp.choices[0].message.content.strip()
            match = re.search(r'\{.*\}', raw, re.DOTALL)
            if match:
                try:
                    d = json.loads(match.group())
                    return await add_event(d.get("title","Meeting"), d.get("date",""),
                                           d.get("time","10:00"), d.get("duration_minutes",60),
                                           d.get("description",""))
                except Exception as e:
                    return f"Couldn't parse event details: {e}. Try: 'Add meeting with [Name] on [date] at [time]'"
            return "Couldn't understand the event. Try: 'Add meeting with Rahul tomorrow at 3pm'"

        else:
            days = 7 if "week" in lower else 3
            return await get_events(days)

    def _append_hist(self, hist: list, result):
        text = result if isinstance(result, str) else result.get("text", "")
        hist.append({"role": "assistant", "content": text[:400]})

    async def handle_callback(self, data: str, user_id: str) -> str:
        if "approve_post" in data:
            account = data.split(":")[-1]
            return f"✅ Content approved for *{account}*.\nCopy the caption above and post it on Instagram.\n\n_Tip: post between 8-9am or 7-8pm IST for best reach._"
        if "send_email" in data:
            return "✅ Email draft approved.\nReply with: `send this to [email@address.com]` and I'll send it via Gmail."
        if "regen" in data:
            return "🔄 Say the same request again and I'll generate a fresh version."
        if "convert" in data:
            return "Say 'convert this to [format]' and I'll adapt the content."
        return "Got it."


async def _safe_async(coro):
    try:
        return await coro
    except Exception as e:
        return f"(unavailable: {e})"


async def _safe_sync(fn):
    try:
        return fn()
    except Exception as e:
        return f"(unavailable: {e})"
