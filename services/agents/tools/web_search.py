import httpx
from agents.config import get_settings


async def web_search(query: str, num_results: int = 5) -> dict:
    settings = get_settings()
    if not settings.brave_search_api_key:
        return {
            "results": [
                {
                    "title": f"[Dev] Result for: {query}",
                    "url": "https://example.com",
                    "snippet": "Configure BRAVE_SEARCH_API_KEY for live search.",
                }
            ]
        }

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://api.search.brave.com/res/v1/web/search",
            params={"q": query, "count": num_results},
            headers={"X-Subscription-Token": settings.brave_search_api_key},
            timeout=15.0,
        )
        resp.raise_for_status()
        data = resp.json()

    results = data.get("web", {}).get("results", [])
    return {
        "results": [
            {
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "snippet": r.get("description", ""),
            }
            for r in results[:num_results]
        ]
    }
