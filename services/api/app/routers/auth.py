from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from jose import jwt

from app.core.config import Settings, get_settings
from app.core.security import AuthUser, get_current_user
from app.models.schemas import AuthTokenRequest, AuthTokenResponse, UserMeResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/token", response_model=AuthTokenResponse)
async def exchange_token(
    body: AuthTokenRequest,
    settings: Annotated[Settings, Depends(get_settings)],
) -> AuthTokenResponse:
    """Exchange Clerk session JWT for API bearer (dev: pass-through)."""
    if not body.clerk_token:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Missing clerk_token")

    if settings.clerk_secret_key:
        try:
            payload = jwt.decode(
                body.clerk_token,
                settings.clerk_secret_key,
                algorithms=["HS256"],
            )
            sub = payload.get("sub", "unknown")
        except Exception:
            access = body.clerk_token
            return AuthTokenResponse(access_token=access)
        access = jwt.encode(
            {"sub": sub, "email": payload.get("email")},
            settings.clerk_secret_key,
            algorithm="HS256",
        )
        return AuthTokenResponse(access_token=access)

    return AuthTokenResponse(access_token=body.clerk_token)


@router.get("/me", response_model=UserMeResponse)
async def get_me(user: Annotated[AuthUser, Depends(get_current_user)]) -> UserMeResponse:
    return UserMeResponse(
        clerk_id=user.clerk_id,
        email=user.email,
        plan=user.plan,
    )
