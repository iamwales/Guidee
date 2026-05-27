import base64
import json
import re
from typing import Any

from config import get_settings
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import SecretStr

_client: ChatAnthropic | None = None


def get_llm(max_tokens: int = 1024) -> ChatAnthropic:
    global _client
    settings = get_settings()
    if _client is None:
        _client = ChatAnthropic(  # type: ignore[call-arg]
            model=settings.claude_model,
            api_key=SecretStr(settings.anthropic_api_key or "placeholder"),
            max_tokens=max_tokens,
        )
    return _client


def _image_content(image_b64: str, media_type: str = "image/jpeg") -> dict[str, Any]:
    if media_type != "image/jpeg":
        raise ValueError("Only JPEG screenshots are supported")

    data = image_b64.strip()
    if data.startswith("data:"):
        _, _, data = data.partition(",")
    base64.b64decode(data, validate=True)
    return {
        "type": "image",
        "source": {
            "type": "base64",
            "media_type": media_type,
            "data": data,
        },
    }


async def complete_json(
    system: str,
    user: str,
    max_tokens: int = 1024,
    image_b64: str | None = None,
    image_media_type: str = "image/jpeg",
) -> dict:
    llm = get_llm(max_tokens)
    user_content: str | list[dict[str, Any]]
    if image_b64:
        user_content = [
            _image_content(image_b64, image_media_type),
            {"type": "text", "text": user},
        ]
    else:
        user_content = user
    messages = [SystemMessage(content=system), HumanMessage(content=user_content)]
    resp = await llm.ainvoke(messages)
    text = resp.content if isinstance(resp.content, str) else str(resp.content)
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        return {}
    try:
        return json.loads(match.group())
    except json.JSONDecodeError:
        return {}
