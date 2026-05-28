from llm import complete_json
from state import AgentState
from tools.browser import requires_confirmation

INSTRUCTION_SYSTEM = """
Combine UI understanding and selectors into an ordered action plan.
Output JSON:
{
  "actions": [
    {"type": "click|fill|goto|screenshot", "selector": "...", "value": "..."}
  ]
}
Insert screenshot() actions after steps that may change the UI.
Supported action types: goto, click, fill, press, select, wait, screenshot, extract_dom.
Mark sensitive actions with "requires_confirmation": true.
"""

SUPPORTED_ACTIONS = {
    "goto",
    "click",
    "fill",
    "press",
    "select",
    "wait",
    "screenshot",
    "extract_dom",
}


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
    actions = normalize_actions(
        data.get("actions", []),
        state.get("task", ""),
        state.get("dom_selectors") or {},
    )
    return {
        **state,
        "action_plan": actions,
        "progress_message": f"Planned {len(actions)} UI actions",
    }


def normalize_actions(
    actions: list[dict],
    task: str,
    dom_selectors: dict,
) -> list[dict]:
    if not actions:
        actions = fallback_actions(task, dom_selectors)

    normalized = []
    for action in actions:
        action_type = action.get("type")
        if action_type not in SUPPORTED_ACTIONS:
            continue
        clean = {key: value for key, value in action.items() if value is not None}
        if requires_confirmation(clean):
            clean["requires_confirmation"] = True
        normalized.append(clean)

    if normalized and normalized[-1].get("type") != "screenshot":
        normalized.append({"type": "screenshot", "purpose": "verify final page state"})
    return normalized


def fallback_actions(task: str, dom_selectors: dict) -> list[dict]:
    lower = task.lower()
    selectors = dom_selectors.get("selectors") or []
    if "open " in lower or "go to " in lower:
        words = task.split()
        url = next(
            (word for word in words if word.startswith(("http://", "https://"))),
            "",
        )
        if url:
            return [{"type": "goto", "value": url}]

    if any(word in lower for word in ("click", "press", "select")) and selectors:
        return [
            {
                "type": "click",
                "selector": selectors[0].get("selector"),
                "purpose": selectors[0].get("purpose") or selectors[0].get("label"),
            }
        ]

    return [{"type": "extract_dom"}, {"type": "screenshot"}]
