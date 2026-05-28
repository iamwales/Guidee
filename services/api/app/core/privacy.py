from collections.abc import Mapping
from typing import Any

SENSITIVE_KEYS = {
    "access_token",
    "api_key",
    "authorization",
    "clerk_token",
    "client_secret",
    "code",
    "image_b64",
    "password",
    "picovoice_access_key",
    "refresh_token",
    "screenshot_b64",
    "secret",
    "stripe_signature",
    "token",
}


def redact_value(key: str, value: Any) -> Any:
    normalized = key.lower()
    if any(sensitive in normalized for sensitive in SENSITIVE_KEYS):
        return "[redacted]"
    if isinstance(value, str) and len(value) > 256:
        return f"{value[:64]}...[truncated:{len(value)}]"
    return value


def redact_mapping(data: Mapping[str, Any]) -> dict[str, Any]:
    redacted: dict[str, Any] = {}
    for key, value in data.items():
        if isinstance(value, Mapping):
            redacted[key] = redact_mapping(value)
        elif isinstance(value, list):
            redacted[key] = [
                redact_mapping(item) if isinstance(item, Mapping) else item
                for item in value
            ]
        else:
            redacted[key] = redact_value(key, value)
    return redacted
