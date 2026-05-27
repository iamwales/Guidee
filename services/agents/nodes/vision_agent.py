from llm import complete_json
from state import AgentState

VISION_SYSTEM = """
Analyze the screenshot and output structured JSON describing the UI:
{
  "page_type": "...",
  "elements": [
    {"label": "...", "role": "button|link|input|...", "approx_location": "..."}
  ],
  "state": "..."
}
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
        f"Task context: {state.get('task', '')}",
        max_tokens=1024,
        image_b64=screenshot,
        image_media_type=state.get("screenshot_media_type") or "image/jpeg",
    )
    return {
        **state,
        "vision_context": data,
        "progress_message": "Analyzed screen layout",
    }
