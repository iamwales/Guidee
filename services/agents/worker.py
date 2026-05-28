"""
Redis queue worker — pulls agent tasks and runs LangGraph graphs.
"""

# ruff: noqa: E402

import asyncio
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any

# Ensure services/agents is on path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import redis.asyncio as redis
from config import get_settings
from supervisor import run_agent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("guidee.worker")

TASK_QUEUE = "guidee:agent:queue"
TASK_PREFIX = "guidee:task:"
TASK_CHANNEL_PREFIX = "task:"
WORKER_HEALTH_KEY = "guidee:worker:health"
SENSITIVE_EVENT_KEYS = {"screenshot_b64", "image_b64", "audio", "token", "secret"}


def sanitize_event(event: dict[str, Any]) -> dict[str, Any]:
    clean: dict[str, Any] = {}
    for key, value in event.items():
        if any(sensitive in key.lower() for sensitive in SENSITIVE_EVENT_KEYS):
            clean[key] = "[redacted]"
        elif isinstance(value, dict):
            clean[key] = sanitize_event(value)
        elif isinstance(value, list):
            clean[key] = [
                sanitize_event(item) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            clean[key] = value
    return clean


def configure_tracing(settings: Any) -> None:
    if not settings.langsmith_api_key:
        return
    os.environ.setdefault("LANGSMITH_TRACING", "true")
    os.environ.setdefault("LANGSMITH_API_KEY", settings.langsmith_api_key)
    os.environ.setdefault("LANGSMITH_PROJECT", settings.langsmith_project)


async def publish(r: Any, task_id: str, event: dict) -> None:
    event = sanitize_event(event)
    event["task_id"] = task_id
    if "total_steps" in event and "steps_total" not in event:
        event["steps_total"] = event["total_steps"]
    if "step" in event and "steps_done" not in event:
        event["steps_done"] = event["step"]
    await r.publish(f"{TASK_CHANNEL_PREFIX}{task_id}", json.dumps(event))
    await r.hset(
        f"{TASK_PREFIX}{task_id}",
        mapping={k: str(v) for k, v in event.items() if v is not None},
    )


async def is_cancelled(r: Any, task_id: str) -> bool:
    return await r.hget(f"{TASK_PREFIX}{task_id}", "status") == "cancelled"


async def heartbeat_loop(r: Any, settings: Any) -> None:
    interval = max(5, int(settings.worker_health_interval_seconds))
    while True:
        try:
            await r.hset(
                WORKER_HEALTH_KEY,
                mapping={
                    "status": "ok",
                    "updated_at": str(int(time.time())),
                    "concurrency": str(settings.worker_concurrency),
                },
            )
            await r.expire(WORKER_HEALTH_KEY, interval * 3)
        except redis.RedisError:
            logger.exception("Worker heartbeat failed")
        await asyncio.sleep(interval)


async def process_task(r: Any, payload: dict) -> None:
    task_id = payload["task_id"]
    route = payload["route"]
    task = payload["task"]
    user_id = payload.get("user_id", "")
    screenshot = payload.get("screenshot_b64")
    screenshot_media_type = payload.get("screenshot_media_type") or "image/jpeg"
    screenshot_metadata = payload.get("screenshot_metadata")

    await publish(
        r,
        task_id,
        {
            "type": "progress",
            "status": "running",
            "message": f"Starting {route} agent",
            "step": 0,
            "total_steps": 5,
        },
    )
    await r.hset(f"{TASK_PREFIX}{task_id}", "status", "running")

    initial_state = {
        "task": task,
        "route": route,
        "task_id": task_id,
        "user_id": user_id,
        "screenshot_b64": screenshot,
        "screenshot_media_type": screenshot_media_type,
        "screenshot_metadata": screenshot_metadata,
        "tool_results": [],
        "messages": [],
        "step": 0,
        "status": "pending",
    }

    try:
        settings = get_settings()

        async def progress(event: dict) -> None:
            await publish(r, task_id, event)

        result = await run_agent(
            route,
            initial_state,
            on_progress=progress,
            is_cancelled=lambda: is_cancelled(r, task_id),
            timeout_seconds=settings.agent_task_timeout_seconds,
            retry_attempts=settings.agent_node_retry_attempts,
        )
        if result.get("status") == "cancelled" or await is_cancelled(r, task_id):
            await publish(
                r,
                task_id,
                {
                    "type": "cancelled",
                    "status": "cancelled",
                    "message": "Task cancelled",
                },
            )
            return
        final = result.get("result", "Task completed")
        await r.hset(
            f"{TASK_PREFIX}{task_id}",
            mapping={
                "status": "done",
                "result": final,
                "steps_done": str(result.get("step", 0)),
            },
        )
        await publish(
            r,
            task_id,
            {
                "type": "done",
                "status": "done",
                "message": result.get("progress_message", "Done"),
                "result": final,
            },
        )
    except Exception as e:
        logger.exception("Task %s failed", task_id)
        await r.hset(
            f"{TASK_PREFIX}{task_id}",
            mapping={"status": "failed", "error": str(e)},
        )
        await publish(
            r,
            task_id,
            {"type": "error", "status": "failed", "message": str(e)},
        )


async def worker_task(r: Any, payload: dict, semaphore: asyncio.Semaphore) -> None:
    async with semaphore:
        await process_task(r, payload)


async def worker_loop() -> None:
    settings = get_settings()
    configure_tracing(settings)
    r: Any = redis.from_url(settings.redis_url, decode_responses=True)
    semaphore = asyncio.Semaphore(max(1, settings.worker_concurrency))
    background: set[asyncio.Task] = {
        asyncio.create_task(heartbeat_loop(r, settings)),
    }
    logger.info(
        "Worker listening on %s with concurrency=%s",
        TASK_QUEUE,
        settings.worker_concurrency,
    )

    while True:
        try:
            done = {task for task in background if task.done()}
            for task in done:
                background.remove(task)
                task.result()
            item = await r.brpop(TASK_QUEUE, timeout=5)
            if not item:
                continue
            _, raw = item
            payload = json.loads(raw)
            task_id = payload.get("task_id")
            current = await r.hget(f"{TASK_PREFIX}{task_id}", "status")
            if current == "cancelled":
                continue
            background.add(asyncio.create_task(worker_task(r, payload, semaphore)))
        except redis.RedisError as e:
            logger.error("Redis error: %s", e)
            await asyncio.sleep(2)
        except Exception as e:
            logger.exception("Worker error: %s", e)
            await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(worker_loop())
