_playwright = None
_browser = None
_page = None

SENSITIVE_KEYWORDS = {
    "buy",
    "checkout",
    "delete",
    "remove",
    "pay",
    "purchase",
    "send",
    "submit payment",
    "transfer",
}


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


async def get_page_snapshot(url: str | None = None) -> dict:
    page = await _ensure_browser()
    if url:
        await page.goto(url, timeout=15000, wait_until="domcontentloaded")
    html = await page.content()
    title = await page.title()
    text = await page.inner_text("body")
    return {
        "url": page.url,
        "title": title,
        "html": html[:50000],
        "text": text[:12000],
    }


async def get_page_html(url: str | None = None) -> dict:
    snapshot = await get_page_snapshot(url)
    return {
        "html": snapshot["html"],
        "url": snapshot["url"],
        "title": snapshot["title"],
    }


def requires_confirmation(action: dict) -> bool:
    if action.get("confirmed") is True:
        return False
    text = " ".join(
        str(action.get(key, ""))
        for key in ("type", "selector", "value", "purpose", "label")
    ).lower()
    return any(keyword in text for keyword in SENSITIVE_KEYWORDS)


async def execute_action(action: dict) -> dict:
    """Execute a single UI action from the action plan."""
    page = await _ensure_browser()
    action_type = action.get("type")
    selector = action.get("selector")
    value = action.get("value")

    try:
        if requires_confirmation(action):
            return {
                "error": "confirmation_required",
                "message": "Sensitive browser action requires user confirmation",
                "action": action,
            }
        if action_type == "click" and selector:
            await page.click(selector, timeout=5000)
        elif action_type == "fill" and selector:
            await page.fill(selector, value or "")
        elif action_type == "press" and selector and value:
            await page.press(selector, value, timeout=5000)
        elif action_type == "select" and selector:
            await page.select_option(selector, value or "")
        elif action_type == "wait":
            await page.wait_for_timeout(int(value or 1000))
        elif action_type == "goto" and value:
            await page.goto(value, timeout=15000)
        elif action_type == "screenshot":
            import base64

            buf = await page.screenshot(type="jpeg", quality=75)
            return {"screenshot_b64": base64.b64encode(buf).decode()}
        elif action_type == "extract_dom":
            return await get_page_snapshot()
        else:
            return {"error": f"Unknown action type: {action_type}"}
        return {"success": True, "action": action_type}
    except Exception as e:
        return {"error": str(e), "action": action}


async def close_browser() -> None:
    global _playwright, _browser, _page
    if _browser is not None:
        await _browser.close()
    if _playwright is not None:
        await _playwright.stop()
    _page = None
    _browser = None
    _playwright = None
