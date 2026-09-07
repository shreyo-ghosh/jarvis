"""
Instagram content generator.
Creates captions + Canva visual briefs for:
  @launchlayer        — LaunchLayer services (Tech Agent)
  @launchlayerfinance — Finance education + MO (Finance Agent)

Auto-posting requires Facebook Business Manager + Instagram Graph API.
Set env vars: INSTAGRAM_ACCESS_TOKEN, LAUNCHLAYER_IG_ACCOUNT_ID, LAUNCHLAYER_FINANCE_IG_ACCOUNT_ID
"""

import os
import asyncio
import logging
from groq import Groq

logger = logging.getLogger(__name__)

INSTA_TOKEN = os.environ.get("INSTAGRAM_ACCESS_TOKEN", "")
IG_IDS = {
    "@launchlayer": os.environ.get("LAUNCHLAYER_IG_ACCOUNT_ID", ""),
    "@launchlayerfinance": os.environ.get("LAUNCHLAYER_FINANCE_IG_ACCOUNT_ID", ""),
}

ACCOUNT_STYLE = {
    "@launchlayer": {
        "vibe": "Tech-forward, clean, modern. Dark gradient background. Neon blue/green accent. Show automation workflows visually.",
        "content_types": "before/after automation | tool showcase | client win story | quick tip | surprising stat",
    },
    "@launchlayerfinance": {
        "vibe": "Clean, trustworthy, aspirational. White/mint background. Growth charts, coins, upward arrows. Warm but professional.",
        "content_types": "SIP explained simply | FD vs MF comparison | compounding magic chart | tax saving tip | market insight",
    }
}


async def create_post_content(
    message: str,
    account: str,
    brand: str,
    tone: str,
    cta: str,
    hashtags: str,
    client: Groq,
    system: str,
    extra_context: str = ""
) -> tuple[str, str]:
    """
    Returns (caption, canva_visual_brief).
    Runs caption + visual generation in parallel.
    """
    style = ACCOUNT_STYLE.get(account, ACCOUNT_STYLE["@launchlayer"])

    caption_prompt = f"""Write an Instagram caption for {account} ({brand}).

Topic/request: {message}
Tone: {tone}
{f'Supporting context: {extra_context}' if extra_context else ''}

Rules:
- First line = hook. No "Hey" or "Introducing". Just dive in with a bold statement, question, or surprising fact.
- 120–180 words total
- Emojis: 3–5, placed naturally (not at start of every line)
- Line breaks every 2–3 lines for mobile readability
- End with CTA: {cta}
- Hashtags at bottom: {hashtags}
- Content type ideas: {style['content_types']}

Output ONLY the caption text. No preamble, no "Here's your caption:"."""

    visual_prompt = f"""Describe the Canva visual for this Instagram post in 2-3 sentences.

Post topic: {message}
Account: {account} ({brand})
Visual style: {style['vibe']}

Be specific: background colour/gradient, main headline text on graphic (5-8 words), 
key visual element (icon/illustration/chart type), any sub-text or stat overlay."""

    caption, visual = await asyncio.gather(
        _call(client, system, caption_prompt, 380),
        _call(client, system, visual_prompt, 120)
    )
    return caption, visual


async def _call(client: Groq, system: str, prompt: str, max_tokens: int) -> str:
    resp = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt}
        ],
        max_tokens=max_tokens,
        temperature=0.82,
    )
    return resp.choices[0].message.content.strip()


async def auto_post(account: str, caption: str, image_url: str) -> str:
    """
    Post to Instagram via Graph API.
    Requires: Professional IG account linked to Facebook Page + Graph API access token.
    image_url must be a publicly accessible HTTPS URL.
    """
    account_id = IG_IDS.get(account, "")
    if not INSTA_TOKEN or not account_id:
        return (
            f"📋 *Manual post needed for {account}*\n\n"
            f"Auto-posting requires Facebook Business Manager setup.\n"
            f"To enable: set INSTAGRAM_ACCESS_TOKEN + {account.upper().replace('@','')}_IG_ACCOUNT_ID in SSM.\n\n"
            f"_For now: copy the caption above and post manually on Instagram._"
        )

    if not image_url:
        return (
            "⚠️ Auto-posting needs an image URL.\n"
            "Upload your Canva design to Cloudinary or Imgur, paste the URL, then say:\n"
            f"'post to {account} with image: [URL]'"
        )

    import aiohttp
    async with aiohttp.ClientSession() as session:
        # Step 1: create media container
        async with session.post(
            f"https://graph.facebook.com/v19.0/{account_id}/media",
            data={"image_url": image_url, "caption": caption, "access_token": INSTA_TOKEN}
        ) as resp:
            data = await resp.json()
            if "error" in data:
                return f"❌ IG API error: {data['error']['message']}"
            container_id = data.get("id")

        # Step 2: publish
        async with session.post(
            f"https://graph.facebook.com/v19.0/{account_id}/media_publish",
            data={"creation_id": container_id, "access_token": INSTA_TOKEN}
        ) as resp:
            pub = await resp.json()
            if "error" in pub:
                return f"❌ IG publish error: {pub['error']['message']}"
            return f"✅ Posted to {account}! ID: {pub.get('id', 'unknown')}"
