from typing import Any, cast

from supabase import Client, create_client

from app.core.config import Settings


class HistoryStore:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._client: Client | None = None

    @property
    def configured(self) -> bool:
        return bool(self.settings.supabase_url and self.settings.supabase_key)

    @property
    def client(self) -> Client:
        if self._client is None:
            self._client = create_client(
                self.settings.supabase_url,
                self.settings.supabase_key,
            )
        return self._client

    async def record_task_created(
        self,
        *,
        task_id: str,
        user_id: str,
        task_input: str,
        route: str,
        screenshot_metadata: dict[str, Any] | None = None,
    ) -> None:
        if not self.configured:
            return
        self.client.table("guidee_task_history").upsert(
            {
                "task_id": task_id,
                "user_id": user_id,
                "task_input": task_input,
                "route": route,
                "status": "pending",
                "screenshot_metadata": screenshot_metadata,
            }
        ).execute()

    async def record_task_update(
        self,
        *,
        task_id: str,
        user_id: str | None = None,
        status: str | None = None,
        result: str | None = None,
        error: str | None = None,
    ) -> None:
        if not self.configured:
            return
        payload: dict[str, Any] = {"task_id": task_id}
        if user_id is not None:
            payload["user_id"] = user_id
        if status is not None:
            payload["status"] = status
        if result is not None:
            payload["result"] = result
        if error is not None:
            payload["error"] = error
        self.client.table("guidee_task_history").upsert(payload).execute()

    async def list_tasks(self, user_id: str, limit: int = 50) -> list[dict[str, Any]]:
        if not self.configured:
            return []
        response = (
            self.client.table("guidee_task_history")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return cast(list[dict[str, Any]], response.data or [])

    async def get_profile(self, user_id: str) -> dict[str, Any] | None:
        if not self.configured:
            return None
        response = (
            self.client.table("guidee_user_profiles")
            .select("*")
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        rows = cast(list[dict[str, Any]], response.data or [])
        return dict(rows[0]) if rows else None

    async def upsert_profile(
        self,
        *,
        user_id: str,
        email: str | None,
        plan: str,
    ) -> dict[str, Any] | None:
        if not self.configured:
            return None
        response = (
            self.client.table("guidee_user_profiles")
            .upsert({"user_id": user_id, "email": email, "plan": plan})
            .execute()
        )
        rows = cast(list[dict[str, Any]], response.data or [])
        return dict(rows[0]) if rows else None
