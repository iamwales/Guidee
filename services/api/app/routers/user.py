from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.config import Settings, get_settings
from app.core.rate_limit import limit_for_plan
from app.core.security import AuthUser, get_current_user
from app.models.schemas import UserMeResponse, UserUsageResponse
from app.services.history import HistoryStore

router = APIRouter(prefix="/user", tags=["user"])


@router.get("/me", response_model=UserMeResponse)
async def get_user_profile(
    user: Annotated[AuthUser, Depends(get_current_user)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> UserMeResponse:
    profile = await HistoryStore(settings).upsert_profile(
        user_id=user.clerk_id,
        email=user.email,
        plan=user.plan,
    )
    return UserMeResponse(
        clerk_id=user.clerk_id,
        email=user.email,
        plan=str(profile.get("plan", user.plan)) if profile else user.plan,
    )


@router.get("/usage", response_model=UserUsageResponse)
async def get_usage(
    user: Annotated[AuthUser, Depends(get_current_user)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> UserUsageResponse:
    return UserUsageResponse(
        plan=user.plan,
        chat_limit_per_minute=limit_for_plan(
            user.plan,
            "/chat/stream",
            settings,
            settings.rate_limit_chat,
        ),
        agent_limit_per_minute=limit_for_plan(
            user.plan,
            "/agent/dispatch",
            settings,
            settings.rate_limit_agent,
        ),
    )


@router.get("/history")
async def get_history(
    user: Annotated[AuthUser, Depends(get_current_user)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    return {"tasks": await HistoryStore(settings).list_tasks(user.clerk_id)}
