from html.parser import HTMLParser
from urllib.parse import urlparse

import httpx
from config import get_settings

MAX_FETCH_CHARS = 12_000


class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self._skip_depth = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs):
        _ = attrs
        if tag in {"script", "style", "noscript", "svg"}:
            self._skip_depth += 1

    def handle_endtag(self, tag: str):
        if tag in {"script", "style", "noscript", "svg"} and self._skip_depth:
            self._skip_depth -= 1

    def handle_data(self, data: str):
        if self._skip_depth:
            return
        clean = " ".join(data.split())
        if clean:
            self.parts.append(clean)

    @property
    def text(self) -> str:
        return " ".join(self.parts)


async def web_search(query: str, num_results: int = 5) -> dict:
    settings = get_settings()
    count = max(1, min(num_results, 10))
    if not settings.brave_search_api_key:
        return {
            "query": query,
            "source": "dev",
            "results": [
                {
                    "title": f"[Dev] Result for: {query}",
                    "url": "https://example.com",
                    "snippet": "Configure BRAVE_SEARCH_API_KEY for live search.",
                }
            ]
        }

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://api.search.brave.com/res/v1/web/search",
                params={"q": query, "count": count},
                headers={"X-Subscription-Token": settings.brave_search_api_key},
                timeout=15.0,
            )
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as exc:
        retry_after = exc.response.headers.get("retry-after")
        return {
            "query": query,
            "source": "brave",
            "error": f"Brave Search returned HTTP {exc.response.status_code}",
            "retry_after": retry_after,
            "results": [],
        }
    except httpx.HTTPError as exc:
        return {
            "query": query,
            "source": "brave",
            "error": str(exc),
            "results": [],
        }

    results = data.get("web", {}).get("results", [])
    return {
        "query": query,
        "source": "brave",
        "results": [
            {
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "snippet": r.get("description", ""),
                "age": r.get("age"),
            }
            for r in results[:count]
            if r.get("url")
        ],
    }


async def fetch_url(url: str, max_chars: int = MAX_FETCH_CHARS) -> dict:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return {"url": url, "error": "Only HTTP and HTTPS URLs can be fetched"}

    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            headers={"User-Agent": "GuideeResearchBot/0.1"},
        ) as client:
            resp = await client.get(url, timeout=15.0)
            resp.raise_for_status()
    except httpx.HTTPStatusError as exc:
        return {
            "url": url,
            "error": f"Fetch returned HTTP {exc.response.status_code}",
        }
    except httpx.HTTPError as exc:
        return {"url": url, "error": str(exc)}

    content_type = resp.headers.get("content-type", "")
    text = resp.text
    if "html" in content_type:
        extractor = TextExtractor()
        extractor.feed(text)
        text = extractor.text
    else:
        text = " ".join(text.split())

    return {
        "url": str(resp.url),
        "status_code": resp.status_code,
        "content_type": content_type,
        "text": text[:max_chars],
    }
