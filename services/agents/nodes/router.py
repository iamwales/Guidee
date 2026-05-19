from state import AgentState


def should_continue(state: AgentState) -> str:
    status = state.get("status", "")
    if status == "failed":
        return "error"
    plan = state.get("plan", [])
    step = state.get("step", 0)
    if step >= len(plan):
        return "summarize"
    return "continue"
