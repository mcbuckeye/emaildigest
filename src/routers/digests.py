"""Digest endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from croniter import croniter
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.database import get_db
from src.models import (
    Digest,
    DigestDelivery,
    DigestSource,
    DigestStatus,
    User,
)
from src.routers.auth import get_current_user
from src.tasks.pipeline import generate_digest_task

router = APIRouter(prefix="/api", tags=["digests"])


class SourceIn(BaseModel):
    source_type: str = Field(pattern="^(rss|url)$")
    url: str = Field(min_length=1, max_length=1000)


class DigestCreateIn(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    frequency_cron: str = Field(default="0 9 * * *")
    recipient_email: EmailStr
    sources: list[SourceIn] = Field(default_factory=list)

    @field_validator("frequency_cron")
    @classmethod
    def _check_cron(cls, value: str) -> str:
        if not croniter.is_valid(value):
            raise ValueError("invalid cron expression")
        return value


class DigestUpdateIn(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    frequency_cron: str | None = None
    recipient_email: EmailStr | None = None

    @field_validator("frequency_cron")
    @classmethod
    def _check_cron(cls, value: str | None) -> str | None:
        if value is None:
            return value
        if not croniter.is_valid(value):
            raise ValueError("invalid cron expression")
        return value


class SourceOut(BaseModel):
    id: int
    source_type: str
    url: str


class DigestOut(BaseModel):
    id: int
    name: str
    description: str | None
    frequency_cron: str
    status: str
    recipient_email: str
    next_run_at: datetime | None
    last_run_at: datetime | None
    sources: list[SourceOut]
    created_at: datetime
    updated_at: datetime


def _serialize(digest: Digest) -> DigestOut:
    return DigestOut(
        id=digest.id,
        name=digest.name,
        description=digest.description,
        frequency_cron=digest.frequency_cron,
        status=digest.status,
        recipient_email=digest.recipient_email,
        next_run_at=digest.next_run_at,
        last_run_at=digest.last_run_at,
        sources=[SourceOut(id=s.id, source_type=s.source_type, url=s.url) for s in (digest.sources or [])],
        created_at=digest.created_at,
        updated_at=digest.updated_at,
    )


async def _load_owned(
    digest_id: int, user: User, db: AsyncSession, *, load_sources: bool = True
) -> Digest:
    stmt = select(Digest).where(Digest.id == digest_id, Digest.owner_id == user.id)
    if load_sources:
        stmt = stmt.options(selectinload(Digest.sources))
    digest = (await db.execute(stmt)).scalar_one_or_none()
    if digest is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Digest not found")
    return digest


@router.get("/digests", response_model=list[DigestOut])
async def list_digests(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    stmt = (
        select(Digest)
        .where(Digest.owner_id == current_user.id)
        .options(selectinload(Digest.sources))
        .order_by(Digest.created_at.desc())
    )
    rows = (await db.execute(stmt)).scalars().all()
    return [_serialize(d) for d in rows]


@router.post("/digests", status_code=status.HTTP_201_CREATED, response_model=DigestOut)
async def create_digest(
    payload: DigestCreateIn,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    from src.tasks.scheduler import compute_next_run_at

    digest = Digest(
        owner_id=current_user.id,
        name=payload.name,
        description=payload.description,
        frequency_cron=payload.frequency_cron,
        status=DigestStatus.ACTIVE.value,
        recipient_email=payload.recipient_email,
    )
    import contextlib

    with contextlib.suppress(ValueError):
        digest.next_run_at = compute_next_run_at(payload.frequency_cron).replace(tzinfo=None)
    for source in payload.sources:
        digest.sources.append(DigestSource(source_type=source.source_type, url=source.url))
    db.add(digest)
    await db.commit()
    await db.refresh(digest, attribute_names=["sources"])
    return _serialize(digest)


@router.get("/digests/{digest_id}", response_model=DigestOut)
async def get_digest(
    digest_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    digest = await _load_owned(digest_id, current_user, db)
    return _serialize(digest)


@router.patch("/digests/{digest_id}", response_model=DigestOut)
async def update_digest(
    digest_id: int,
    payload: DigestUpdateIn,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    digest = await _load_owned(digest_id, current_user, db)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(digest, field, value)
    await db.commit()
    await db.refresh(digest, attribute_names=["sources"])
    return _serialize(digest)


@router.delete("/digests/{digest_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_digest(
    digest_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    digest = await _load_owned(digest_id, current_user, db, load_sources=False)
    await db.delete(digest)
    await db.commit()


@router.post("/digests/{digest_id}/pause")
async def pause_digest(
    digest_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    digest = await _load_owned(digest_id, current_user, db, load_sources=False)
    digest.status = DigestStatus.PAUSED.value
    await db.commit()
    return {"id": digest.id, "status": digest.status}


@router.post("/digests/{digest_id}/resume")
async def resume_digest(
    digest_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    digest = await _load_owned(digest_id, current_user, db, load_sources=False)
    digest.status = DigestStatus.ACTIVE.value
    await db.commit()
    return {"id": digest.id, "status": digest.status}


@router.post("/digests/{digest_id}/resend", status_code=status.HTTP_202_ACCEPTED)
async def resend_digest(
    digest_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    digest = await _load_owned(digest_id, current_user, db, load_sources=False)
    generate_digest_task.delay(digest.id)
    return {"status": "queued", "digest_id": digest.id}


class DeliveryOut(BaseModel):
    id: int
    digest_id: int
    scheduled_at: datetime
    sent_at: datetime | None
    status: str
    subject: str | None
    error_message: str | None
    item_count: int


@router.get("/digests/{digest_id}/deliveries", response_model=list[DeliveryOut])
async def list_deliveries(
    digest_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = 20,
    offset: int = 0,
):
    await _load_owned(digest_id, current_user, db, load_sources=False)

    stmt = (
        select(DigestDelivery)
        .where(DigestDelivery.digest_id == digest_id)
        .options(selectinload(DigestDelivery.items))
        .order_by(DigestDelivery.scheduled_at.desc())
        .offset(offset)
        .limit(min(limit, 100))
    )
    rows = (await db.execute(stmt)).scalars().all()
    return [
        DeliveryOut(
            id=d.id,
            digest_id=d.digest_id,
            scheduled_at=d.scheduled_at,
            sent_at=d.sent_at,
            status=d.status,
            subject=d.subject,
            error_message=d.error_message,
            item_count=len(d.items),
        )
        for d in rows
    ]


@router.get("/deliveries/{delivery_id}/preview", response_class=HTMLResponse)
async def preview_delivery(
    delivery_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    stmt = (
        select(DigestDelivery)
        .join(Digest, Digest.id == DigestDelivery.digest_id)
        .where(DigestDelivery.id == delivery_id, Digest.owner_id == current_user.id)
    )
    delivery = (await db.execute(stmt)).scalar_one_or_none()
    if delivery is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Delivery not found")
    if not delivery.html_body:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No preview available")
    return HTMLResponse(content=delivery.html_body)
