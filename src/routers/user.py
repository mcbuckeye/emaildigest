"""User settings endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.mailer.client import send_email_verification
from src.models import EmailVerificationToken, User
from src.routers.auth import _hash_token, get_current_user

router = APIRouter(prefix="/api/user", tags=["user"])


class ChangePasswordIn(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)


class ChangeEmailIn(BaseModel):
    new_email: EmailStr
    current_password: str


@router.post("/change-password")
async def change_password(
    payload: ChangePasswordIn,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    if not current_user.verify_password(payload.current_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is wrong")
    current_user.set_password(payload.new_password)
    await db.commit()
    return {"detail": "Password changed"}


@router.post("/change-email")
async def change_email(
    payload: ChangeEmailIn,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    if not current_user.verify_password(payload.current_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is wrong")
    existing = (
        await db.execute(select(User).where(User.email == payload.new_email, User.id != current_user.id))
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already in use")

    import secrets
    from datetime import datetime, timedelta

    current_user.email = payload.new_email
    current_user.email_verified_at = None
    raw = secrets.token_urlsafe(32)
    db.add(
        EmailVerificationToken(
            user_id=current_user.id,
            token_hash=_hash_token(raw),
            expires_at=datetime.utcnow() + timedelta(days=2),
        )
    )
    await db.commit()
    await send_email_verification(current_user.email, raw)
    return {"detail": "Email changed; please verify"}


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    confirm: str = Query(default=""),
):
    if confirm != "DELETE":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Send ?confirm=DELETE")
    await db.delete(current_user)
    await db.commit()
