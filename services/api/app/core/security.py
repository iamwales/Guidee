from dataclasses import dataclass
from typing import Annotated

import httpx
from fastapi import Depends, HTTPException, Request, status
from jose import JWTError, jwt

from app.core.config import Settings, get_settings

JWKS_CACHE: dict | None = None


@dataclass
class AuthUser:
    clerk_id: str
    email: str | None = None
    plan: str = "free"


async def _fetch_jwks(settings: Settings) -> dict:
    global JWKS_CACHE
    if JWKS_CACHE is not None:
        return JWKS_CACHE
    if not settings.clerk_jwks_url:
        JWKS_CACHE = {"keys": []}
        return JWKS_CACHE
    async with httpx.AsyncClient() as client:
        resp = await client.get(settings.clerk_jwks_url, timeout=10.0)
        resp.raise_for_status()
        JWKS_CACHE = resp.json()
    return JWKS_CACHE


def _decode_token(token: str, settings: Settings, jwks: dict) -> dict:
    if not settings.clerk_secret_key and not settings.clerk_jwks_url:
        # Development: accept opaque dev tokens
        if token.startswith("dev:"):
            return {"sub": token[4:], "email": "dev@guidee.local"}
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Auth not configured")

    if settings.clerk_jwks_url and jwks.get("keys"):
        try:
            return jwt.decode(
                token,
                jwks,
                algorithms=["RS256"],
                options={"verify_aud": False},
            )
        except JWTError as e:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token") from e

    try:
        return jwt.decode(token, settings.clerk_secret_key, algorithms=["HS256"])
    except JWTError as e:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token") from e


async def get_current_user(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
) -> AuthUser:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing bearer token")
    token = auth[7:].strip()
    jwks = await _fetch_jwks(settings)
    payload = _decode_token(token, settings, jwks)
    clerk_id = payload.get("sub") or payload.get("user_id")
    if not clerk_id:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token payload")
    return AuthUser(
        clerk_id=str(clerk_id),
        email=payload.get("email"),
        plan=payload.get("plan", "free"),
    )


async def optional_user(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
) -> AuthUser | None:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    try:
        return await get_current_user(request, settings)
    except HTTPException:
        return None
