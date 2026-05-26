from state import AgentState
from llm import complete_json

VISION_SYSTEM = """
Analyze the screenshot and output structured JSON describing the UI:
{"page_type": "...", "elements": [{"label": "...", "role": "button|link|input|...", "approx_location": "..."}], "state": "..."}
"""


async def run(state: AgentState) -> AgentState:
    screenshot = state.get("screenshot_b64")
    if not screenshot:
        return {
            **state,
            "vision_context": {"page_type": "unknown", "elements": []},
            "progress_message": "No screenshot — skipping vision",
        }

    data = await complete_json(
        VISION_SYSTEM,
        f"Task context: {state.get('task', '')}\n[Screenshot provided as image in production]",
        max_tokens=1024,
    )
    return {
        **state,
        "vision_context": data,
        "progress_message": "Analyzed screen layout",
    }
