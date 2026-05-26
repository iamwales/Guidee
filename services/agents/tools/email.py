async def draft_email(to: str, subject: str, body: str) -> dict:
    return {
        "draft": True,
        "to": to,
        "subject": subject,
        "body": body,
        "message": "Draft ready — configure Gmail API for sending",
    }


async def send_email(to: str, subject: str, body: str) -> dict:
    # Production: Gmail API / SMTP via OAuth
    return {
        "sent": False,
        "to": to,
        "subject": subject,
        "message": "Email sending requires Gmail OAuth configuration",
    }
