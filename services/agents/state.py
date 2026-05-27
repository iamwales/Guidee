from typing import Annotated, Any, TypedDict

from langgraph.graph.message import add_messages


class AgentState(TypedDict, total=False):
    task: str
    route: str
    plan: list[str]
    messages: Annotated[list[Any], add_messages]
    tool_results: list[dict]
    step: int
    status: str
    result: str | None
    screenshot_b64: str | None
    screenshot_media_type: str | None
    screenshot_metadata: dict | None
    html: str | None
    vision_context: dict | None
    dom_selectors: dict | None
    action_plan: list[dict] | None
    user_id: str
    task_id: str
    progress_message: str
