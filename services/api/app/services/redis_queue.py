import json
import uuid
from collections.abc import AsyncIterator
from typing import Any

import redis.asyncio as redis

from app.core.config import Settings

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
    ) -> str:
        r = await self.connect()
        task_id = str(uuid.uuid4())
        payload = {
            "task_id": task_id,
            "user_id": user_id,
            "task": task_input,
            "route": route,
            "screenshot_b64": screenshot_b64,
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
        return task_id

    async def get_task(self, task_id: str) -> dict[str, str] | None:
        r = await self.connect()
        data = await r.hgetall(f"{TASK_PREFIX}{task_id}")
        return data or None

    async def update_task(self, task_id: str, **fields: Any) -> None:
        r = await self.connect()
        await r.hset(
            f"{TASK_PREFIX}{task_id}",
            mapping={k: str(v) for k, v in fields.items()},
        )

    async def cancel_task(self, task_id: str) -> bool:
        task = await self.get_task(task_id)
        if not task:
            return False
        if task.get("status") in ("done", "failed", "cancelled"):
            return False
        await self.update_task(task_id, status="cancelled")
        await self.publish_progress(
            task_id,
            {"type": "error", "message": "Task cancelled"},
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
