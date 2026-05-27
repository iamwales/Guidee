import json
import sys
import unittest
from base64 import b64encode
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.claude import build_messages
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

    def test_build_messages_attaches_valid_jpeg_screenshot(self):
        screenshot = b64encode(b"jpeg bytes").decode()
        messages = build_messages("what is this?", screenshot, [])

        content = messages[-1]["content"]
        self.assertEqual(content[0]["type"], "image")
        self.assertEqual(content[0]["source"]["media_type"], "image/jpeg")
        self.assertEqual(content[0]["source"]["data"], screenshot)
        self.assertEqual(content[1], {"type": "text", "text": "what is this?"})

    def test_build_messages_strips_data_url_prefix(self):
        screenshot = b64encode(b"jpeg bytes").decode()
        messages = build_messages(
            "what is this?",
            f"data:image/jpeg;base64,{screenshot}",
            [],
        )

        self.assertEqual(messages[-1]["content"][0]["source"]["data"], screenshot)


if __name__ == "__main__":
    unittest.main()
