from tools.web_search import web_search
from tools.browser import browse_url, get_page_html, execute_action
from tools.filesystem import read_file, write_file, list_directory
from tools.email import send_email, draft_email
from tools.code_exec import run_code

TOOL_REGISTRY = {
    "web_search": web_search,
    "browse_url": browse_url,
    "read_file": read_file,
    "write_file": write_file,
    "list_directory": list_directory,
    "send_email": send_email,
    "draft_email": draft_email,
    "run_code": run_code,
}


async def dispatch_tool(name: str, inputs: dict) -> dict:
    fn = TOOL_REGISTRY.get(name)
    if not fn:
        return {"error": f"Unknown tool: {name}"}
    return await fn(**inputs)
