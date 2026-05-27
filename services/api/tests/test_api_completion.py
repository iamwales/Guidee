import sys
import unittest
from pathlib import Path

from fastapi.testclient import TestClient
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import Settings
from app.core.rate_limit import limit_for_plan
from app.main import create_app
from app.models.schemas import AgentDispatchRequest, ScreenshotMetadata


class ApiCompletionTests(unittest.TestCase):
    def test_plan_limits_use_billing_tier(self):
        settings = Settings()

        self.assertEqual(
            limit_for_plan("free", "/chat/stream", settings, settings.rate_limit_chat),
            settings.rate_limit_chat,
        )
        self.assertEqual(
            limit_for_plan("pro", "/chat/stream", settings, settings.rate_limit_chat),
            settings.rate_limit_chat_pro,
        )
        self.assertEqual(
            limit_for_plan(
                "team",
                "/agent/dispatch",
                settings,
                settings.rate_limit_agent,
            ),
            settings.rate_limit_agent_team,
        )

    def test_screenshot_metadata_is_validated(self):
        with self.assertRaises(ValidationError):
            ScreenshotMetadata(
                source="selectedMonitor",
                width=0,
                height=100,
                original_width=100,
                original_height=100,
                quality=75,
                byte_size=1000,
            )

    def test_dispatch_request_trims_empty_screenshot(self):
        request = AgentDispatchRequest(task="open docs", screenshot_b64="  ")

        self.assertIsNone(request.screenshot_b64)

    def test_structured_validation_errors_include_error_envelope(self):
        client = TestClient(create_app())
        response = client.post(
            "/chat/supervisor",
            json={},
            headers={"Authorization": "Bearer dev:test-user"},
        )

        self.assertEqual(response.status_code, 422)
        body = response.json()
        self.assertEqual(body["error"]["code"], "validation_error")
        self.assertEqual(body["error"]["message"], "Invalid request payload")
        self.assertIn("request_id", body["error"])


if __name__ == "__main__":
    unittest.main()
