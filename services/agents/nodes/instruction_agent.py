from state import AgentState
from llm import complete_json

INSTRUCTION_SYSTEM = """
Combine UI understanding and selectors into an ordered action plan.
Output JSON: {"actions": [{"type": "click|fill|goto|screenshot", "selector": "...", "value": "..."}]}
Insert screenshot() actions after steps that may change the UI.
"""


async def run(state: AgentState) -> AgentState:
    data = await complete_json(
        INSTRUCTION_SYSTEM,
        f"Task: {state.get('task')}\nVision: {state.get('vision_context')}\nSelectors: {state.get('dom_selectors')}",
        max_tokens=1024,
    )
    actions = data.get("actions", [])
    return {
        **state,
        "action_plan": actions,
        "progress_message": f"Planned {len(actions)} UI actions",
    }
