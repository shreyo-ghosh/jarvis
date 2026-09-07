"""
Finance Agent — Revenue Generation Specialist

Dual mandate:
1. @launchlayerfinance Instagram — finance education + MO lead attraction
2. Motilal Oswal outreach — email campaigns, WhatsApp broadcasts, SIP/ELSS/lumpsum pitches

Goal: Grow AUM from ₹45K → ₹5L+ in 90 days.
"""

import os
import asyncio
import logging
from datetime import datetime
from groq import Groq
from tools.search import web_search
from tools.gmail import draft_email
from tools.instagram import create_post_content

logger = logging.getLogger(__name__)
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL = "llama-3.3-70b-versatile"

SYSTEM = f"""You are the Finance & Revenue Agent for Shreyo Ghosh's Jarvis system.

Motilal Oswal context:
- Shreyo is a registered Digital Franchise Partner
- Products to sell: Nifty 50 Index Fund, ELSS Tax Saver Fund, Flexi Cap Fund, Liquid Fund
- Current AUM: ~₹45,000. Target: ₹5L+ in 90 days.
- Target investors: Salaried professionals 25–40yrs, ₹25K–₹1L/month income
- Key hooks: 80C tax saving (ELSS), compounding, SIP starts at ₹500, beats FD returns

@launchlayerfinance Instagram:
- Dual-purpose: attracts MO investors + LaunchLayer business clients
- Tagline: "Automate your savings like you automate your business"
- Mix: SIP education + financial tips + occasional LaunchLayer tease

Sales philosophy:
- Educate first, pitch second — never hard sell
- WhatsApp: feel like a friend's tip, not a broker pitch
- Email: trust-building, specific fund data, low-friction CTA
- MF disclaimer is MANDATORY on all investment content

Today: {datetime.now().strftime("%A, %d %B %Y")}

ALWAYS add at end of investment content:
_⚠️ Mutual fund investments are subject to market risks. Please read all scheme-related documents carefully._"""


class FinanceAgent:
    def __init__(self):
        self.client = Groq(api_key=GROQ_API_KEY)

    async def handle(self, message: str) -> dict | str:
        lower = message.lower()

        if "instagram" in lower or "@launchlayerfinance" in lower:
            return await self._instagram_finance(message)
        if "whatsapp" in lower:
            return await self._whatsapp(message)
        if "email" in lower or "outreach" in lower:
            return await self._email_campaign(message)
        if "campaign" in lower or "aum" in lower:
            return await self._campaign_plan(message)
        if "lead" in lower or "prospect" in lower:
            return await self._lead_strategy(message)
        return await self._general(message)

    async def _instagram_finance(self, message: str) -> dict:
        search = await web_search("SIP mutual fund investment tips India 2025")
        caption, visual = await create_post_content(
            message=message,
            account="@launchlayerfinance",
            brand="LaunchLayer Finance",
            tone="friendly, educational, empowering — like a smart friend who knows finance",
            cta="💬 DM 'SIP' to start your investment journey | 🔗 Link in bio",
            hashtags="#SIP #MutualFunds #InvestIndia #FinancialFreedom #ELSS #TaxSaving #MotilalOswal #WealthBuilding #IndianInvestor #PersonalFinance #SavingsGoals #CompoundInterest",
            client=self.client,
            system=SYSTEM,
            extra_context=search[:500]
        )
        # Ensure MF disclaimer in caption
        if "market risk" not in caption.lower():
            caption += "\n\n_⚠️ MF investments subject to market risks. Read scheme documents carefully._"

        return {
            "text": (
                f"💰 *Finance Agent — @launchlayerfinance Instagram*\n\n"
                f"*Caption:*\n```\n{caption}\n```\n\n"
                f"*Canva visual brief:*\n_{visual}_\n\n"
                f"_Post on @launchlayerfinance account._\n"
                f"_Best times: 8am, 12pm, 7pm IST_"
            ),
            "buttons": [
                {"label": "✅ Post this", "data": "approve_post:launchlayerfinance"},
                {"label": "🔄 New angle", "data": "regen:ig_finance"},
                {"label": "📧 Make email version", "data": "convert:email_finance"}
            ]
        }

    async def _whatsapp(self, message: str) -> dict:
        resp = self.client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": f"""Write WhatsApp outreach messages for Motilal Oswal SIPs.
