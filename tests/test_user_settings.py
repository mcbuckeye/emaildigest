"""Tests for /api/user settings endpoints."""

from __future__ import annotations

from sqlalchemy import select


class TestChangePassword:
    async def test_requires_current_password(self, client, auth_headers):
        r = await client.post(
            "/api/user/change-password",
            headers=auth_headers,
            json={"current_password": "wrong", "new_password": "pw-new12345"},
        )
        assert r.status_code == 400

    async def test_changes_password(self, client, auth_headers, user):
        r = await client.post(
            "/api/user/change-password",
            headers=auth_headers,
            json={"current_password": "password123", "new_password": "pw-new12345"},
        )
        assert r.status_code == 200
        login = await client.post(
            "/api/auth/login",
            json={"email": user.email, "password": "pw-new12345"},
        )
        assert login.status_code == 200


class TestChangeEmail:
    async def test_rejects_used_email(self, client, auth_headers, other_user):
        r = await client.post(
            "/api/user/change-email",
            headers=auth_headers,
            json={"new_email": other_user.email, "current_password": "password123"},
        )
        assert r.status_code == 409

    async def test_changes_email_and_re_verifies(self, client, auth_headers, db, user, mocker):
        mocker.patch("src.routers.user.send_email_verification", autospec=True)
        r = await client.post(
            "/api/user/change-email",
            headers=auth_headers,
            json={"new_email": "new-email@example.com", "current_password": "password123"},
        )
        assert r.status_code == 200
        await db.refresh(user)
        assert user.email == "new-email@example.com"
        assert user.email_verified_at is None


class TestDeleteAccount:
    async def test_deletes_user(self, client, auth_headers, db, user):
        r = await client.delete(
            "/api/user",
            headers=auth_headers,
            params={"confirm": "DELETE"},
        )
        assert r.status_code == 204

        from src.models import User

        remaining = (
            await db.execute(select(User).where(User.id == user.id))
        ).scalar_one_or_none()
        assert remaining is None

    async def test_requires_confirmation(self, client, auth_headers):
        r = await client.delete("/api/user", headers=auth_headers)
        assert r.status_code == 400
