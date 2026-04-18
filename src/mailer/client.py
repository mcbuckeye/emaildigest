"""Email sending client."""

from __future__ import annotations

import logging
from email.message import EmailMessage

import aiosmtplib

from src.config import config

logger = logging.getLogger(__name__)


async def send_email_message(message: EmailMessage) -> None:
    """Send an EmailMessage via smtp2go."""
    settings = config()
    if not settings.smtp2go_api_key:
        logger.warning("SMTP2GO_API_KEY not set; skipping real send")
        return
    await aiosmtplib.send(
        message,
        hostname=settings.smtp2go_host,
        port=settings.smtp2go_port,
        username=settings.smtp2go_api_key,
        password=settings.smtp2go_api_key,
        start_tls=True,
    )


async def send_password_reset_email(to_email: str, token: str) -> None:
    """Send a password reset link."""
    settings = config()
    reset_url = f"{settings.app_base_url.rstrip('/')}/reset-password?token={token}"

    msg = EmailMessage()
    msg["From"] = f"{settings.smtp2go_from_name} <{settings.smtp2go_from_email}>"
    msg["To"] = to_email
    msg["Subject"] = f"{settings.app_name}: reset your password"
    msg.set_content(
        "Someone requested a password reset for this account.\n\n"
        f"Reset link (valid for {settings.password_reset_token_expire_minutes} minutes):\n"
        f"{reset_url}\n\n"
        "If this wasn't you, you can ignore this email."
    )
    msg.add_alternative(
        f"""
        <html><body>
          <p>Someone requested a password reset for this account.</p>
          <p><a href="{reset_url}">Reset your password</a>
             (valid for {settings.password_reset_token_expire_minutes} minutes)</p>
          <p>If this wasn't you, ignore this email.</p>
        </body></html>
        """,
        subtype="html",
    )

    await send_email_message(msg)
