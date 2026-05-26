from llm import complete_json
from state import AgentState

INSTRUCTION_SYSTEM = """
Combine UI understanding and selectors into an ordered action plan.
Output JSON:
{
  "actions": [
    {"type": "click|fill|goto|screenshot", "selector": "...", "value": "..."}
  ]
}
Insert screenshot() actions after steps that may change the UI.
"""


async def run(state: AgentState) -> AgentState:
    data = await complete_json(
        INSTRUCTION_SYSTEM,
        (
            f"Task: {state.get('task')}\n"
            f"Vision: {state.get('vision_context')}\n"
            f"Selectors: {state.get('dom_selectors')}"
        ),
        max_tokens=1024,
    )
    actions = data.get("actions", [])
    return {
        **state,
        "action_plan": actions,
        "progress_message": f"Planned {len(actions)} UI actions",
    }
