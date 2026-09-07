"""
tools/search.py — free web search via DuckDuckGo Instant Answer API.
"""
import json
import urllib.parse
import urllib.request


def web_search(query: str, max_results: int = 5) -> str:
    params = {
        "q": query,
        "format": "json",
        "no_html": "1",
        "skip_disambig": "1",
    }
    url = "https://api.duckduckgo.com/" + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            payload = json.loads(resp.read().decode("utf-8", errors="ignore"))
    except Exception as e:
        return f"Search failed: {e}"

    topics = payload.get("RelatedTopics", []) or []
    seen = set()
    results = []

    for topic in topics[:max_results]:
        text = topic.get("Text") or ""
        first_url = topic.get("FirstURL") or ""
        if not text and not first_url:
            continue
        label = text.strip() if text else first_url
        if label in seen:
            continue
        seen.add(label)
        if first_url:
            results.append(f"{len(results) + 1}. {label} — {first_url}")
        else:
            results.append(f"{len(results) + 1}. {label}")

    if not results:
        answer = payload.get("AbstractText") or payload.get("Answer") or "No results found."
        if answer and answer.strip():
            return answer.strip()
        return "No results found."

    return "\n".join(results)
