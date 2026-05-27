import json
import re
from typing import TYPE_CHECKING

from app.models.schemas import SupervisorResponse

if TYPE_CHECKING:
    from app.services.claude import ClaudeService

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
{
  "route": "...",
  "reasoning": "...",
  "clarify_question": null or "...",
  "task": null or "refined task"
}
""".strip()


def detect_intent_prefix(transcript: str) -> tuple[str, str] | None:
    """Legacy voice prefix: 'guidee agent,' forces agent route."""
    lower = transcript.lower().strip()
    if lower.startswith(("guidee agent,", "agent,")):
        task = transcript.split(",", 1)[1].strip()
        return ("agent", task)
    return None


async def classify_request(
    claude: "ClaudeService",
    transcript: str,
    screenshot_b64: str | None,
    screenshot_media_type: str | None = "image/jpeg",
) -> SupervisorResponse:
    prefix = detect_intent_prefix(transcript)
    if prefix:
        return SupervisorResponse(
            route="research",
            reasoning="Explicit agent prefix",
            task=prefix[1],
        )

    prompt = f"User request:\n{transcript}\n\nClassify and route."
    raw = await claude.complete(
        prompt,
        system=SUPERVISOR_PROMPT,
        max_tokens=256,
        image_b64=screenshot_b64,
        image_media_type=screenshot_media_type,
    )

    # Extract JSON from response
    match = re.search(r"\{[\s\S]*\}", raw)
    if not match:
        return SupervisorResponse(route="instant", reasoning="Fallback to instant")

    try:
        data = json.loads(match.group())
        route = data.get("route", "instant")
        valid = {"instant", "browser", "research", "file", "email", "clarify"}
        if route not in valid:
            route = "instant"
        return SupervisorResponse(
            route=route,
            reasoning=data.get("reasoning", ""),
            clarify_question=data.get("clarify_question"),
            task=data.get("task") or transcript,
        )
    except json.JSONDecodeError:
        return SupervisorResponse(route="instant", reasoning="Parse error fallback")
