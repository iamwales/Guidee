import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

SERVICE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICE_ROOT))

tools_spec = importlib.util.spec_from_file_location(
    "guidee_web_search",
    SERVICE_ROOT / "tools" / "web_search.py",
)
if tools_spec is None or tools_spec.loader is None:
    raise RuntimeError("Unable to load web_search module")
web_search_module = importlib.util.module_from_spec(tools_spec)
tools_spec.loader.exec_module(web_search_module)

research_spec = importlib.util.spec_from_file_location(
    "guidee_research_node",
    SERVICE_ROOT / "nodes" / "research.py",
)
if research_spec is None or research_spec.loader is None:
    raise RuntimeError("Unable to load research node module")
research = importlib.util.module_from_spec(research_spec)
research_spec.loader.exec_module(research)


class FakeResponse:
    def __init__(
        self,
        json_data=None,
        text="",
        headers=None,
        status_code=200,
        url="https://example.com",
    ):
        self._json_data = json_data or {}
        self.text = text
        self.headers = headers or {}
        self.status_code = status_code
        self.url = url

    def json(self):
        return self._json_data

    def raise_for_status(self):
        return None


class FakeClient:
    def __init__(self, response):
        self.response = response

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def get(self, *args, **kwargs):
        return self.response


class ResearchTests(unittest.IsolatedAsyncioTestCase):
    async def test_web_search_parses_brave_results(self):
        response = FakeResponse(
            json_data={
                "web": {
                    "results": [
                        {
                            "title": "Guidee",
                            "url": "https://example.com/guidee",
                            "description": "Desktop assistant",
                            "age": "1 day ago",
                        }
                    ]
                }
            }
        )

        with (
            patch.object(
                web_search_module,
                "get_settings",
                return_value=type("Settings", (), {"brave_search_api_key": "key"})(),
            ),
            patch.object(
                web_search_module.httpx,
                "AsyncClient",
                return_value=FakeClient(response),
            ),
        ):
            result = await web_search_module.web_search("guidee")

        self.assertEqual(result["source"], "brave")
        self.assertEqual(result["results"][0]["title"], "Guidee")
        self.assertEqual(result["results"][0]["url"], "https://example.com/guidee")

    async def test_fetch_url_extracts_html_text(self):
        response = FakeResponse(
            text="<html><script>bad()</script><body><h1>Hello</h1><p>World</p></body></html>",
            headers={"content-type": "text/html"},
        )

        with patch.object(
            web_search_module.httpx,
            "AsyncClient",
            return_value=FakeClient(response),
        ):
            result = await web_search_module.fetch_url("https://example.com")

        self.assertIn("Hello World", result["text"])
        self.assertNotIn("bad()", result["text"])

    async def test_research_synthesis_falls_back_without_llm(self):
        state = {
            "task": "Research Guidee",
            "sources": [
                {
                    "id": 1,
                    "title": "Guidee",
                    "url": "https://example.com",
                    "snippet": "Snippet",
                    "text": "Guidee is a desktop assistant.",
                }
            ],
        }

        with patch.object(research, "complete_text", new=AsyncMock(return_value="")):
            result = await research.synthesize(state)

        self.assertEqual(result["status"], "done")
        self.assertIn("[1] Guidee", result["result"])
        self.assertEqual(result["citations"][0]["url"], "https://example.com")


if __name__ == "__main__":
    unittest.main()
