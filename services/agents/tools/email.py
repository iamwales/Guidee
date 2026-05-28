import base64
import json
import os
import re
import time
from email.message import EmailMessage
from email.utils import make_msgid
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import httpx
from config import get_settings

from tools.filesystem import safe_path

GMAIL_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GMAIL_TOKEN_URL = "https://oauth2.googleapis.com/token"
GMAIL_API_BASE = "https://gmail.googleapis.com/gmail/v1/users/me"
GMAIL_SCOPES = (
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/gmail.send",
)
EMAIL_RE = (
    r"^[A-Z0-9.!#$%&'*+/=?^_`{|}~-]+@"
    r"[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?"
    r"(?:\.[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?)+$"
)


def get_gmail_oauth_url(state: str = "guidee") -> dict:
    settings = get_settings()
    if not settings.gmail_client_id:
        return {"error": "GMAIL_CLIENT_ID is not configured"}

    query = urlencode(
        {
            "client_id": settings.gmail_client_id,
            "redirect_uri": settings.gmail_redirect_uri,
            "response_type": "code",
            "scope": " ".join(GMAIL_SCOPES),
            "access_type": "offline",
            "prompt": "consent",
            "state": state,
        }
    )
    return {"url": f"{GMAIL_AUTH_URL}?{query}", "scopes": list(GMAIL_SCOPES)}


async def exchange_gmail_oauth_code(code: str) -> dict:
    settings = get_settings()
    if not settings.gmail_client_id or not settings.gmail_client_secret:
        return {"error": "Gmail OAuth client credentials are not configured"}

    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(
            GMAIL_TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.gmail_client_id,
                "client_secret": settings.gmail_client_secret,
                "redirect_uri": settings.gmail_redirect_uri,
                "grant_type": "authorization_code",
            },
        )
        response.raise_for_status()

    token = response.json()
    store_gmail_tokens(token)
    audit_email_event(
        "oauth_token_stored",
        {"has_refresh_token": bool(token.get("refresh_token"))},
    )
    return {
        "stored": True,
        "scope": token.get("scope"),
        "expires_in": token.get("expires_in"),
    }


def validate_recipients(to: str | list[str], cc: str | list[str] | None = None) -> dict:
    recipients = normalize_recipients(to) + normalize_recipients(cc)
    invalid = [address for address in recipients if not is_valid_email(address)]
    return {"valid": not invalid, "recipients": recipients, "invalid": invalid}


async def draft_email(
    to: str | list[str],
    subject: str,
    body: str,
    cc: str | list[str] | None = None,
    bcc: str | list[str] | None = None,
    attachments: list[str] | None = None,
    thread_id: str | None = None,
    in_reply_to: str | None = None,
) -> dict:
    validation = validate_recipients(to, cc)
    if not validation["valid"]:
        return {"error": "invalid_recipients", **validation}

    message = build_message(
        to=to,
        subject=subject,
        body=body,
        cc=cc,
        bcc=bcc,
        attachments=attachments,
        thread_id=thread_id,
        in_reply_to=in_reply_to,
    )
    if message.get("error"):
        return message

    payload: dict[str, Any] = {"message": {"raw": message["raw"]}}
    if thread_id:
        payload["message"]["threadId"] = thread_id

    response = await gmail_request("POST", "/drafts", json_body=payload)
    event = {
        "to": validation["recipients"],
        "subject": subject,
        "thread_id": thread_id,
        "draft_id": response.get("id"),
        "status": "created" if not response.get("error") else "failed",
    }
    audit_email_event("draft_email", event)
    if response.get("error"):
        return response

    return {
        "draft": True,
        "draft_id": response.get("id"),
        "message_id": response.get("message", {}).get("id"),
        "thread_id": response.get("message", {}).get("threadId") or thread_id,
        "to": validation["recipients"],
        "subject": subject,
    }


async def send_email(
    to: str | list[str],
    subject: str,
    body: str,
    confirmed: bool = False,
    cc: str | list[str] | None = None,
    bcc: str | list[str] | None = None,
    attachments: list[str] | None = None,
    thread_id: str | None = None,
    in_reply_to: str | None = None,
    draft_id: str | None = None,
) -> dict:
    validation = validate_recipients(to, cc)
    if not validation["valid"]:
        return {"error": "invalid_recipients", **validation}
    if not confirmed:
        audit_email_event(
            "send_email_confirmation_required",
            {"to": validation["recipients"], "subject": subject, "draft_id": draft_id},
        )
        return {
            "error": "confirmation_required",
            "message": "Sending email requires user confirmation",
            "to": validation["recipients"],
            "subject": subject,
            "preview": body[:1000],
            "draft_id": draft_id,
        }

    if draft_id:
        response = await gmail_request(
            "POST",
            "/drafts/send",
            json_body={"id": draft_id},
        )
    else:
        message = build_message(
            to=to,
            subject=subject,
            body=body,
            cc=cc,
            bcc=bcc,
            attachments=attachments,
            thread_id=thread_id,
            in_reply_to=in_reply_to,
        )
        if message.get("error"):
            return message
        payload: dict[str, Any] = {"raw": message["raw"]}
        if thread_id:
            payload["threadId"] = thread_id
        response = await gmail_request("POST", "/messages/send", json_body=payload)

    event = {
        "to": validation["recipients"],
        "subject": subject,
        "draft_id": draft_id,
        "thread_id": response.get("threadId") or thread_id,
        "message_id": response.get("id"),
        "status": "sent" if not response.get("error") else "failed",
    }
    audit_email_event("send_email", event)
    if response.get("error"):
        return response

    return {
        "sent": True,
        "message_id": response.get("id"),
        "thread_id": response.get("threadId") or thread_id,
        "to": validation["recipients"],
        "subject": subject,
    }


