"""Open-pixel + click-through tracking endpoints (public)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse, Response
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.models import DigestDelivery, DigestItem

router = APIRouter(prefix="/api/track", tags=["tracking"])

# 1x1 transparent GIF
_PIXEL = (
    b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\x00\x00\x00!\xf9\x04\x01"
    b"\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
)


@router.get("/open/{token}.gif")
async def open_pixel(
    token: str,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    stmt = (
        update(DigestDelivery)
        .where(DigestDelivery.tracking_token == token)
        .values(open_count=DigestDelivery.open_count + 1)
    )
    await db.execute(stmt)
    await db.commit()
    return Response(content=_PIXEL, media_type="image/gif")


@router.get("/click/{token}/{item_id}")
async def click_redirect(
    token: str,
    item_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    delivery = (
        await db.execute(select(DigestDelivery).where(DigestDelivery.tracking_token == token))
    ).scalar_one_or_none()
    item = await db.get(DigestItem, item_id)
    if delivery is None or item is None or item.delivery_id != delivery.id:
        return RedirectResponse(url="/", status_code=307)

    delivery.click_count += 1
    item.click_count += 1
    await db.commit()
    return RedirectResponse(url=item.url, status_code=307)
