"""Tests for email verification flow."""

from __future__ import annotations

from sqlalchemy import select

from src.models import EmailVerificationToken


class TestEmailVerification:
    async def test_signup_creates_verification_token(self, client, db, mocker):
        send = mocker.patch("src.routers.auth.send_email_verification", autospec=True)

        r = await client.post(
            "/api/auth/signup",
            json={"email": "verify@example.com", "password": "pw-12345678"},
        )
        assert r.status_code == 201

        rows = (await db.execute(select(EmailVerificationToken))).scalars().all()
        assert len(rows) == 1
        assert rows[0].used_at is None
        send.assert_awaited_once()

    async def test_verify_confirms_email(self, client, db, mocker):
        captured = {}

        async def capture(email, token):
            captured["token"] = token

        mocker.patch("src.routers.auth.send_email_verification", side_effect=capture)

        await client.post(
            "/api/auth/signup",
            json={"email": "verify2@example.com", "password": "pw-12345678"},
        )
        assert "token" in captured

        r = await client.post(
            "/api/auth/verify-email", json={"token": captured["token"]}
        )
        assert r.status_code == 200

        from src.models import User

        user = (
            await db.execute(select(User).where(User.email == "verify2@example.com"))
        ).scalar_one()
        assert user.email_verified_at is not None

    async def test_invalid_token_rejected(self, client):
        r = await client.post("/api/auth/verify-email", json={"token": "nope"})
        assert r.status_code == 400

    async def test_resend_verification(self, client, auth_headers, mocker):
        send = mocker.patch("src.routers.auth.send_email_verification", autospec=True)
        r = await client.post("/api/auth/resend-verification", headers=auth_headers)
        assert r.status_code == 202
        send.assert_awaited_once()
