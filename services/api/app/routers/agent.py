from typing import Annotated

from app.core.config import Settings, get_settings
from app.core.rate_limit import check_rate_limit, get_redis
from app.core.security import AuthUser, get_current_user
from app.models.schemas import (
    AgentDispatchRequest,
    AgentDispatchResponse,
    AgentStatusResponse,
    SupervisorRequest,
)
from app.routers.chat import get_claude
from app.services.claude import ClaudeService
from app.services.redis_queue import TaskStore
from app.services.supervisor import classify_request
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sse_starlette.sse import EventSourceResponse

router = APIRouter(prefix="/agent", tags=["agent"])


def get_tasks(settings: Annotated[Settings, Depends(get_settings)]) -> TaskStore:
    return TaskStore(settings)


@router.post("/dispatch", response_model=AgentDispatchResponse)
async def dispatch_agent(
    request: Request,
    body: AgentDispatchRequest,
    user: Annotated[AuthUser, Depends(get_current_user)],
    settings: Annotated[Settings, Depends(get_settings)],
    tasks: Annotated[TaskStore, Depends(get_tasks)],
    claude: Annotated[ClaudeService, Depends(get_claude)],
):
    r = await get_redis(settings)
    await check_rate_limit(request, user, settings, r, settings.rate_limit_agent)

    route = body.route
    task_text = body.task

    if not route:
        if settings.anthropic_api_key:
            classification = await classify_request(
                claude,
                body.transcript or body.task,
                body.screenshot_b64,
            )
            if classification.route == "clarify":
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    classification.clarify_question or "Please clarify your request",
                )
            if classification.route == "instant":
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    "This request should use /chat/stream instead",
                )
            route = classification.route
            task_text = classification.task or body.task
        else:
            route = "research"

    agent_routes = {"browser", "research", "file", "email"}
    if route not in agent_routes:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Invalid agent route: {route}",
        )

    task_id = await tasks.create_task(
        user.clerk_id,
        task_text,
        route,
        body.screenshot_b64,
    )
    return AgentDispatchResponse(task_id=task_id, route=route, status="pending")


@router.post("/route-and-dispatch", response_model=AgentDispatchResponse)
async def route_and_dispatch(
    request: Request,
    body: SupervisorRequest,
    user: Annotated[AuthUser, Depends(get_current_user)],
    settings: Annotated[Settings, Depends(get_settings)],
    tasks: Annotated[TaskStore, Depends(get_tasks)],
    claude: Annotated[ClaudeService, Depends(get_claude)],
):
    """Supervisor classifies then dispatches if not instant/clarify."""
    r = await get_redis(settings)
    await check_rate_limit(request, user, settings, r, settings.rate_limit_agent)

    classification = await classify_request(
        claude,
        body.transcript,
        body.screenshot_b64,
    )

    if classification.route == "instant":
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail={"message": "Use /chat/stream", "route": "instant"},
        )
    if classification.route == "clarify":
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "route": "clarify",
                "question": classification.clarify_question,
            },
        )

    task_id = await tasks.create_task(
        user.clerk_id,
        classification.task or body.transcript,
        classification.route,
        body.screenshot_b64,
    )
    return AgentDispatchResponse(
        task_id=task_id,
        route=classification.route,
        status="pending",
    )


@router.get("/{task_id}/status", response_model=AgentStatusResponse)
async def get_status(
    task_id: str,
    user: Annotated[AuthUser, Depends(get_current_user)],
    tasks: Annotated[TaskStore, Depends(get_tasks)],
):
    data = await tasks.get_task(task_id)
    if not data or data.get("user_id") != user.clerk_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found")
    return AgentStatusResponse(
        task_id=task_id,
        status=data.get("status", "unknown"),
        route=data.get("route"),
        steps_total=int(data["steps_total"]) if data.get("steps_total") else None,
        steps_done=int(data.get("steps_done", 0)),
        result=data.get("result"),
        error=data.get("error"),
    )


@router.get("/{task_id}/stream")
async def stream_agent_progress(
    task_id: str,
    user: Annotated[AuthUser, Depends(get_current_user)],
    tasks: Annotated[TaskStore, Depends(get_tasks)],
):
    data = await tasks.get_task(task_id)
    if not data or data.get("user_id") != user.clerk_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found")

    async def event_generator():
        import json

        async for event in tasks.subscribe_progress(task_id):
            yield {"event": event.get("type", "progress"), "data": json.dumps(event)}

    return EventSourceResponse(event_generator())


@router.delete("/{task_id}")
async def cancel_task(
    task_id: str,
    user: Annotated[AuthUser, Depends(get_current_user)],
    tasks: Annotated[TaskStore, Depends(get_tasks)],
):
    data = await tasks.get_task(task_id)
    if not data or data.get("user_id") != user.clerk_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found")
    ok = await tasks.cancel_task(task_id)
    if not ok:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cannot cancel task")
    return {"status": "cancelled"}
