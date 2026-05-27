import json
import uuid
from collections.abc import AsyncIterator
from typing import Any

import redis.asyncio as redis

from app.core.config import Settings
from app.services.history import HistoryStore

TASK_QUEUE = "guidee:agent:queue"
TASK_PREFIX = "guidee:task:"
TASK_CHANNEL_PREFIX = "task:"


class TaskStore:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._redis: Any = None

    async def connect(self) -> Any:
        if self._redis is None:
            self._redis = redis.from_url(self.settings.redis_url, decode_responses=True)
        return self._redis

    async def create_task(
        self,
        user_id: str,
        task_input: str,
        route: str,
        screenshot_b64: str | None = None,
        screenshot_media_type: str | None = None,
        screenshot_metadata: dict[str, Any] | None = None,
    ) -> str:
        r = await self.connect()
        task_id = str(uuid.uuid4())
        payload = {
            "task_id": task_id,
            "user_id": user_id,
            "task": task_input,
            "route": route,
            "screenshot_b64": screenshot_b64,
            "screenshot_media_type": screenshot_media_type,
            "screenshot_metadata": screenshot_metadata,
            "status": "pending",
        }
        await r.hset(
            f"{TASK_PREFIX}{task_id}",
            mapping={
                "task_id": task_id,
                "user_id": user_id,
                "task_input": task_input,
                "route": route,
                "status": "pending",
                "steps_done": "0",
            },
        )
        await r.lpush(TASK_QUEUE, json.dumps(payload))
        await HistoryStore(self.settings).record_task_created(
            task_id=task_id,
            user_id=user_id,
            task_input=task_input,
            route=route,
            screenshot_metadata=screenshot_metadata,
        )
        return task_id

    async def get_task(self, task_id: str) -> dict[str, str] | None:
        r = await self.connect()
        data = await r.hgetall(f"{TASK_PREFIX}{task_id}")
        if not data:
            return None
        if data.get("status") in {"done", "failed", "cancelled"}:
            await HistoryStore(self.settings).record_task_update(
                task_id=task_id,
                user_id=data.get("user_id"),
                status=data.get("status"),
                result=data.get("result"),
                error=data.get("error"),
            )
        return data

    async def update_task(self, task_id: str, **fields: Any) -> None:
        r = await self.connect()
        await r.hset(
            f"{TASK_PREFIX}{task_id}",
            mapping={k: str(v) for k, v in fields.items()},
        )
        status = str(fields["status"]) if "status" in fields else None
        result = str(fields["result"]) if "result" in fields else None
        error = str(fields["error"]) if "error" in fields else None
        if status or result or error:
            await HistoryStore(self.settings).record_task_update(
                task_id=task_id,
                user_id=str(fields["user_id"]) if "user_id" in fields else None,
                status=status,
                result=result,
                error=error,
            )

    async def cancel_task(self, task_id: str) -> bool:
        task = await self.get_task(task_id)
        if not task:
            return False
        if task.get("status") in ("done", "failed", "cancelled"):
            return False
        await self.update_task(task_id, status="cancelled", cancelled="true")
        await self.publish_progress(
            task_id,
            {"type": "cancelled", "status": "cancelled", "message": "Task cancelled"},
        )
        return True

    async def publish_progress(self, task_id: str, event: dict) -> None:
        r = await self.connect()
        event["task_id"] = task_id
        await r.publish(f"{TASK_CHANNEL_PREFIX}{task_id}", json.dumps(event))

    async def subscribe_progress(self, task_id: str) -> AsyncIterator[dict]:
        r = await self.connect()
        pubsub = r.pubsub()
        await pubsub.subscribe(f"{TASK_CHANNEL_PREFIX}{task_id}")
        try:
            async for message in pubsub.listen():
                if message["type"] != "message":
                    continue
                yield json.loads(message["data"])
        finally:
            await pubsub.unsubscribe(f"{TASK_CHANNEL_PREFIX}{task_id}")
            await pubsub.aclose()
