import base64
import json
import re
from typing import Any

import anthropic
from config import get_settings

_client: anthropic.AsyncAnthropic | None = None


def get_llm() -> anthropic.AsyncAnthropic:
    global _client
    settings = get_settings()
    if _client is None:
        _client = anthropic.AsyncAnthropic(
            api_key=settings.openrouter_api_key,
            base_url=settings.openrouter_anthropic_base_url,
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
    settings = get_settings()
    llm = get_llm()
    user_content: list[dict[str, Any]]
    if image_b64:
        user_content = [
            _image_content(image_b64, image_media_type),
            {"type": "text", "text": user},
        ]
    else:
        user_content = [{"type": "text", "text": user}]
    resp = await llm.messages.create(
        model=settings.claude_model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user_content}],
    )
    text = "".join(
        block.text for block in resp.content if getattr(block, "type", None) == "text"
    )
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        return {}
    try:
        return json.loads(match.group())
    except json.JSONDecodeError:
        return {}
