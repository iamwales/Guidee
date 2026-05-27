from tools.browser import browse_url
from tools.code_exec import run_code
from tools.email import draft_email, send_email
from tools.filesystem import (
    edit_file,
    list_directory,
    read_file,
    summarize_file,
    write_file,
)
from tools.web_search import fetch_url, web_search

TOOL_REGISTRY = {
    "web_search": web_search,
    "browse_url": browse_url,
    "read_file": read_file,
    "write_file": write_file,
    "edit_file": edit_file,
    "list_directory": list_directory,
    "summarize_file": summarize_file,
    "send_email": send_email,
    "draft_email": draft_email,
    "run_code": run_code,
    "fetch_url": fetch_url,
}


async def dispatch_tool(name: str, inputs: dict) -> dict:
    fn = TOOL_REGISTRY.get(name)
    if not fn:
        return {"error": f"Unknown tool: {name}"}
    return await fn(**inputs)
