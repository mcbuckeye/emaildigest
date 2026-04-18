"""Render digest emails."""

from __future__ import annotations

from datetime import datetime
from email.message import EmailMessage
from typing import Any

import bleach
from jinja2 import Environment, FileSystemLoader, select_autoescape

from src.config import config
from src.models import Digest

ALLOWED_TAGS = {
    "a",
    "abbr",
    "b",
    "blockquote",
    "br",
    "code",
    "em",
    "h1",
    "h2",
    "h3",
    "h4",
    "i",
    "li",
    "ol",
    "p",
    "pre",
    "strong",
    "ul",
    "span",
    "img",
}
ALLOWED_ATTRS = {
    "a": ["href", "title", "rel"],
    "img": ["src", "alt", "title"],
    "span": ["class"],
}


def sanitize_html(value: str | None) -> str:
    if not value:
        return ""
    return bleach.clean(value, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRS, strip=True)


def _jinja_env() -> Environment:
    env = Environment(
        loader=FileSystemLoader("src/templates"),
        autoescape=select_autoescape(["html", "xml"]),
    )
    env.filters["sanitize"] = sanitize_html
    return env


def render_digest_html(digest: Digest, items: list[dict[str, Any]]) -> tuple[str, str]:
    env = _jinja_env()
    template = env.get_template("digest_email.html")
    html_body = template.render(
        digest=digest,
        items=items[:50],
        current_date=datetime.utcnow(),
        app_name=config().app_name,
    )

    plain_lines = [digest.name]
    if digest.description:
        plain_lines.append(digest.description)
    plain_lines.append("")
    for item in items[:50]:
        plain_lines.append(f"- {item.get('title', '(no title)')}: {item.get('url', '')}")
        if item.get("summary"):
            plain_lines.append(f"  {_strip_html(item['summary'])[:300]}")
    plain_body = "\n".join(plain_lines)

    return html_body, plain_body


def _strip_html(value: str) -> str:
    return bleach.clean(value, tags=[], strip=True)


def build_email_message(
    digest: Digest,
    items: list[dict[str, Any]],
    to_email: str,
) -> EmailMessage:
    settings = config()
    subject = f"{digest.name} — {datetime.utcnow().strftime('%Y-%m-%d')}"
    html_body, plain_body = render_digest_html(digest, items)

    msg = EmailMessage()
    msg["From"] = f"{settings.smtp2go_from_name} <{settings.smtp2go_from_email}>"
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(plain_body)
    msg.add_alternative(html_body, subtype="html")
    return msg
