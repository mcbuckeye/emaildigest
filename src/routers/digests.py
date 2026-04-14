"""Digest endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from src.database import db_session
from src.models.digest import Digest, DigestStatus
from src.models.user import User
from src.routers.auth import get_current_user


router = APIRouter(prefix="/api/digests", tags=["digests"])


@router.get("/", response_model=list[dict])
async def list_digests(current_user: User = Depends(get_current_user)):
    """List all digests for the current user."""
    async with db_session() as session:
        results = await session.execute(
            Digest.select().where(Digest.owner_id == current_user.id)
        )
        digests = results.scalars().all()
        return [
            {
                "id": d.id,
                "name": d.name,
                "description": d.description,
                "frequency_cron": d.frequency_cron,
                "status": d.status,
                "recipient_email": d.recipient_email,
                "created_at": d.created_at,
                "updated_at": d.updated_at,
            }
            for d in digests
        ]


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_digest(
    data: dict,
    current_user: User = Depends(get_current_user),
):
    """Create a new digest."""
    name = data.get("name")
    description = data.get("description")
    frequency_cron = data.get("frequency_cron", "0 9 * * *")
    recipient_email = data.get("recipient_email")
    source_type = data.get("source_type", "rss")
    source_url = data.get("source_url")

    if not name or not recipient_email or not source_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="name, recipient_email, and source_url are required",
        )

    async with db_session() as session:
        digest = Digest(
            owner_id=current_user.id,
            name=name,
            description=description,
            frequency_cron=frequency_cron,
            status=DigestStatus.ACTIVE,
            recipient_email=recipient_email,
        )
        session.add(digest)
        await session.commit()
        await session.refresh(digest)

        return {
            "id": digest.id,
            "name": digest.name,
            "description": digest.description,
            "frequency_cron": digest.frequency_cron,
            "status": digest.status,
            "recipient_email": digest.recipient_email,
            "created_at": digest.created_at,
            "updated_at": digest.updated_at,
        }


@router.get("/{digest_id}")
async def get_digest(digest_id: int, current_user: User = Depends(get_current_user)):
    """Get a specific digest."""
    async with db_session() as session:
        digest = await session.get(Digest, digest_id)
        if digest is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Digest not found",
            )
        if digest.owner_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )
        return {
            "id": digest.id,
            "name": digest.name,
            "description": digest.description,
            "frequency_cron": digest.frequency_cron,
            "status": digest.status,
            "recipient_email": digest.recipient_email,
            "created_at": digest.created_at,
            "updated_at": digest.updated_at,
        }


@router.patch("/{digest_id}")
async def update_digest(
    digest_id: int,
    data: dict,
    current_user: User = Depends(get_current_user),
):
    """Update a digest."""
    async with db_session() as session:
        digest = await session.get(Digest, digest_id)
        if digest is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Digest not found",
            )
        if digest.owner_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )

        for field in ["name", "description", "frequency_cron", "recipient_email"]:
            if field in data:
                setattr(digest, field, data[field])

        await session.commit()
        await session.refresh(digest)

        return {
            "id": digest.id,
            "name": digest.name,
            "description": digest.description,
            "frequency_cron": digest.frequency_cron,
            "status": digest.status,
            "recipient_email": digest.recipient_email,
            "created_at": digest.created_at,
            "updated_at": digest.updated_at,
        }


@router.delete("/{digest_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_digest(digest_id: int, current_user: User = Depends(get_current_user)):
    """Delete a digest."""
    async with db_session() as session:
        digest = await session.get(Digest, digest_id)
        if digest is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Digest not found",
            )
        if digest.owner_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )

        await session.delete(digest)
        await session.commit()


@router.post("/{digest_id}/pause")
async def pause_digest(digest_id: int, current_user: User = Depends(get_current_user)):
    """Pause a digest."""
    async with db_session() as session:
        digest = await session.get(Digest, digest_id)
        if digest is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Digest not found",
            )
        if digest.owner_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )

        digest.status = DigestStatus.PAUSED
        await session.commit()
        await session.refresh(digest)

        return {
            "id": digest.id,
            "name": digest.name,
            "status": digest.status,
        }


@router.post("/{digest_id}/resume")
async def resume_digest(digest_id: int, current_user: User = Depends(get_current_user)):
    """Resume a paused digest."""
    async with db_session() as session:
        digest = await session.get(Digest, digest_id)
        if digest is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Digest not found",
            )
        if digest.owner_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )

        digest.status = DigestStatus.ACTIVE
        await session.commit()
        await session.refresh(digest)

        return {
            "id": digest.id,
            "name": digest.name,
            "status": digest.status,
        }


@router.post("/{digest_id}/deliveries")
async def deliver_digest_now(digest_id: int, current_user: User = Depends(get_current_user)):
    """Trigger immediate delivery of a digest."""
    # TODO: Implement actual delivery trigger
    return {
        "message": "Delivery triggered (implement Celery task)",
        "digest_id": digest_id,
    }
