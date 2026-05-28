from llm import complete_text
from state import AgentState
from tools.web_search import fetch_url, web_search

SYNTHESIS_SYSTEM = """
You are Guidee's research synthesizer.
Answer the user's task using only the provided sources.
Include concise citations as [1], [2], etc. Do not invent sources.
If sources are weak, say what is missing.
""".strip()


async def search(state: AgentState) -> AgentState:
    task = state.get("task", "")
    result = await web_search(task, num_results=5)
    results = result.get("results", [])
    return {
        **state,
        "research_query": task,
        "search_results": results,
        "tool_results": [
            *state.get("tool_results", []),
            {"tool": "web_search", "result": result},
        ],
        "status": "running",
        "progress_message": (
            result.get("error")
            or f"Found {len(results)} search result{'s' if len(results) != 1 else ''}"
        ),
    }


async def fetch_sources(state: AgentState) -> AgentState:
    search_results = state.get("search_results", []) or []
    sources = []
    tool_results = list(state.get("tool_results", []))

    for index, item in enumerate(search_results[:3], start=1):
        url = item.get("url")
        if not url:
            continue
        fetched = await fetch_url(url)
        source = {
            "id": index,
            "title": item.get("title") or url,
            "url": fetched.get("url") or url,
            "snippet": item.get("snippet", ""),
            "text": fetched.get("text", ""),
            "error": fetched.get("error"),
        }
        sources.append(source)
        tool_results.append(
            {"tool": "fetch_url", "input": {"url": url}, "result": fetched}
        )

    source_count = len(sources)

    return {
        **state,
        "sources": sources,
        "tool_results": tool_results,
        "progress_message": (
            f"Fetched {source_count} source page"
            f"{'s' if source_count != 1 else ''}"
        ),
    }


async def synthesize(state: AgentState) -> AgentState:
    task = state.get("task", "")
    sources = state.get("sources", []) or []
    if not sources:
        return {
            **state,
            "status": "failed",
            "result": "I could not find usable sources for this research task.",
            "progress_message": "No usable research sources",
        }

    source_text = "\n\n".join(
        (
            f"[{source['id']}] {source['title']}\n"
            f"URL: {source['url']}\n"
            f"Snippet: {source.get('snippet', '')}\n"
            "Content: "
            f"{source.get('text') or source.get('error') or 'No text extracted'}"
        )
        for source in sources
    )
    summary = await complete_text(
        SYNTHESIS_SYSTEM,
        f"Task: {task}\n\nSources:\n{source_text}",
        max_tokens=1200,
    )
    if not summary:
        summary = synthesize_without_llm(task, sources)

    citations = [
        {"id": source["id"], "title": source["title"], "url": source["url"]}
        for source in sources
    ]
    return {
        **state,
        "status": "done",
        "result": summary,
        "citations": citations,
        "progress_message": "Synthesized research answer",
    }


def synthesize_without_llm(task: str, sources: list[dict]) -> str:
    lines = [f"Research results for: {task}", ""]
    for source in sources:
        text = source.get("text") or source.get("snippet") or source.get("error") or ""
        excerpt = text[:500].strip()
        lines.append(f"[{source['id']}] {source['title']}")
        if excerpt:
            lines.append(excerpt)
        lines.append(f"Source: {source['url']}")
        lines.append("")
    return "\n".join(lines).strip()
