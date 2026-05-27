import importlib.util
import sys
import unittest
from pathlib import Path

SERVICE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICE_ROOT))

spec = importlib.util.spec_from_file_location(
    "guidee_agent_supervisor",
    SERVICE_ROOT / "supervisor.py",
)
if spec is None or spec.loader is None:
    raise RuntimeError("Unable to load supervisor module")
supervisor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(supervisor)

worker_spec = importlib.util.spec_from_file_location(
    "guidee_agent_worker",
    SERVICE_ROOT / "worker.py",
)
if worker_spec is None or worker_spec.loader is None:
    raise RuntimeError("Unable to load worker module")
worker = importlib.util.module_from_spec(worker_spec)
worker_spec.loader.exec_module(worker)


class FakeGraph:
    async def astream(self, state, stream_mode):
        self.stream_mode = stream_mode
        yield {"planner": {**state, "progress_message": "Planned", "step": 0}}
        yield {
            "summarizer": {
                **state,
                "status": "done",
                "result": "Finished",
                "progress_message": "Task complete",
            }
        }


class FakeRedis:
    def __init__(self):
        self.published = []
        self.hashes = {}

    async def publish(self, channel, data):
        self.published.append((channel, data))

    async def hset(self, key, mapping=None, *args):
        self.hashes.setdefault(key, {})
        if mapping:
            self.hashes[key].update(mapping)
        elif len(args) == 2:
            self.hashes[key][args[0]] = args[1]


class RuntimeTests(unittest.IsolatedAsyncioTestCase):
    async def test_run_agent_streams_node_progress(self):
        original_graphs = dict(supervisor.ROUTE_GRAPHS)
        supervisor.ROUTE_GRAPHS["research"] = FakeGraph()
        events = []

        async def on_progress(event):
            events.append(event)

        try:
            result = await supervisor.run_agent(
                "research",
                {"task": "find docs", "route": "research"},
                on_progress=on_progress,
                timeout_seconds=5,
                retry_attempts=0,
            )
        finally:
            supervisor.ROUTE_GRAPHS.clear()
            supervisor.ROUTE_GRAPHS.update(original_graphs)

        self.assertEqual(result["result"], "Finished")
        self.assertEqual([event["node"] for event in events], ["planner", "summarizer"])
        self.assertEqual(events[-1]["status"], "done")

    async def test_run_agent_returns_cancelled_state_between_nodes(self):
        original_graphs = dict(supervisor.ROUTE_GRAPHS)
        supervisor.ROUTE_GRAPHS["research"] = FakeGraph()
        calls = 0

        async def is_cancelled():
            nonlocal calls
            calls += 1
            return calls > 1

        try:
            result = await supervisor.run_agent(
                "research",
                {"task": "find docs", "route": "research"},
                is_cancelled=is_cancelled,
                timeout_seconds=5,
                retry_attempts=0,
            )
        finally:
            supervisor.ROUTE_GRAPHS.clear()
            supervisor.ROUTE_GRAPHS.update(original_graphs)

        self.assertEqual(result["status"], "cancelled")

    async def test_publish_normalizes_progress_fields(self):
        redis = FakeRedis()

        await worker.publish(
            redis,
            "task-1",
            {"type": "progress", "step": 2, "total_steps": 4},
        )

        payload = redis.hashes["guidee:task:task-1"]
        self.assertEqual(payload["steps_done"], "2")
        self.assertEqual(payload["steps_total"], "4")


if __name__ == "__main__":
    unittest.main()
