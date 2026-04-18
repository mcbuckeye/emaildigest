"""Tests for authentication endpoints and flows."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from src.models import PasswordResetToken, User


class TestUserModel:
    async def test_password_hashing_roundtrip(self, db):
        user = User(email="hash@example.com")
        user.set_password("correct-horse")
        db.add(user)
        await db.commit()
        await db.refresh(user)

        assert user.password_hash != "correct-horse"
        assert user.verify_password("correct-horse") is True
        assert user.verify_password("wrong") is False

    async def test_email_unique(self, db):
        from sqlalchemy.exc import IntegrityError

        db.add(User(email="dup@example.com", password_hash="x"))
        await db.commit()
        db.add(User(email="dup@example.com", password_hash="x"))
        with pytest.raises(IntegrityError):
            await db.commit()


class TestSignup:
    async def test_signup_returns_token(self, client: AsyncClient):
        r = await client.post(
            "/api/auth/signup",
            json={"email": "new@example.com", "password": "pw-123456"},
        )
        assert r.status_code == 201
        data = r.json()
        assert data["email"] == "new@example.com"
        assert data["token_type"] == "bearer"
        assert len(data["token"]) > 20

    async def test_signup_duplicate_email(self, client: AsyncClient):
        await client.post("/api/auth/signup", json={"email": "dup2@example.com", "password": "pw-123456"})
        r = await client.post("/api/auth/signup", json={"email": "dup2@example.com", "password": "pw-123456"})
        assert r.status_code == 400

    async def test_signup_missing_fields(self, client: AsyncClient):
        r = await client.post("/api/auth/signup", json={"email": "nope@example.com"})
        assert r.status_code == 422

    async def test_signup_invalid_email(self, client: AsyncClient):
        r = await client.post("/api/auth/signup", json={"email": "not-an-email", "password": "pw-123456"})
        assert r.status_code == 422


class TestLogin:
    async def test_login_with_json(self, client: AsyncClient):
        await client.post("/api/auth/signup", json={"email": "li@example.com", "password": "pw-123456"})
        r = await client.post("/api/auth/login", json={"email": "li@example.com", "password": "pw-123456"})
        assert r.status_code == 200
        assert r.json()["token_type"] == "bearer"
        assert "access_token" in r.json()

    async def test_login_with_form(self, client: AsyncClient):
        await client.post("/api/auth/signup", json={"email": "li2@example.com", "password": "pw-123456"})
        r = await client.post(
            "/api/auth/login",
            data={"username": "li2@example.com", "password": "pw-123456"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert r.status_code == 200

    async def test_login_wrong_password(self, client: AsyncClient):
        await client.post("/api/auth/signup", json={"email": "li3@example.com", "password": "pw-123456"})
        r = await client.post("/api/auth/login", json={"email": "li3@example.com", "password": "wrong"})
        assert r.status_code == 401

    async def test_login_unknown_email(self, client: AsyncClient):
        r = await client.post("/api/auth/login", json={"email": "ghost@example.com", "password": "whatever"})
        assert r.status_code == 401


class TestMe:
    async def test_me_returns_current_user(self, client: AsyncClient, user, auth_headers):
        r = await client.get("/api/auth/me", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["email"] == user.email

    async def test_me_without_auth(self, client: AsyncClient):
        r = await client.get("/api/auth/me")
        assert r.status_code == 401

    async def test_me_with_expired_token(self, client: AsyncClient, user):
        from src.auth import create_access_token

        token = create_access_token({"sub": str(user.id)}, expires_delta=timedelta(seconds=-10))
        r = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 401


class TestPasswordReset:
    async def test_request_token_creates_db_row(self, client: AsyncClient, db, user, mocker):
        mocker.patch("src.routers.auth.send_password_reset_email", autospec=True)
        r = await client.post("/api/auth/password-reset", json={"email": user.email})
        assert r.status_code == 202

        stmt = select(PasswordResetToken).where(PasswordResetToken.user_id == user.id)
        rows = (await db.execute(stmt)).scalars().all()
        assert len(rows) == 1
        assert rows[0].expires_at > datetime.utcnow()
        assert rows[0].used_at is None

    async def test_request_for_unknown_email_returns_202(self, client: AsyncClient, mocker):
        mocker.patch("src.routers.auth.send_password_reset_email", autospec=True)
        r = await client.post("/api/auth/password-reset", json={"email": "nobody@example.com"})
        assert r.status_code == 202

    async def test_confirm_changes_password(self, client: AsyncClient, user, mocker):
        sent = {}

        async def capture_send(email: str, token: str) -> None:
            sent["email"] = email
            sent["token"] = token

        mocker.patch("src.routers.auth.send_password_reset_email", side_effect=capture_send)

        await client.post("/api/auth/password-reset", json={"email": user.email})
        assert "token" in sent

        r = await client.post(
            "/api/auth/password-reset/confirm",
            json={"token": sent["token"], "new_password": "brand-new-pw"},
        )
        assert r.status_code == 200

        login = await client.post("/api/auth/login", json={"email": user.email, "password": "brand-new-pw"})
        assert login.status_code == 200

    async def test_confirm_token_is_single_use(self, client: AsyncClient, user, mocker):
        sent = {}

        async def capture_send(email: str, token: str) -> None:
            sent["token"] = token

        mocker.patch("src.routers.auth.send_password_reset_email", side_effect=capture_send)
        await client.post("/api/auth/password-reset", json={"email": user.email})

        r1 = await client.post(
            "/api/auth/password-reset/confirm",
            json={"token": sent["token"], "new_password": "pw-first-change"},
        )
        assert r1.status_code == 200

        r2 = await client.post(
            "/api/auth/password-reset/confirm",
            json={"token": sent["token"], "new_password": "pw-second-change"},
        )
        assert r2.status_code == 400

    async def test_confirm_rejects_invalid_token(self, client: AsyncClient):
        r = await client.post(
            "/api/auth/password-reset/confirm",
            json={"token": "not-a-real-token", "new_password": "brand-new-pw"},
        )
        assert r.status_code == 400
