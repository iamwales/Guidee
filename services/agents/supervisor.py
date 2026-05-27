"""
Supervisor — entry point for all agent work in the worker.
Maps route strings to compiled LangGraph agents.
"""

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

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

NODE_TOTALS = {
    "browser": 5,
    "research": 3,
    "file": 3,
    "email": 3,
}

ProgressCallback = Callable[[dict[str, Any]], Awaitable[None]]
CancelCheck = Callable[[], Awaitable[bool]]


async def run_agent(
    route: str,
    initial_state: dict,
    on_progress: ProgressCallback | None = None,
    is_cancelled: CancelCheck | None = None,
    timeout_seconds: int = 300,
    retry_attempts: int = 1,
) -> dict:
    graph = ROUTE_GRAPHS.get(route)
    if not graph:
        raise ValueError(f"Unknown route: {route}")

    attempt = 0
    last_error: Exception | None = None
    while attempt <= retry_attempts:
        try:
            async with asyncio.timeout(timeout_seconds):
                return await _run_graph_stream(
                    graph,
                    route,
                    initial_state,
                    on_progress,
                    is_cancelled,
                    attempt,
                )
        except asyncio.CancelledError:
            raise
        except Exception as error:
            last_error = error
            if on_progress:
                await on_progress(
                    {
                        "type": "retry" if attempt < retry_attempts else "error",
                        "status": "running" if attempt < retry_attempts else "failed",
                        "message": str(error),
                        "attempt": attempt + 1,
                    }
                )
            attempt += 1
            if attempt <= retry_attempts:
                await asyncio.sleep(min(2**attempt, 8))

    if last_error:
        raise last_error
    raise RuntimeError("Agent failed without an error")


async def _run_graph_stream(
    graph: Any,
    route: str,
    initial_state: dict,
    on_progress: ProgressCallback | None,
    is_cancelled: CancelCheck | None,
    attempt: int,
) -> dict:
    state = dict(initial_state)
    step = int(state.get("step", 0))
    total = NODE_TOTALS.get(route, 3)

    async for update in graph.astream(state, stream_mode="updates"):
        if is_cancelled and await is_cancelled():
            return {
                **state,
                "status": "cancelled",
                "progress_message": "Task cancelled",
            }

        for node_name, node_state in update.items():
            if isinstance(node_state, dict):
                state.update(node_state)
            step += 1
            state["step"] = max(int(state.get("step", 0)), step)
            if on_progress:
                await on_progress(
                    {
                        "type": "progress",
                        "status": state.get("status", "running"),
                        "node": node_name,
                        "message": state.get(
                            "progress_message",
                            f"Completed {node_name}",
                        ),
                        "step": min(step, total),
                        "total_steps": total,
                        "attempt": attempt + 1,
                    }
                )

    return state
