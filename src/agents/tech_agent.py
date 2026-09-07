"""
Tech Agent — LaunchLayer Content & Tech Intelligence Specialist

Channels owned:
- @launchlayer Instagram (service showcases, automation demos)
- Shreyo's LinkedIn (personal thought leadership)
- "The Automation Edge" newsletter
- Cold outreach emails for LaunchLayer leads

Monitors: AI/automation news, new tools, India startup ecosystem
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

SYSTEM = f"""You are the Tech & Content Agent for LaunchLayer, Shreyo Ghosh's AI automation agency.

LaunchLayer:
- Services: WhatsApp bots, chatbots, Google Sheets automation, Make.com/Zapier workflows, email automation
- Pricing: ₹3,000–₹25,000/project
- Ideal clients: restaurants, CA firms, coaching centres, clinics, real estate, e-commerce
- Instagram: @launchlayer — service showcase, automation demos, before/after stories
- LinkedIn: Shreyo Ghosh personal page — thought leadership, case studies
- Newsletter: "The Automation Edge" — weekly, to leads/subscribers

Content principles:
- LinkedIn: personal + expert. First line = scroll-stopper. 180-250 words. Question/CTA at end.
- @launchlayer IG: practical, punchy, visual-first. "Before automation / After automation" angle works best.
- Newsletter: curated AI news + one LaunchLayer case study + one offer.
- Cold emails: ultra-specific to prospect's industry. Under 150 words. Low-friction CTA.

Today: {datetime.now().strftime("%A, %d %B %Y")}"""


class TechAgent:
    def __init__(self):
        self.client = Groq(api_key=GROQ_API_KEY)

    async def handle(self, message: str) -> dict | str:
        lower = message.lower()

        if "newsletter" in lower:
            return await self._newsletter(message)
        if "linkedin" in lower:
            return await self._linkedin(message)
        if "instagram" in lower or "@launchlayer" in lower:
            return await self._instagram_launchlayer(message)
        if "outreach" in lower or "cold email" in lower:
            return await self._cold_email(message)
        if any(k in lower for k in ["news", "trend", "tool", "ai ", "automation"]):
            return await self._tech_news(message)
        return await self._general(message)

    async def _tech_news(self, message: str) -> str:
        results = await asyncio.gather(
            web_search("AI automation tools India small business 2025 new"),
            web_search("Make.com Zapier ChatGPT updates this week")
        )
        news = "\n---\n".join(results)
        resp = self.client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content":
                    f"Request: {message}\n\nFresh news:\n{news[:2000]}\n\n"
                    f"Summarise the 3 most relevant developments for LaunchLayer. "
                    f"For each: what it is | why it matters to clients | how LaunchLayer can sell it. "
                    f"End with: 💡 *Content angle:* [one post idea from this news]"}
            ],
            max_tokens=700, temperature=0.5,
        )
        return f"📡 *Tech Agent — News Brief*\n\n{resp.choices[0].message.content.strip()}"

    async def _newsletter(self, message: str) -> dict:
        news1, news2 = await asyncio.gather(
            web_search("AI automation India news this week"),
            web_search("best new AI tools for small business 2025")
        )
        resp = self.client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": f"""Write "The Automation Edge" newsletter.
Request: {message}
News: {(news1+news2)[:1800]}

Structure:
SUBJECT: [catchy 8-10 word subject line]

Hi [First Name],

🔥 THIS WEEK IN AI AUTOMATION
[3 bullet points — biggest news relevant to Indian SMEs]

💡 CASE STUDY: [business type] Saves [X hrs/₹] with Automation
[120 words — relatable story, specific results, LaunchLayer did this]

⚡ TOOL OF THE WEEK
[one free/cheap tool + how LaunchLayer integrates it for clients]

🎯 THIS WEEK'S OFFER
[one specific LaunchLayer service, price, clear CTA — reply or WhatsApp]

Until next week,
Shreyo Ghosh
Founder, LaunchLayer

