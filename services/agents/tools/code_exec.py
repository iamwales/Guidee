from agents.config import get_settings


async def run_code(code: str) -> dict:
    settings = get_settings()
    if not settings.e2b_api_key:
        return {
            "stdout": "",
            "stderr": "",
            "error": "Configure E2B_API_KEY for sandboxed code execution",
            "dev_note": "Would execute via e2b.dev sandbox",
        }

    try:
        from e2b_code_interpreter import Sandbox

        with Sandbox(api_key=settings.e2b_api_key) as sandbox:
            execution = sandbox.run_code(code)
            return {
                "stdout": execution.logs.stdout if execution.logs else "",
                "stderr": execution.logs.stderr if execution.logs else "",
                "error": str(execution.error) if execution.error else None,
            }
    except ImportError:
        return {"error": "Install e2b-code-interpreter for code execution"}
