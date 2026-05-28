from state import AgentState
from tools.browser import execute_action

from nodes import vision_agent


async def run(state: AgentState) -> AgentState:
    actions = state.get("action_plan") or []
    results = list(state.get("tool_results", []))
    screenshot_checks = 0

    for i, action in enumerate(actions):
        if action.get("requires_confirmation") and action.get("confirmed") is not True:
            return {
                **state,
                "tool_results": results,
                "status": "failed",
                "progress_message": "Browser action needs user confirmation",
                "result": (
                    "I need confirmation before performing a sensitive browser action."
                ),
            }

        if action.get("type") == "screenshot":
            screenshot_checks += 1
            if screenshot_checks > 3:
                continue
            # Re-perception loop
            result = await execute_action(action)
            results.append({"action_index": i, "result": result})
            if result.get("screenshot_b64"):
                state = {
                    **state,
                    "screenshot_b64": result["screenshot_b64"],
                    "screenshot_media_type": "image/jpeg",
                }
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
