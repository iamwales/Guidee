import json
import re
from typing import TYPE_CHECKING, Literal

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

Routing rules:
- Prefer instant for direct questions, explanation, summarization, and screen Q&A.
- Prefer browser only when interaction with a website/app UI is required.
- Prefer research only when fresh web information or external lookup is required.
- Prefer file only when local files, folders, PDFs, spreadsheets, or
  documents are needed.
- Prefer email only for email composition, replies, or sending.
- Use clarify when confidence is below 0.55 or the request lacks a concrete target.

Respond with JSON only:
{
  "route": "...",
  "reasoning": "...",
  "clarify_question": null or "...",
  "task": null or "refined task",
  "confidence": 0.0 to 1.0
}
""".strip()

ROUTES = {"instant", "browser", "research", "file", "email", "clarify"}
AGENT_ROUTES = {"browser", "research", "file", "email"}
MIN_CONFIDENCE = 0.55

CLARIFY_PATTERNS = (
    r"^(help|help me|do it|fix it|handle it|take care of it|continue)$",
    r"^(this|that|it)$",
)

EMAIL_KEYWORDS = (
    "email",
    "mail",
    "reply",
    "respond to",
    "draft a reply",
    "send a message",
)
FILE_KEYWORDS = (
    "file",
    "folder",
    "pdf",
    "document",
    "docx",
    "spreadsheet",
    "csv",
    "xlsx",
    "local",
    "downloaded",
)
RESEARCH_KEYWORDS = (
    "research",
    "search the web",
    "look up",
    "latest",
    "today",
    "news",
    "price",
    "compare",
    "find online",
)
BROWSER_KEYWORDS = (
    "click",
    "open",
    "navigate",
    "go to",
    "fill",
    "submit",
    "login",
    "sign in",
    "download",
    "export",
    "select",
)
INSTANT_PREFIXES = (
    "what",
    "why",
    "how",
    "explain",
    "summarize",
    "define",
    "tell me",
    "is this",
)


def detect_intent_prefix(transcript: str) -> tuple[str, str] | None:
    """Legacy voice prefix: 'guidee agent,' forces agent route."""
    lower = transcript.lower().strip()
    if lower.startswith(("guidee agent,", "agent,")):
        task = transcript.split(",", 1)[1].strip()
        return ("agent", task)
    return None


def classify_with_rules(
    transcript: str,
    has_screenshot: bool = False,
) -> SupervisorResponse | None:
    text = transcript.strip()
    lower = text.lower()
    if not text:
        return SupervisorResponse(
            route="clarify",
            reasoning="Empty request",
            clarify_question="What would you like me to do?",
            confidence=1.0,
            source="rules",
        )

    if any(re.search(pattern, lower) for pattern in CLARIFY_PATTERNS):
        return SupervisorResponse(
            route="clarify",
            reasoning="Request is too ambiguous to route safely",
            clarify_question="What should I do with it?",
            confidence=0.95,
            source="rules",
        )

    if any(keyword in lower for keyword in EMAIL_KEYWORDS):
        return _rule_response("email", text, "Email intent keyword")

    if any(keyword in lower for keyword in FILE_KEYWORDS):
        return _rule_response("file", text, "File or document intent keyword")

    if any(keyword in lower for keyword in RESEARCH_KEYWORDS):
        return _rule_response("research", text, "Research intent keyword")

    if any(keyword in lower for keyword in BROWSER_KEYWORDS):
        return _rule_response("browser", text, "Browser action intent keyword")

    if lower.startswith(INSTANT_PREFIXES) or has_screenshot:
        return SupervisorResponse(
            route="instant",
            reasoning="Direct question or screen Q&A",
            task=None,
            confidence=0.78,
            source="rules",
        )

    return None


def _rule_response(
    route: Literal["browser", "research", "file", "email"],
    task: str,
    reasoning: str,
) -> SupervisorResponse:
    return SupervisorResponse(
        route=route,
        reasoning=reasoning,
        task=task,
        confidence=0.86,
        source="rules",
    )


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
            confidence=1.0,
            source="rules",
        )

    rule_result = classify_with_rules(transcript, has_screenshot=bool(screenshot_b64))
    if rule_result and rule_result.route in {"clarify", "email", "file", "research"}:
        return rule_result

    prompt = f"User request:\n{transcript}\n\nClassify and route."
    try:
        raw = await claude.complete(
            prompt,
            system=SUPERVISOR_PROMPT,
            max_tokens=256,
            image_b64=screenshot_b64,
            image_media_type=screenshot_media_type,
        )
    except Exception:
        return rule_result or SupervisorResponse(
            route="instant",
            reasoning="Supervisor unavailable; using safe instant fallback",
            confidence=0.4,
            source="fallback",
        )

    # Extract JSON from response
    match = re.search(r"\{[\s\S]*\}", raw)
    if not match:
        return rule_result or SupervisorResponse(
            route="instant",
            reasoning="Fallback to instant",
            confidence=0.4,
            source="fallback",
        )

    try:
        data = json.loads(match.group())
        route = data.get("route", "instant")
        if route not in ROUTES:
            return rule_result or SupervisorResponse(
                route="instant",
                reasoning="Unknown route fallback",
                confidence=0.4,
                source="fallback",
            )
        confidence = _parse_confidence(data.get("confidence"))
        if confidence < MIN_CONFIDENCE and route != "clarify":
            return SupervisorResponse(
                route="clarify",
                reasoning=data.get("reasoning", "Low confidence route"),
                clarify_question=(
                    data.get("clarify_question")
                    or "Should I answer directly or run an agent for this?"
                ),
                task=None,
                confidence=confidence,
                source="claude",
            )
        return SupervisorResponse(
            route=route,
            reasoning=data.get("reasoning", ""),
            clarify_question=data.get("clarify_question"),
            task=data.get("task") or (transcript if route in AGENT_ROUTES else None),
            confidence=confidence,
            source="claude",
        )
    except json.JSONDecodeError:
        return rule_result or SupervisorResponse(
            route="instant",
            reasoning="Parse error fallback",
            confidence=0.4,
            source="fallback",
        )


def _parse_confidence(value: object) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return 0.5
