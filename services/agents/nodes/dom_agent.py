from llm import complete_json
from state import AgentState
from tools.browser import get_page_html

DOM_SYSTEM = """
Given HTML, output precise CSS selectors for interactive elements as JSON:
{
  "selectors": [
    {
      "purpose": "submit button",
      "selector": "button[type=submit]",
      "confidence": 0.9
    }
  ]
}
"""


async def run(state: AgentState) -> AgentState:
    html = state.get("html")
    if not html:
        page = await get_page_html()
        html = page.get("html", "")

    data = await complete_json(
        DOM_SYSTEM,
        f"HTML excerpt:\n{html[:15000]}",
        max_tokens=1024,
    )
    return {
        **state,
        "html": html,
        "dom_selectors": data,
        "progress_message": "Mapped DOM selectors",
    }
