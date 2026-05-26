_playwright = None
_browser = None
_page = None


async def _ensure_browser():
    global _playwright, _browser, _page
    if _page is not None:
        return _page
    from playwright.async_api import async_playwright

    _playwright = await async_playwright().start()
    _browser = await _playwright.chromium.launch(headless=True)
    _page = await _browser.new_page()
    return _page


async def browse_url(url: str) -> dict:
    page = await _ensure_browser()
    await page.goto(url, timeout=15000, wait_until="domcontentloaded")
    content = await page.inner_text("body")
    return {"url": url, "content": content[:8000]}


async def get_page_html(url: str | None = None) -> dict:
    page = await _ensure_browser()
    if url:
        await page.goto(url, timeout=15000, wait_until="domcontentloaded")
    html = await page.content()
    return {"html": html[:50000]}


async def execute_action(action: dict) -> dict:
    """Execute a single UI action from the action plan."""
    page = await _ensure_browser()
    action_type = action.get("type")
    selector = action.get("selector")
    value = action.get("value")

    try:
        if action_type == "click" and selector:
            await page.click(selector, timeout=5000)
        elif action_type == "fill" and selector:
            await page.fill(selector, value or "")
        elif action_type == "goto" and value:
            await page.goto(value, timeout=15000)
        elif action_type == "screenshot":
            import base64

            buf = await page.screenshot(type="jpeg", quality=75)
            return {"screenshot_b64": base64.b64encode(buf).decode()}
        else:
            return {"error": f"Unknown action type: {action_type}"}
        return {"success": True, "action": action_type}
    except Exception as e:
        return {"error": str(e), "action": action}