Write the full newsletter. Human tone, not corporate."""}
            ],
            max_tokens=1000, temperature=0.75,
        )
        content = resp.choices[0].message.content.strip()

        subject = "The Automation Edge"
        for line in content.split("\n"):
            if "SUBJECT:" in line.upper():
                subject = line.replace("SUBJECT:", "").strip(" *[]_")
                break

        return {
            "text": (
                f"📧 *Tech Agent — Newsletter Draft*\n"
                f"_'The Automation Edge'_\n\n"
                f"*Subject:* {subject}\n\n"
                f"```\n{content}\n```\n\n"
                f"_Review above then reply 'send newsletter to [email list]' to dispatch._"
            ),
            "buttons": [
                {"label": "✅ Approve", "data": "approve_post:newsletter"},
                {"label": "🔄 Regenerate", "data": "regen:newsletter"}
            ]
        }

    async def _linkedin(self, message: str) -> dict:
        search = await web_search(f"AI automation {message} India 2025")
        resp = self.client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": f"""Write a LinkedIn post for Shreyo Ghosh (personal page).
Request: {message}
Context: {search[:600]}

Rules:
- Line 1 = scroll-stopping hook (question, stat, or bold claim — NOT a greeting)
- 3-4 short paragraphs (2-3 lines each)
- Personal + expert tone — Shreyo is a scrappy founder, not a corporate drone
- End: question or CTA inviting comments/DMs
- 3-5 hashtags (#AIAutomation #LaunchLayer #IndiaStartup etc)
- 180-250 words

Output ONLY the post."""}
            ],
            max_tokens=450, temperature=0.82,
        )
        post = resp.choices[0].message.content.strip()
        return {
            "text": (
                f"✍️ *Tech Agent — LinkedIn Post*\n"
                f"_For: Shreyo Ghosh personal page_\n\n"
                f"```\n{post}\n```\n\n"
                f"_Post now. Engage with comments in first 30 min for max reach._"
            ),
            "buttons": [
                {"label": "✅ Use this", "data": "approve_post:linkedin"},
                {"label": "🔄 Try again", "data": "regen:linkedin"},
                {"label": "📸 Make IG version", "data": "convert:ig_launchlayer"}
            ]
        }

    async def _instagram_launchlayer(self, message: str) -> dict:
        caption, visual = await create_post_content(
            message=message,
            account="@launchlayer",
            brand="LaunchLayer",
            tone="practical, punchy, automation-focused — show real business impact",
            cta="DM us 'AUTOMATE' to get started 🚀",
            hashtags="#AIAutomation #LaunchLayer #AutomateIndia #IndiaStartup #BusinessBot #WorkSmarter #AIForBusiness #StartupIndia #ChatBot #WhatsAppBot",
            client=self.client,
            system=SYSTEM
        )
        return {
            "text": (
                f"📸 *Tech Agent — @launchlayer Instagram*\n\n"
                f"*Caption:*\n```\n{caption}\n```\n\n"
                f"*Canva visual brief:*\n_{visual}_\n\n"
                f"_Best posting times: 8–9am or 7–8pm IST._\n"
                f"_Post on @launchlayer account._"
            ),
            "buttons": [
                {"label": "✅ Post this", "data": "approve_post:launchlayer"},
                {"label": "🔄 Different angle", "data": "regen:ig_launchlayer"}
            ]
        }

    async def _cold_email(self, message: str) -> dict:
        resp = self.client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": f"""Write a LaunchLayer cold outreach email.
Request: {message}

Format:
SUBJECT: [subject line]
---
[email body — under 150 words]

Requirements:
- Opening references their specific business/pain point
- Names one concrete problem they likely have
- Shows exactly how LaunchLayer solves it (specific, not vague)
- Social proof: "We helped a similar [business type] save X hours/week"
- CTA: 15-min call or WhatsApp reply — low friction
- Professional but warm. Sign off as Shreyo Ghosh, LaunchLayer."""}
            ],
            max_tokens=450, temperature=0.7,
        )
        content = resp.choices[0].message.content.strip()
        return {
            "text": f"📧 *Tech Agent — Cold Outreach Email*\n\n```\n{content}\n```",
            "buttons": [
                {"label": "✅ Use template", "data": "approve_post:cold_email"},
                {"label": "🔄 Different industry", "data": "regen:cold_email"}
            ]
        }

    async def _general(self, message: str) -> str:
        search = await web_search(message + " AI automation India")
        resp = self.client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": f"{message}\n\nContext: {search[:800]}"}
            ],
            max_tokens=700, temperature=0.6,
        )
        return f"📡 *Tech Agent*\n\n{resp.choices[0].message.content.strip()}"
