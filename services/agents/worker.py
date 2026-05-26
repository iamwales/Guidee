"""
Redis queue worker — pulls agent tasks and runs LangGraph graphs.
"""

# ruff: noqa: E402

import asyncio
import json
import logging
import sys
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


async def publish(r: Any, task_id: str, event: dict) -> None:
    event["task_id"] = task_id
    await r.publish(f"{TASK_CHANNEL_PREFIX}{task_id}", json.dumps(event))
    await r.hset(
        f"{TASK_PREFIX}{task_id}",
        mapping={k: str(v) for k, v in event.items() if v is not None},
    )


async def process_task(r: Any, payload: dict) -> None:
    task_id = payload["task_id"]
    route = payload["route"]
    task = payload["task"]
    user_id = payload.get("user_id", "")
    screenshot = payload.get("screenshot_b64")

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
        "tool_results": [],
        "messages": [],
        "step": 0,
        "status": "pending",
    }

    try:
        result = await run_agent(route, initial_state)
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


async def worker_loop() -> None:
    settings = get_settings()
    r: Any = redis.from_url(settings.redis_url, decode_responses=True)
    logger.info("Worker listening on %s", TASK_QUEUE)

    while True:
        try:
            item = await r.brpop(TASK_QUEUE, timeout=5)
            if not item:
                continue
            _, raw = item
            payload = json.loads(raw)
            task_id = payload.get("task_id")
            current = await r.hget(f"{TASK_PREFIX}{task_id}", "status")
            if current == "cancelled":
                continue
            await process_task(r, payload)
        except redis.RedisError as e:
            logger.error("Redis error: %s", e)
            await asyncio.sleep(2)
        except Exception as e:
            logger.exception("Worker error: %s", e)
            await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(worker_loop())
