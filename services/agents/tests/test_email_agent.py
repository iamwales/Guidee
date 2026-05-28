import importlib.util
import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

SERVICE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICE_ROOT))

spec = importlib.util.spec_from_file_location(
    "guidee_email_tool",
    SERVICE_ROOT / "tools" / "email.py",
)
if spec is None or spec.loader is None:
    raise RuntimeError("Unable to load email tool")
email_tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(email_tool)


class EmailSettings:
    def __init__(self, root: Path):
        self.gmail_client_id = "client-id"
        self.gmail_client_secret = "client-secret"
        self.gmail_redirect_uri = "http://localhost/callback"
        self.gmail_token_path = str(root / "tokens.json")
        self.email_audit_log_path = str(root / "audit.jsonl")
        self.file_agent_allowed_roots = str(root)
        self.file_agent_max_read_bytes = 5_000_000


class EmailAgentTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.settings = EmailSettings(self.root)
        self.settings_patch = patch.object(
            email_tool,
            "get_settings",
            return_value=self.settings,
        )
        self.settings_patch.start()

    def tearDown(self):
        self.settings_patch.stop()
        self.tmp.cleanup()

    def test_validate_recipients_accepts_lists_and_rejects_bad_addresses(self):
        result = email_tool.validate_recipients(
            ["a@example.com", "bad"],
            cc="team@example.com",
        )

        self.assertFalse(result["valid"])
        self.assertIn("bad", result["invalid"])
        self.assertIn("team@example.com", result["recipients"])

    async def test_send_email_requires_confirmation_before_gmail_call(self):
        with patch.object(email_tool, "gmail_request", new=AsyncMock()) as request:
            result = await email_tool.send_email(
                "a@example.com",
                "Hello",
                "Body",
                confirmed=False,
            )

        self.assertEqual(result["error"], "confirmation_required")
        request.assert_not_called()
        self.assertTrue(Path(self.settings.email_audit_log_path).exists())

    async def test_draft_email_creates_gmail_draft_and_audit_record(self):
        response = {
            "id": "draft-1",
            "message": {"id": "msg-1", "threadId": "thread-1"},
        }

        with patch.object(
            email_tool,
            "gmail_request",
            new=AsyncMock(return_value=response),
        ) as request:
            result = await email_tool.draft_email(
                "a@example.com",
                "Hello",
                "Body",
            )

        self.assertTrue(result["draft"])
        self.assertEqual(result["draft_id"], "draft-1")
        request.assert_awaited_once()
        audit = Path(self.settings.email_audit_log_path).read_text(encoding="utf-8")
        self.assertIn("draft_email", audit)

    async def test_send_email_uses_draft_id_when_confirmed(self):
        response = {"id": "msg-1", "threadId": "thread-1"}
        with patch.object(
            email_tool,
            "gmail_request",
            new=AsyncMock(return_value=response),
        ) as request:
            result = await email_tool.send_email(
                "a@example.com",
                "Hello",
                "Body",
                confirmed=True,
                draft_id="draft-1",
            )

        self.assertTrue(result["sent"])
        request.assert_awaited_once_with(
            "POST",
            "/drafts/send",
            json_body={"id": "draft-1"},
        )

    def test_build_message_attaches_sandboxed_file(self):
        attachment = self.root / "report.txt"
        attachment.write_text("hello", encoding="utf-8")

        with patch.dict(
            email_tool.safe_path.__globals__,
            {"get_settings": lambda: self.settings},
        ):
            result = email_tool.build_message(
                "a@example.com",
                "Hello",
                "Body",
                attachments=[str(attachment)],
            )

        self.assertNotIn("error", result)
        self.assertEqual(result["attachment_count"], 1)

    def test_store_gmail_tokens_writes_private_file_with_expiry(self):
        email_tool.store_gmail_tokens({"access_token": "abc", "expires_in": 60})

        path = Path(self.settings.gmail_token_path)
        data = json.loads(path.read_text(encoding="utf-8"))
        mode = os.stat(path).st_mode & 0o777

        self.assertEqual(mode, 0o600)
        self.assertGreater(data["expires_at"], time.time())


if __name__ == "__main__":
    unittest.main()