async def reply_email(
    thread_id: str,
    to: str | list[str],
    subject: str,
    body: str,
    confirmed: bool = False,
    in_reply_to: str | None = None,
    attachments: list[str] | None = None,
) -> dict:
    return await send_email(
        to=to,
        subject=subject if subject.lower().startswith("re:") else f"Re: {subject}",
        body=body,
        confirmed=confirmed,
        attachments=attachments,
        thread_id=thread_id,
        in_reply_to=in_reply_to,
    )


def build_message(
    to: str | list[str],
    subject: str,
    body: str,
    cc: str | list[str] | None = None,
    bcc: str | list[str] | None = None,
    attachments: list[str] | None = None,
    thread_id: str | None = None,
    in_reply_to: str | None = None,
) -> dict:
    validation = validate_recipients(to, cc)
    bcc_validation = validate_recipients(bcc or [])
    if not validation["valid"] or not bcc_validation["valid"]:
        return {
            "error": "invalid_recipients",
            "invalid": validation["invalid"] + bcc_validation["invalid"],
        }

    message = EmailMessage()
    message["To"] = ", ".join(normalize_recipients(to))
    if cc:
        message["Cc"] = ", ".join(normalize_recipients(cc))
    if bcc:
        message["Bcc"] = ", ".join(normalize_recipients(bcc))
    message["Subject"] = subject
    message["Message-ID"] = make_msgid(domain="guidee.local")
    if thread_id:
        message["X-Guidee-Thread-ID"] = thread_id
    if in_reply_to:
        message["In-Reply-To"] = in_reply_to
        message["References"] = in_reply_to
    message.set_content(body)

    for attachment_path in attachments or []:
        attachment = load_attachment(attachment_path)
        if attachment.get("error"):
            return attachment
        message.add_attachment(
            attachment["data"],
            maintype=attachment["maintype"],
            subtype=attachment["subtype"],
            filename=attachment["filename"],
        )

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode("ascii")
    return {
        "raw": raw,
        "thread_id": thread_id,
        "attachment_count": len(attachments or []),
    }


def load_attachment(path: str) -> dict:
    try:
        resolved = safe_path(path)
    except PermissionError as exc:
        return {"error": str(exc), "path": path}
    if not resolved.exists() or not resolved.is_file():
        return {"error": "Attachment not found", "path": str(resolved)}
    data = resolved.read_bytes()
    if len(data) > 10_000_000:
        return {"error": "Attachment exceeds 10MB limit", "path": str(resolved)}
    maintype, subtype = content_type_for(resolved)
    return {
        "filename": resolved.name,
        "data": data,
        "maintype": maintype,
        "subtype": subtype,
    }


async def gmail_request(
    method: str,
    path: str,
    json_body: dict | None = None,
) -> dict:
    token = await get_valid_token()
    if token.get("error"):
        return token

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.request(
            method,
            f"{GMAIL_API_BASE}{path}",
            headers={"Authorization": f"Bearer {token['access_token']}"},
            json=json_body,
        )
    if response.status_code >= 400:
        return {
            "error": "gmail_api_error",
            "status": response.status_code,
            "body": response.text,
        }
    return response.json()


async def get_valid_token() -> dict:
    token = load_gmail_tokens()
    if token.get("error"):
        return token
    expires_at = float(token.get("expires_at", 0))
    if token.get("access_token") and expires_at > time.time() + 60:
        return token
    if not token.get("refresh_token"):
        return {"error": "gmail_token_expired", "message": "Reconnect Gmail OAuth"}
    return await refresh_gmail_token(token)


async def refresh_gmail_token(token: dict) -> dict:
    settings = get_settings()
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(
            GMAIL_TOKEN_URL,
            data={
                "client_id": settings.gmail_client_id,
                "client_secret": settings.gmail_client_secret,
                "refresh_token": token["refresh_token"],
                "grant_type": "refresh_token",
            },
        )
        response.raise_for_status()
    refreshed = {**token, **response.json()}
    store_gmail_tokens(refreshed)
    return refreshed


def store_gmail_tokens(token: dict) -> None:
    token = dict(token)
    if token.get("expires_in"):
        token["expires_at"] = time.time() + int(token["expires_in"])
    path = secure_path(get_settings().gmail_token_path)
    path.write_text(json.dumps(token), encoding="utf-8")
    os.chmod(path, 0o600)


def load_gmail_tokens() -> dict:
    path = Path(get_settings().gmail_token_path).expanduser()
    if not path.exists():
        return {"error": "gmail_not_connected", "message": "Connect Gmail OAuth first"}
    return json.loads(path.read_text(encoding="utf-8"))


def audit_email_event(event: str, payload: dict) -> None:
    path = secure_path(get_settings().email_audit_log_path)
    record = {"ts": int(time.time()), "event": event, **payload}
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")
    os.chmod(path, 0o600)


def secure_path(raw: str) -> Path:
    path = Path(raw).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(path.parent, 0o700)
    return path


def normalize_recipients(value: str | list[str] | None) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        items = value.replace(";", ",").split(",")
    else:
        items = value
    return [item.strip() for item in items if item and item.strip()]


def is_valid_email(address: str) -> bool:
    return bool(re.match(EMAIL_RE, address, re.IGNORECASE))


def content_type_for(path: Path) -> tuple[str, str]:
    ext = path.suffix.lower()
    if ext in {".txt", ".md", ".csv", ".json"}:
        return ("text", "plain")
    if ext in {".jpg", ".jpeg"}:
        return ("image", "jpeg")
    if ext == ".png":
        return ("image", "png")
    if ext == ".pdf":
        return ("application", "pdf")
    return ("application", "octet-stream")
