from collections.abc import AsyncIterator

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

SUPERVISOR_PROMPT = """
You are the Guidee Supervisor. You NEVER answer the user's question or perform tasks.
You ONLY classify the request and route it.

Routes:
- instant: quick Q&A about what's on screen, explanations, "what does this do"
- browser: requires clicking, typing, navigating UI, exporting, filling forms
- research: web research, finding products, summarizing topics from the web
- file: read/summarize/analyze local files, PDFs, notes
- email: compose, draft, or send email
- clarify: intent is ambiguous; ask ONE short clarifying question

Respond with JSON only:
{"route": "...", "reasoning": "...", "clarify_question": null or "...", "task": null or "refined task"}
""".strip()


def build_messages(
    transcript: str,
    screenshot_b64: str | None,
    history: list[ChatTurn],
) -> list[dict]:
    messages: list[dict] = []
    for turn in history[-10:]:
        messages.append({"role": turn.role, "content": turn.content})

    user_content: list[dict] = []
    if screenshot_b64:
        user_content.append(
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": screenshot_b64,
                },
            }
        )
    user_content.append({"type": "text", "text": transcript})
    messages.append({"role": "user", "content": user_content})
    return messages


class ClaudeService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._client: anthropic.AsyncAnthropic | None = None

    @property
    def client(self) -> anthropic.AsyncAnthropic:
        if self._client is None:
            self._client = anthropic.AsyncAnthropic(api_key=self.settings.anthropic_api_key)
        return self._client

    async def stream_chat(
        self,
        messages: list[dict],
        system: str = SYSTEM_PROMPT,
        max_tokens: int | None = None,
    ) -> AsyncIterator[str]:
        max_tokens = max_tokens or self.settings.chat_max_tokens
        async with self.client.messages.stream(
            model=self.settings.claude_model,
            max_tokens=max_tokens,
            system=system,
            messages=messages,
        ) as stream:
            async for text in stream.text_stream:
                yield text

    async def complete(
        self,
        user_message: str,
        system: str,
        max_tokens: int = 1024,
        image_b64: str | None = None,
    ) -> str:
        content: list[dict] = []
        if image_b64:
            content.append(
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/jpeg",
                        "data": image_b64,
                    },
                }
            )
        content.append({"type": "text", "text": user_message})

        msg = await self.client.messages.create(
            model=self.settings.claude_model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": content}],
        )
        parts = []
        for block in msg.content:
            if hasattr(block, "text"):
                parts.append(block.text)
        return "".join(parts)
