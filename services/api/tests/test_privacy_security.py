import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.privacy import redact_mapping


class PrivacySecurityTests(unittest.TestCase):
    def test_redacts_sensitive_keys_recursively(self):
        data = {
            "authorization": "Bearer secret",
            "metadata": {
                "screenshot_b64": "abc123",
                "safe": "ok",
            },
            "items": [{"refresh_token": "token"}],
        }

        result = redact_mapping(data)

        self.assertEqual(result["authorization"], "[redacted]")
        self.assertEqual(result["metadata"]["screenshot_b64"], "[redacted]")
        self.assertEqual(result["metadata"]["safe"], "ok")
        self.assertEqual(result["items"][0]["refresh_token"], "[redacted]")

    def test_truncates_large_strings_without_redacting_safe_keys(self):
        result = redact_mapping({"message": "x" * 300})

        self.assertIn("[truncated:300]", result["message"])


if __name__ == "__main__":
    unittest.main()
