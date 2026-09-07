"""
Market Agent — Indian Stock Market Specialist

- Nifty 50, Sensex, sector indices (live via Gemini search)
- Individual NSE/BSE stock analysis
- Motilal Oswal MF NAV + fund performance data
- Macro: RBI, FII/DII, rupee, crude oil
- Watchlist management (stored in DynamoDB)
- Daily summary for morning brief
"""

import os
import json
import logging
from datetime import datetime
from groq import Groq
from tools.search import web_search
from tools.dynamo import DynamoStore

logger = logging.getLogger(__name__)
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL = "llama-3.3-70b-versatile"

SYSTEM = f"""You are the Market Intelligence Agent for Shreyo Ghosh's Jarvis system.

Context:
- Shreyo runs a Motilal Oswal Digital Franchise — needs market insights to sell MF products
- Also a beginner trader — uses your analysis to understand markets and talk credibly to investors

Your specialties:
1. Indian indices: Nifty 50, Sensex, Nifty Bank, Nifty IT, Nifty Midcap
2. NSE/BSE stock analysis (fundamentals + recent news)
3. Motilal Oswal funds: Nifty 50 Index, ELSS Tax Saver, Flexi Cap, Liquid Fund
4. Macro India: RBI policy, FII/DII flows, INR, crude oil impact
5. SIP timing advice for client conversations

Format: Telegram markdown (*bold*, _italic_). Be data-rich but readable.
Always end investment analysis with: _⚠️ For informational use only — not financial advice._
Today: {datetime.now().strftime("%A, %d %B %Y")}"""


class MarketAgent:
    def __init__(self):
        self.client = Groq(api_key=GROQ_API_KEY)
        self.db = DynamoStore()

    async def handle(self, message: str) -> str:
        lower = message.lower()

        if "watchlist" in lower:
            if "add" in lower or "watch " in lower:
                return await self._watchlist_add(message)
            if "remove" in lower:
                return await self._watchlist_remove(message)
            return await self._watchlist_show()

        return await self._analyse(message)

    async def daily_summary(self) -> str:
        """3-line market pulse for morning brief."""
        try:
            data = await web_search("Nifty 50 Sensex India stock market today")
            resp = self.client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[{"role": "user", "content":
                    f"Give a 3-line India market summary from this data:\n{data[:600]}\n"
                    f"Format: Nifty level+direction | key sector move | one macro note. No fluff."}],
                max_tokens=120, temperature=0.2,
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            return f"Market data unavailable ({e})"

    async def _analyse(self, message: str) -> str:
        needs_live = any(k in message.lower() for k in [
            "today", "now", "current", "price", "nifty", "sensex", "stock",
            "market", "news", "rbi", "fii", "fund", "nav", "return", "performance",
            "rate", "crude", "rupee", "inr"
        ])

        context = ""
        if needs_live:
            query = f"India NSE BSE {message[:80]}"
            context = await web_search(query)

        prompt = message + (f"\n\nLive data:\n{context[:1500]}" if context else "")

        resp = self.client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": prompt}
            ],
            max_tokens=900, temperature=0.4,
        )
        return f"📈 *Market Agent*\n\n{resp.choices[0].message.content.strip()}"

    async def _watchlist_add(self, message: str) -> str:
        ticker = self._extract_ticker(message, exclude=["ADD", "TO", "WATCH", "WATCHLIST", "MY", "THE"])
        if not ticker:
            return "❓ Which stock to add? E.g. _'add RELIANCE to watchlist'_"
        wl = self.db.get("watchlist") or []
        if ticker not in wl:
            wl.append(ticker)
            self.db.put("watchlist", wl)
        return f"✅ *{ticker}* added to watchlist.\nTracking: {', '.join(wl)}"

    async def _watchlist_remove(self, message: str) -> str:
        ticker = self._extract_ticker(message, exclude=["REMOVE", "FROM", "WATCHLIST", "MY"])
        if not ticker:
            return "❓ Which stock to remove?"
        wl = self.db.get("watchlist") or []
        if ticker in wl:
            wl.remove(ticker)
            self.db.put("watchlist", wl)
        return f"✅ *{ticker}* removed.\nRemaining: {', '.join(wl) or 'empty'}"

    async def _watchlist_show(self) -> str:
        wl = self.db.get("watchlist") or ["NIFTY50", "RELIANCE", "HDFCBANK", "INFY"]
        data = await web_search(f"NSE stock price today {' '.join(wl[:5])}")
        resp = self.client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content":
                    f"Watchlist: {', '.join(wl)}\nLive data: {data[:1000]}\n\n"
                    f"Show a quick status for each. Simple format."}
            ],
            max_tokens=400, temperature=0.3,
        )
        return f"📋 *Watchlist*\n\n{resp.choices[0].message.content.strip()}"

    def _extract_ticker(self, message: str, exclude: list) -> str:
        words = message.upper().split()
        for w in words:
            clean = w.strip(".,!?:")
            if clean.isalpha() and 2 <= len(clean) <= 15 and clean not in exclude:
                return clean
        return ""
