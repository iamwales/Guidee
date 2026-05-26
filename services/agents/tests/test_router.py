import importlib.util
import sys
import unittest
from pathlib import Path

SERVICE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICE_ROOT))

spec = importlib.util.spec_from_file_location(
    "guidee_agent_router",
    SERVICE_ROOT / "nodes" / "router.py",
)
if spec is None or spec.loader is None:
    raise RuntimeError("Unable to load router module")
router = importlib.util.module_from_spec(spec)
spec.loader.exec_module(router)


class RouterTests(unittest.TestCase):
    def test_failed_state_routes_to_error(self):
        self.assertEqual(router.should_continue({"status": "failed"}), "error")

    def test_incomplete_plan_continues(self):
        state = {"status": "running", "plan": ["first", "second"], "step": 1}

        self.assertEqual(router.should_continue(state), "continue")

    def test_completed_plan_summarizes(self):
        state = {"status": "running", "plan": ["first"], "step": 1}

        self.assertEqual(router.should_continue(state), "summarize")


if __name__ == "__main__":
    unittest.main()
