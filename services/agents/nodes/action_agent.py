from state import AgentState
from tools.browser import execute_action
from nodes import vision_agent


async def run(state: AgentState) -> AgentState:
    actions = state.get("action_plan") or []
    results = list(state.get("tool_results", []))

    for i, action in enumerate(actions):
        if action.get("type") == "screenshot":
            # Re-perception loop
            result = await execute_action(action)
            if result.get("screenshot_b64"):
                state = {**state, "screenshot_b64": result["screenshot_b64"]}
                state = await vision_agent.run(state)
            continue

        result = await execute_action(action)
        results.append({"action_index": i, "result": result})

        if result.get("error"):
            return {
                **state,
                "tool_results": results,
                "status": "failed",
                "progress_message": f"Action failed: {result.get('error')}",
            }

    return {
        **state,
        "tool_results": results,
        "status": "done",
        "result": "Browser task completed",
        "progress_message": "All UI actions executed",
    }
