"""Authentication endpoints."""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import create_access_token, verify_token
from src.config import config
from src.database import get_db
from src.mailer.client import send_password_reset_email
from src.models import PasswordResetToken, User
from src.rate_limit import limiter

router = APIRouter(prefix="/api/auth", tags=["auth"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


class SignupIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginJSONIn(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class SignupOut(BaseModel):
    id: int
    email: EmailStr
    token: str
    token_type: str = "bearer"


class PasswordResetRequestIn(BaseModel):
    email: EmailStr


class PasswordResetConfirmIn(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    try:
        payload = verify_token(token)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    sub = payload.get("sub")
    if not sub:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    try:
        user_id = int(sub)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc

    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _issue_access_token(user: User) -> str:
    return create_access_token(
        {"sub": str(user.id)},
        expires_delta=timedelta(minutes=config().access_token_expire_minutes),
    )


def _env_rate(key: str, fallback: str) -> str:
    import os

    return os.environ.get(key) or fallback


@router.post("/signup", status_code=status.HTTP_201_CREATED, response_model=SignupOut)
@limiter.limit(lambda: _env_rate("RATE_LIMIT_SIGNUP", config().rate_limit_signup))
async def signup(
    request: Request,
    payload: SignupIn,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SignupOut:
    existing = (await db.execute(select(User).where(User.email == payload.email))).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User already registered")

    user = User(email=payload.email)
    user.set_password(payload.password)
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return SignupOut(id=user.id, email=user.email, token=_issue_access_token(user))


@router.post("/login", response_model=TokenOut)
@limiter.limit(lambda: _env_rate("RATE_LIMIT_LOGIN", config().rate_limit_login))
async def login(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenOut:
    """Accept either JSON {email, password} or OAuth2 form (username, password)."""
    email: str | None = None
    password: str | None = None

    content_type = (request.headers.get("content-type") or "").lower()
    if "application/json" in content_type:
        try:
            data = await request.json()
        except Exception:
            data = None
        if not data:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid JSON")
        email = data.get("email") or data.get("username")
        password = data.get("password")
    else:
        try:
            form = await request.form()
        except Exception:
            form = {}
        email = form.get("username") or form.get("email")
        password = form.get("password")

    if not email or not password:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="email and password required")

    user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if user is None or not user.verify_password(password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return TokenOut(access_token=_issue_access_token(user))


@router.get("/me")
async def get_me(current_user: Annotated[User, Depends(get_current_user)]):
    return {"id": current_user.id, "email": current_user.email}


@router.post("/password-reset", status_code=status.HTTP_202_ACCEPTED)
@limiter.limit(lambda: _env_rate("RATE_LIMIT_PASSWORD_RESET", "3/minute"))
async def password_reset_request(
    request: Request,
    payload: PasswordResetRequestIn,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Issue a one-time reset token. Always returns 202 to avoid account enumeration."""
    user = (await db.execute(select(User).where(User.email == payload.email))).scalar_one_or_none()
    if user is not None:
        raw_token = secrets.token_urlsafe(32)
        token_row = PasswordResetToken(
            user_id=user.id,
            token_hash=_hash_token(raw_token),
            expires_at=datetime.utcnow() + timedelta(minutes=config().password_reset_token_expire_minutes),
        )
        db.add(token_row)
        await db.commit()
        await send_password_reset_email(user.email, raw_token)
    return {"detail": "If the email is registered, a reset link has been sent."}


@router.post("/password-reset/confirm")
async def password_reset_confirm(
    payload: PasswordResetConfirmIn,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    token_hash = _hash_token(payload.token)
    row = (
        await db.execute(select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash))
    ).scalar_one_or_none()

    if row is None or row.used_at is not None or row.expires_at < datetime.utcnow():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired token")

    user = await db.get(User, row.user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token")

    user.set_password(payload.new_password)
    row.used_at = datetime.utcnow()
    await db.commit()
    return {"detail": "Password updated"}
