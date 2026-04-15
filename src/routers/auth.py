"""Authentication endpoints."""

from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
import json

from src.auth import create_access_token
from src.database import db_session
from src.models.user import User
from src.config import config


router = APIRouter(prefix="/api/auth", tags=["auth"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


class SignupIn(BaseModel):
    email: EmailStr
    password: str


async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """Get current authenticated user."""
    from src.auth import verify_token

    try:
        payload = verify_token(token)
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    async with db_session() as session:
        user = await session.get(User, payload.get("sub"))
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )
    return user


@router.post("/signup", status_code=status.HTTP_201_CREATED, response_model=None)
async def signup(payload: SignupIn = None, request: Request = None):
    """Register a new user (accepts JSON body). If payload parsing fails, attempt a manual JSON parse as a fallback."""
    # Allow Pydantic parsing to work; if it doesn't, try reading raw JSON/form from request
    if payload is None:
        if request is None:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid payload")
        # Try JSON body
        data = None
        try:
            data = await request.json()
        except Exception:
            data = None
        # Try form body
        if not data:
            try:
                form = await request.form()
                data = {k: v for k, v in form.items()}
            except Exception:
                data = None
        # Try raw body decode
        if not data:
            try:
                raw = await request.body()
                if raw:
                    data = json.loads(raw.decode())
            except Exception:
                data = None
        if not data:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid request payload")
        email = data.get("email")
        password = data.get("password")
    else:
        email = payload.email
        password = payload.password

    async with db_session() as session:
        res = await session.execute(select(User).filter_by(email=email))
        existing = res.scalar_one_or_none()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User already registered",
            )

        user = User(email=email)
        user.set_password(password)
        session.add(user)
        await session.commit()
        await session.refresh(user)

        access_token_expires = timedelta(minutes=config().access_token_expire_minutes)
        access_token = create_access_token(
            data={"sub": str(user.id)},
            expires_delta=access_token_expires,
        )

        return {
            "id": user.id,
            "email": user.email,
            "token": access_token,
            "token_type": "bearer",
        }


@router.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Login and return access token."""
    async with db_session() as session:
        res = await session.execute(select(User).filter_by(email=form_data.username))
        user = res.scalar_one_or_none()
        if user is None or not user.verify_password(form_data.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        access_token_expires = timedelta(minutes=config().access_token_expire_minutes)
        access_token = create_access_token(
            data={"sub": str(user.id)},
            expires_delta=access_token_expires,
        )

        return {
            "access_token": access_token,
            "token_type": "bearer",
        }


@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    """Get current user information."""
    return {
        "id": current_user.id,
        "email": current_user.email,
    }


@router.post("/password-reset")
async def password_reset(email: EmailStr):
    """Request password reset."""
    # For now, just acknowledge the request
    # In production, this would send an actual email with reset token
    return {
        "detail": f"Password reset instructions sent to {email}",
    }
