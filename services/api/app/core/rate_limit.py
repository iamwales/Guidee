import time
from typing import Annotated, Any

import redis.asyncio as redis
from fastapi import Depends, HTTPException, Request, status

from app.core.config import Settings, get_settings
from app.core.security import AuthUser, get_current_user

_redis: redis.Redis | None = None


async def get_redis(settings: Annotated[Settings, Depends(get_settings)]) -> Any:
    global _redis
    if _redis is None:
        _redis = redis.from_url(settings.redis_url, decode_responses=True)
    return _redis


async def check_rate_limit(
    request: Request,
    user: Annotated[AuthUser, Depends(get_current_user)],
    settings: Annotated[Settings, Depends(get_settings)],
    r: Annotated[Any, Depends(get_redis)],
    limit: int,
    window_seconds: int = 60,
) -> None:
    limit = limit_for_plan(user.plan, request.url.path, settings, limit)
    path = request.url.path
    key = f"rl:{user.clerk_id}:{path}:{int(time.time()) // window_seconds}"
    try:
        count = await r.incr(key)
        if count == 1:
            await r.expire(key, window_seconds)
        if count > limit:
            raise HTTPException(
                status.HTTP_429_TOO_MANY_REQUESTS,
                "Rate limit exceeded",
                headers={"Retry-After": str(window_seconds)},
            )
    except redis.RedisError:
        # Fail open if Redis unavailable in dev
        pass


def limit_for_plan(plan: str, path: str, settings: Settings, default: int) -> int:
    normalized = plan.lower()
    if "/agent" in path:
        if normalized == "team":
            return settings.rate_limit_agent_team
        if normalized == "pro":
            return settings.rate_limit_agent_pro
        return default

    if normalized == "team":
        return settings.rate_limit_chat_team
    if normalized == "pro":
        return settings.rate_limit_chat_pro
    return default


def daily_agent_limit_for_plan(plan: str, settings: Settings) -> int:
    normalized = plan.lower()
    if normalized == "team":
        return settings.daily_agent_tasks_team
    if normalized == "pro":
        return settings.daily_agent_tasks_pro
    return settings.daily_agent_tasks_free
