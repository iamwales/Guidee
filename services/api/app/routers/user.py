from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.security import AuthUser, get_current_user

router = APIRouter(prefix="/user", tags=["user"])


@router.get("/history")
async def get_history(user: Annotated[AuthUser, Depends(get_current_user)]):
    """Conversation history — backed by Supabase when configured."""
    _ = user
    return {"conversations": []}
