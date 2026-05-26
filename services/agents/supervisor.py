"""
Supervisor — entry point for all agent work in the worker.
Maps route strings to compiled LangGraph agents.
"""

from graphs.browser_graph import browser_graph
from graphs.email_agent import email_agent
from graphs.file_agent import file_agent
from graphs.research_agent import research_agent

ROUTE_GRAPHS = {
    "browser": browser_graph,
    "research": research_agent,
    "file": file_agent,
    "email": email_agent,
}


async def run_agent(route: str, initial_state: dict) -> dict:
    graph = ROUTE_GRAPHS.get(route)
    if not graph:
        raise ValueError(f"Unknown route: {route}")
    result = await graph.ainvoke(initial_state)
    return result
