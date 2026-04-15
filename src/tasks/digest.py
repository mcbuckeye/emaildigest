"""Digest generation tasks."""

import asyncio
import logging
from datetime import datetime
from typing import Any

import aiosmtplib
from celery import shared_task
from jinja2 import Environment, FileSystemLoader

from src.config import config
from src.database import db_session
from src.models.digest import Digest, DigestDelivery, DigestItem, DeliveryStatus

logger = logging.getLogger(__name__)


async def fetch_rss_feed(url: str) -> list[dict[str, Any]]:
    """Fetch items from an RSS feed."""
    import feedparser

    feed = feedparser.parse(url)
    items = []
    for entry in feed.entries:
        items.append({
            "title": entry.get("title", "Untitled"),
            "link": entry.get("link", ""),
            "published": datetime.fromtimestamp(
                entry.get("published_parsed", datetime.now()).timestamp()
            ),
            "summary": entry.get("summary", ""),
            "source_url": url,
        })
    return items


async def fetch_webpage(url: str) -> list[dict[str, Any]]:
    """Basic webpage scraper - extracts links and titles."""
    import aiohttp
    from bs4 import BeautifulSoup

    async with aiohttp.ClientSession() as session:
        async with session.get(url, timeout=10) as resp:
            html = await resp.text()
            soup = BeautifulSoup(html, "html.parser")

            items = []
            for tag in soup.find_all(["a"]):
                link = tag.get("href")
                if link and (link.startswith("http") or link.startswith("/")):
                    items.append({
                        "title": tag.get_text(strip=True),
                        "link": link,
                        "source_url": url,
                    })
            return items


async def generate_digest_email(digest: Digest, items: list[dict]) -> tuple[str, str]:
    """Generate HTML email content for a digest."""
    env = Environment(loader=FileSystemLoader("src/templates"))
    template = env.get_template("digest_email.html")

    html_body = template.render(
        digest=digest,
        items=items[:20],  # Limit to 20 items
        current_date=datetime.utcnow(),
    )

    plain_text = f"""{digest.name}

{digest.description or ""}

{'=' * 50}

"""
    for item in items[:20]:
        plain_text += f"{item['title']}: {item.get('link', item.get('source_url'))}\n\n"
        plain_text += f"Summary: {item.get('summary', 'No summary available')}\n\n"
        plain_text += "-" * 50 + "\n"

    return html_body, plain_text


async def send_email(html_body: str, plain_text: str, to_email: str):
    """Send email using smtp2go."""
    await aiosmtplib.send(
        f"From: {config().smtp2go_from_name} <{config().smtp2go_from_email}>\n"
        f"To: {to_email}\n"
        f"Subject: {config().app_name}: {datetime.utcnow().strftime('%Y-%m-%d')}\n"
        f"MIME-Version: 1.0\n"
        f"Content-Type: multipart/alternative; boundary=\"----mime-boundary\"\n\n"
        f"------mime-boundary\n"
        f"Content-Type: text/plain; charset=\"utf-8\"\n\n{plain_text}\n"
        f"------mime-boundary\n"
        f"Content-Type: text/html; charset=\"utf-8\"\n\n{html_body}\n"
        f"------mime-boundary--\n",
        hostname="smtp.smtp2go.com",
        port=2525,
        username=config().smtp2go_api_key,
        password="",
    )


@shared_task
def generate_digest_task(digest_id: int):
    """Generate and send a digest."""
    async def run_task():
        async with db_session() as session:
            # Get digest
            digest = await session.get(Digest, digest_id)
            if not digest:
                logger.error(f"Digest {digest_id} not found")
                return

            # Check if digest is active
            if digest.status != "active":
                logger.info(f"Digest {digest_id} is not active, skipping")
                return

            # Create delivery record
            delivery = DigestDelivery(digest_id=digest_id, status="pending")
            session.add(delivery)
            await session.commit()
            await session.refresh(delivery)

            logger.info(f"Generating delivery {delivery.id} for digest {digest_id}")

            try:
                # Fetch items from all sources
                all_items = []
                for source in digest.sources:
                    if source.source_type == "rss":
                        items = await fetch_rss_feed(source.url)
                    else:
                        items = await fetch_webpage(source.url)
                    all_items.extend(items)

                if not all_items:
                    logger.warning(f"No items found for digest {digest_id}")
                    delivery.status = DeliveryStatus.FAILED
                    delivery.error_message = "No items found"
                    await session.commit()
                    return

                # Generate email
                html_body, plain_text = await generate_digest_email(digest, all_items)

                # Send email
                await send_email(html_body, plain_text, digest.recipient_email)

                # Save items
                for item in all_items:
                    digest_item = DigestItem(
                        delivery_id=delivery.id,
                        source_url=item.get("source_url", ""),
                        title=item.get("title", ""),
                        summary=item.get("summary", ""),
                        url=item.get("link", ""),
                        published_at=item.get("published"),
                    )
                    session.add(digest_item)

                delivery.status = DeliveryStatus.SENT
                delivery.sent_at = datetime.utcnow()
                await session.commit()

                logger.info(f"Delivery {delivery.id} sent successfully")

            except Exception as e:
                logger.error(f"Error generating delivery {delivery.id}: {e}")
                delivery.status = DeliveryStatus.FAILED
                delivery.error_message = str(e)
                await session.commit()

    asyncio.run(run_task())
