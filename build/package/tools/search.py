"""
tools/search.py — free web search via DuckDuckGo HTML scrape (no API key needed).
"""
import urllib.request
import urllib.parse
import re


def web_search(query: str, max_results: int = 5) -> str:
    url = "https://html.duckduckgo.com/html/?" + urllib.parse.urlencode({"q": query})
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
    except Exception as e:
        return f"Search failed: {e}"

    titles = re.findall(r'class="result__a"[^>]*>(.*?)</a>', html)
    snippets = re.findall(r'class="result__snippet"[^>]*>(.*?)</a>', html)

    results = []
    for i, title in enumerate(titles[:max_results]):
        clean_title = re.sub("<.*?>", "", title)
        snippet = re.sub("<.*?>", "", snippets[i]) if i < len(snippets) else ""
        results.append(f"{i+1}. {clean_title} — {snippet}")

    if not results:
        return "No results found."
    return "\n".join(results)
