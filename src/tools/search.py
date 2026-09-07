"""
Web search — Gemini Flash with Google Search grounding (free, 1500 req/day).
Falls back to DuckDuckGo HTML scrape if Gemini key not set.
"""

import os
import aiohttp
import re
from urllib.parse import quote_plus

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")


async def web_search(query: str) -> str:
    if not query:
        return "No query provided."

    if GEMINI_API_KEY:
        try:
            result = await _gemini_search(query)
            if result and len(result) > 30:
                return result
        except Exception:
            pass  # Fall through to DDG

    return await _ddg_search(query)


async def _gemini_search(query: str) -> str:
    import google.generativeai as genai
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-1.5-flash", tools="google_search_retrieval")
    response = model.generate_content(
        f"Search: {query}\n\n"
        f"Provide a concise factual summary with key data, numbers, and dates. "
        f"Max 250 words. Include source names where available."
    )
    return response.text.strip() if response.text else ""


async def _ddg_search(query: str) -> str:
    results = []
    async with aiohttp.ClientSession() as session:
        # Instant Answer API
        try:
            url = f"https://api.duckduckgo.com/?q={quote_plus(query)}&format=json&no_html=1&skip_disambig=1"
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=8)) as resp:
                data = await resp.json(content_type=None)
            if data.get("AbstractText"):
                results.append(data["AbstractText"][:400])
            for topic in (data.get("RelatedTopics") or [])[:2]:
                if isinstance(topic, dict) and topic.get("Text"):
                    results.append(topic["Text"][:150])
        except Exception:
            pass

        # HTML fallback
        if not results:
            try:
                headers = {"User-Agent": "Mozilla/5.0 (compatible; JarvisBot/2.0)"}
                html_url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
                async with session.get(html_url, headers=headers,
                                       timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    html = await resp.text()
                snippets = re.findall(r'class="result__snippet"[^>]*>(.*?)</(?:a|span)>',
                                      html, re.DOTALL)
                titles = re.findall(r'class="result__a"[^>]*>(.*?)</a>', html, re.DOTALL)
                clean = lambda t: re.sub(r'<[^>]+>', '', t).strip()
                for title, snippet in zip(titles[:4], snippets[:4]):
                    results.append(f"{clean(title)}: {clean(snippet)[:160]}")
            except Exception:
                pass

    return "\n".join(results) if results else f"No results found for: {query}"
