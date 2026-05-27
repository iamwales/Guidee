from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sse_starlette.sse import EventSourceResponse

from app.core.config import Settings, get_settings
from app.core.rate_limit import check_rate_limit, get_redis
from app.core.security import AuthUser, get_current_user
from app.models.schemas import ChatRequest, SupervisorRequest, SupervisorResponse
from app.services.claude import FALLBACK_RESPONSE, ClaudeService, build_messages
from app.services.supervisor import classify_request, classify_with_rules

router = APIRouter(prefix="/chat", tags=["chat"])


def get_claude(settings: Annotated[Settings, Depends(get_settings)]) -> ClaudeService:
    return ClaudeService(settings)


@router.post("/supervisor", response_model=SupervisorResponse)
async def supervisor_route(
    body: SupervisorRequest,
    user: Annotated[AuthUser, Depends(get_current_user)],
    claude: Annotated[ClaudeService, Depends(get_claude)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> SupervisorResponse:
    _ = user
    if not settings.has_llm_api_key:
        return classify_with_rules(
            body.transcript,
            has_screenshot=bool(body.screenshot_b64),
        ) or SupervisorResponse(
            route="instant",
            reasoning="No API key; safe instant fallback",
            confidence=0.4,
            source="fallback",
        )
    return await classify_request(
        claude,
        body.transcript,
        body.screenshot_b64,
        body.screenshot_media_type,
    )


@router.post("/stream")
async def stream_chat(
    request: Request,
    body: ChatRequest,
    user: Annotated[AuthUser, Depends(get_current_user)],
    claude: Annotated[ClaudeService, Depends(get_claude)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    r = await get_redis(settings)
    await check_rate_limit(request, user, settings, r, settings.rate_limit_chat)

    messages = build_messages(
        body.transcript,
        body.screenshot_b64,
        body.history,
        body.screenshot_media_type,
    )

    async def event_generator():
        if not settings.has_llm_api_key:
            yield {"data": FALLBACK_RESPONSE}
            return
        try:
            async for token in claude.stream_chat(messages):
                if await request.is_disconnected():
                    break
                yield {"data": token}
        except Exception:
            yield {"data": FALLBACK_RESPONSE}

    return EventSourceResponse(event_generator())
