import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

SERVICE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICE_ROOT))


def load_module(name: str, relative_path: str):
    spec = importlib.util.spec_from_file_location(name, SERVICE_ROOT / relative_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {relative_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


browser_tool = load_module(
    "guidee_browser_tool",
    "tools/browser.py",
)
dom_agent = load_module("guidee_dom_agent", "nodes/dom_agent.py")
instruction_agent = load_module(
    "guidee_instruction_agent",
    "nodes/instruction_agent.py",
)
action_agent = load_module("guidee_action_agent", "nodes/action_agent.py")


class BrowserAgentTests(unittest.IsolatedAsyncioTestCase):
    def test_extract_interactive_elements_prefers_stable_selectors(self):
        html = """
        <button data-testid="save">Save</button>
        <input name="email" placeholder="Email" />
        <a href="/docs">Docs</a>
        """

        elements = dom_agent.extract_interactive_elements(html)

        self.assertEqual(elements[0]["selector"], "[data-testid='save']")
        self.assertEqual(elements[1]["selector"], "input[name='email']")
        self.assertEqual(elements[2]["selector"], "a[href='/docs']")

    def test_sensitive_actions_require_confirmation(self):
        self.assertTrue(
            browser_tool.requires_confirmation(
                {"type": "click", "purpose": "delete account"}
            )
        )
        self.assertFalse(
            browser_tool.requires_confirmation(
                {"type": "click", "purpose": "delete account", "confirmed": True}
            )
        )

    def test_instruction_normalizes_supported_actions_and_adds_screenshot(self):
        actions = instruction_agent.normalize_actions(
            [
                {"type": "click", "selector": "#save"},
                {"type": "unknown", "selector": "#bad"},
            ],
            "click save",
            {},
        )

        self.assertEqual(actions[0]["type"], "click")
        self.assertEqual(actions[-1]["type"], "screenshot")
        self.assertEqual(len(actions), 2)

    async def test_action_agent_blocks_sensitive_unconfirmed_actions(self):
        result = await action_agent.run(
            {
                "action_plan": [
                    {
                        "type": "click",
                        "selector": "#delete",
                        "requires_confirmation": True,
                    }
                ],
                "tool_results": [],
            }
        )

        self.assertEqual(result["status"], "failed")
        self.assertIn("confirmation", result["progress_message"])

    async def test_action_agent_reperceives_after_screenshot(self):
        with (
            patch.object(
                action_agent,
                "execute_action",
                new=AsyncMock(return_value={"screenshot_b64": "abc"}),
            ),
            patch.object(
                action_agent.vision_agent,
                "run",
                new=AsyncMock(return_value={"vision_context": {"page_type": "home"}}),
            ),
        ):
            result = await action_agent.run(
                {"action_plan": [{"type": "screenshot"}], "tool_results": []}
            )

        self.assertEqual(result["status"], "done")
        self.assertEqual(result["result"], "Browser task completed")
        self.assertNotIn(
            "screenshot_b64",
            result["tool_results"][0]["result"],
        )


if __name__ == "__main__":
    unittest.main()
