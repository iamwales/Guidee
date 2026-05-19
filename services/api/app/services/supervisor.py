import json
import re

from app.models.schemas import SupervisorResponse
from app.services.claude import ClaudeService, SUPERVISOR_PROMPT


def detect_intent_prefix(transcript: str) -> tuple[str, str] | None:
    """Legacy voice prefix: 'guidee agent,' forces agent route."""
    lower = transcript.lower().strip()
    if lower.startswith(("guidee agent,", "agent,")):
        task = transcript.split(",", 1)[1].strip()
        return ("agent", task)
    return None


async def classify_request(
    claude: ClaudeService,
    transcript: str,
    screenshot_b64: str | None,
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
