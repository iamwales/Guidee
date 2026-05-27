import base64
from collections.abc import AsyncIterator
from typing import Any, cast

import anthropic

from app.core.config import Settings
from app.models.schemas import ChatTurn

SYSTEM_PROMPT = """
You are Guidee, a helpful AI assistant that lives on the user's desktop.
You can see their screen and hear their voice.

Your personality:
- Concise and direct. Never pad answers.
- Conversational, warm, not corporate.
- If you're unsure what's on screen, say so and ask.

Response format:
- For quick questions: 1–3 sentences max.
- For complex explanations: use short bullet points, no headers.
- For code: use code blocks.
- Never say "As an AI language model..." or similar filler.

When the user asks about something on their screen, describe what you
see in the screenshot before answering, unless it's obvious.
""".strip()

def build_messages(
    transcript: str,
    screenshot_b64: str | None,
    history: list[ChatTurn],
    screenshot_media_type: str | None = "image/jpeg",
) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = []
    for turn in history[-10:]:
        messages.append({"role": turn.role, "content": turn.content})

    user_content: list[dict[str, Any]] = []
    image_block = build_image_block(screenshot_b64, screenshot_media_type)
    if image_block:
        user_content.append(image_block)
    user_content.append({"type": "text", "text": transcript})
    messages.append({"role": "user", "content": user_content})
    return messages


def build_image_block(
    screenshot_b64: str | None,
    media_type: str | None = "image/jpeg",
) -> dict[str, Any] | None:
    if not screenshot_b64:
        return None

    if media_type != "image/jpeg":
        raise ValueError("Only JPEG screenshots are supported")

    data = screenshot_b64.strip()
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


class ClaudeService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._client: anthropic.AsyncAnthropic | None = None

    @property
    def client(self) -> anthropic.AsyncAnthropic:
        if self._client is None:
            self._client = anthropic.AsyncAnthropic(
                api_key=self.settings.anthropic_api_key
            )
        return self._client

    async def stream_chat(
        self,
        messages: list[dict[str, Any]],
        system: str = SYSTEM_PROMPT,
        max_tokens: int | None = None,
    ) -> AsyncIterator[str]:
        max_tokens = max_tokens or self.settings.chat_max_tokens
        async with self.client.messages.stream(
            model=self.settings.claude_model,
            max_tokens=max_tokens,
            system=system,
            messages=cast(Any, messages),
        ) as stream:
            async for text in stream.text_stream:
                yield text

    async def complete(
        self,
        user_message: str,
        system: str,
        max_tokens: int = 1024,
        image_b64: str | None = None,
        image_media_type: str | None = "image/jpeg",
    ) -> str:
        content: list[dict[str, Any]] = []
        image_block = build_image_block(image_b64, image_media_type)
        if image_block:
            content.append(image_block)
        content.append({"type": "text", "text": user_message})

        msg = await self.client.messages.create(
            model=self.settings.claude_model,
            max_tokens=max_tokens,
            system=system,
            messages=cast(Any, [{"role": "user", "content": content}]),
        )
        parts = []
        for block in msg.content:
            if hasattr(block, "text"):
                parts.append(block.text)
        return "".join(parts)
