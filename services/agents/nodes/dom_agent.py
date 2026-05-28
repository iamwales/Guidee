from html.parser import HTMLParser

from llm import complete_json
from state import AgentState
from tools.browser import get_page_snapshot

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


class InteractiveElementParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.elements: list[dict] = []
        self._current: dict | None = None

    def handle_starttag(self, tag: str, attrs):
        attrs_dict = dict(attrs)
        if tag not in {"a", "button", "input", "select", "textarea"}:
            return
        selector = selector_for(tag, attrs_dict, len(self.elements))
        self._current = {
            "tag": tag,
            "role": attrs_dict.get("role") or tag,
            "label": attrs_dict.get("aria-label")
            or attrs_dict.get("placeholder")
            or attrs_dict.get("value")
            or attrs_dict.get("name")
            or "",
            "selector": selector,
            "confidence": 0.72 if selector else 0.4,
        }

    def handle_data(self, data: str):
        if self._current and not self._current.get("label"):
            clean = " ".join(data.split())
            if clean:
                self._current["label"] = clean[:80]

    def handle_endtag(self, tag: str):
        if self._current and self._current.get("tag") == tag:
            self.elements.append(self._current)
            self._current = None


def selector_for(tag: str, attrs: dict, index: int) -> str:
    if attrs.get("data-testid"):
        return f"[data-testid='{attrs['data-testid']}']"
    if attrs.get("id"):
        return f"#{attrs['id']}"
    if attrs.get("name"):
        return f"{tag}[name='{attrs['name']}']"
    if attrs.get("aria-label"):
        return f"{tag}[aria-label='{attrs['aria-label']}']"
    if attrs.get("href") and tag == "a":
        return f"a[href='{attrs['href']}']"
    return f"{tag}:nth-of-type({index + 1})"


def extract_interactive_elements(html: str) -> list[dict]:
    parser = InteractiveElementParser()
    parser.feed(html)
    return parser.elements


async def run(state: AgentState) -> AgentState:
    browser_context = state.get("browser_context") or {}
    html = state.get("html") or browser_context.get("html")
    page_snapshot = browser_context
    if not html:
        page_snapshot = await get_page_snapshot(browser_context.get("url"))
        html = page_snapshot.get("html", "")

    deterministic = extract_interactive_elements(html)

    data = await complete_json(
        DOM_SYSTEM,
        f"HTML excerpt:\n{html[:15000]}",
        max_tokens=1024,
    )
    selectors = data.get("selectors") or deterministic
    return {
        **state,
        "html": html,
        "browser_context": {
            **page_snapshot,
            "html": html,
            "interactive_elements": deterministic,
        },
        "dom_selectors": {"selectors": selectors},
        "progress_message": f"Mapped {len(selectors)} DOM selectors",
    }
