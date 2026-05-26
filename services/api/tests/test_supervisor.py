import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.supervisor import classify_request, detect_intent_prefix


class FakeClaudeService:
    def __init__(self, response: str):
        self.response = response

    async def complete(self, *args, **kwargs) -> str:
        return self.response


class SupervisorTests(unittest.IsolatedAsyncioTestCase):
    def test_detects_legacy_agent_prefix(self):
        self.assertEqual(
            detect_intent_prefix("Guidee agent, research this market"),
            ("agent", "research this market"),
        )

    def test_ignores_non_agent_prefix(self):
        self.assertIsNone(detect_intent_prefix("Guidee, answer this quickly"))

    async def test_classify_request_parses_valid_route_json(self):
        payload = {
            "route": "browser",
            "reasoning": "User asked to use a website",
            "task": "Open the docs",
        }
        result = await classify_request(
            FakeClaudeService(json.dumps(payload)),
            "open the docs",
            None,
        )

        self.assertEqual(result.route, "browser")
        self.assertEqual(result.reasoning, "User asked to use a website")
        self.assertEqual(result.task, "Open the docs")

    async def test_classify_request_falls_back_for_invalid_json(self):
        result = await classify_request(FakeClaudeService("not json"), "hello", None)

        self.assertEqual(result.route, "instant")
        self.assertEqual(result.reasoning, "Fallback to instant")

    async def test_classify_request_rejects_unknown_routes(self):
        result = await classify_request(
            FakeClaudeService('{"route": "calendar", "reasoning": "bad route"}'),
            "schedule this",
            None,
        )

        self.assertEqual(result.route, "instant")


if __name__ == "__main__":
    unittest.main()