Request: {message}
Today: {datetime.now().strftime("%d %B %Y")}

Write TWO versions:

VERSION A — Beginner (never invested, money sitting in savings account):
- Under 90 words
- "Hi [Name]," opening
- Hook: ₹500/month SIP compounding angle
- One simple ask (reply YES / call / check link)
- MF disclaimer (short version)

VERSION B — FD holder (has FDs, wants better returns):
- Under 90 words
- Hook: FD rate vs MF returns comparison with numbers
- Mention ELSS 80C benefit if applicable
- One simple ask
- MF disclaimer

Make both feel like a friend's message, NOT a broker pitch."""}
            ],
            max_tokens=500, temperature=0.72,
        )
        content = resp.choices[0].message.content.strip()
        return {
            "text": (
                f"📱 *Finance Agent — WhatsApp Broadcast Templates*\n\n"
                f"```\n{content}\n```\n\n"
                f"_Personalise [Name] before sending._\n"
                f"_Send via WhatsApp Business broadcast list._"
            ),
            "buttons": [
                {"label": "✅ Use Version A", "data": "approve_post:wa_a"},
                {"label": "✅ Use Version B", "data": "approve_post:wa_b"},
                {"label": "🔄 Regenerate", "data": "regen:whatsapp"}
            ]
        }

    async def _email_campaign(self, message: str) -> dict:
        search = await web_search("Motilal Oswal fund performance returns 2025")
        resp = self.client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": f"""Write a Motilal Oswal investor outreach email.
Request: {message}
Fund data context: {search[:600]}

Format:
SUBJECT: [benefit-focused, 6-8 words]
---
Hi [First Name],

[Opening — acknowledge their current financial situation]

[Education block — one key insight: MF vs FD numbers, or SIP compounding, or 80C benefit]

[Product mention — specific Motilal Oswal fund for their situation]

[CTA — 15-min free call or WhatsApp. "No pressure, just clarity."]

Warm regards,
Shreyo Ghosh
Motilal Oswal Partner | LaunchLayer

[Full MF disclaimer]

Body under 170 words. Warm, trustworthy, not salesy."""}
            ],
            max_tokens=550, temperature=0.65,
        )
        content = resp.choices[0].message.content.strip()
        draft = draft_email("", "Investment opportunity", content)
        return {
            "text": f"📧 *Finance Agent — MO Investor Email*\n\n{draft}",
            "buttons": [
                {"label": "✅ Approve draft", "data": "send_email:mo_outreach"},
                {"label": "🔄 Different angle", "data": "regen:email_mo"}
            ]
        }

    async def _campaign_plan(self, message: str) -> str:
        resp = self.client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": f"""{message}

Situation: Shreyo needs MO AUM to go from ₹45K → ₹5L in 90 days, zero marketing budget.

Design a specific campaign:
- Campaign name + core angle
- Target segment (exact profile)
- Week-by-week content calendar (@launchlayerfinance IG + WhatsApp broadcasts)
- Email sequence (3-email drip)
- Expected SIP conversions and AUM impact per week
- All zero-cost execution steps"""}
            ],
            max_tokens=800, temperature=0.6,
        )
        return f"💰 *Finance Agent — Campaign Plan*\n\n{resp.choices[0].message.content.strip()}"

    async def _lead_strategy(self, message: str) -> str:
        resp = self.client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": f"""{message}

Shreyo's goal: 10 new SIP clients this month. Budget: ₹0.

Give:
1. Exact target profile to chase (be specific — not "salaried professionals", say who)
2. Best opening line for this profile
3. Channel rank: WhatsApp / Email / IG DM (which first for this lead type)
4. Follow-up sequence: Day 1, Day 3, Day 7 messages
5. One common objection + how to handle it"""}
            ],
            max_tokens=700, temperature=0.6,
        )
        return f"💰 *Finance Agent — Lead Strategy*\n\n{resp.choices[0].message.content.strip()}"

    async def _general(self, message: str) -> str:
        resp = self.client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": message}
            ],
            max_tokens=700, temperature=0.6,
        )
        return f"💰 *Finance Agent*\n\n{resp.choices[0].message.content.strip()}"
