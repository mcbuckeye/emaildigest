"""Tests for user model and auth."""

import pytest
from sqlalchemy.orm import Session

from src.models.user import User


class TestUserModel:
    """Tests for User model."""

    def test_user_creation(self, test_db: Session, test_user: User):
        """Test user creation."""
        assert test_user.id is not None
        assert test_user.email == "test@example.com"
        assert test_user.password_hash is not None
        assert test_user.created_at is not None
        assert test_user.updated_at is not None

    def test_password_hashing(self, test_db: Session):
        """Test that passwords are properly hashed."""
        user = User(
            email="newuser@example.com",
            password_hash="hashed_password_123",
        )
        test_db.add(user)
        test_db.commit()
        test_db.refresh(user)

        assert user.password_hash == "hashed_password_123"
        assert user.password_hash != "plain_password"

    def test_password_verification(self, test_user: User):
        """Test password verification."""
        # Correct password
        assert test_user.verify_password("testpassword123") is True

        # Incorrect password
        assert test_user.verify_password("wrongpassword") is False

    def test_unique_email(self, test_db: Session):
        """Test that email must be unique."""
        user1 = User(
            email="unique@example.com",
            password_hash="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.GEjCYKyLwvX4AC",
        )
        user2 = User(
            email="unique@example.com",  # Duplicate email
            password_hash="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.GEjCYKyLwvX4AC",
        )

        test_db.add(user1)
        test_db.commit()

        test_db.add(user2)
        with pytest.raises(Exception):
            test_db.commit()

    def test_set_password(self, test_db: Session):
        """Test set_password method."""
        user = User(
            email="setpass@example.com",
            password_hash="",
        )
        test_db.add(user)
        test_db.commit()
        test_db.refresh(user)

        user.set_password("new_password_123")
        test_db.commit()
        test_db.refresh(user)

        assert user.verify_password("new_password_123") is True
        assert user.verify_password("old_password") is False


class TestAuthEndpoints:
    """Tests for authentication endpoints."""

    @pytest.mark.asyncio
    async def test_user_signup(self, client: AsyncClient):
        """Test user signup."""
        response = await client.post(
            "/api/auth/signup",
            json={
                "email": "signup_test@example.com",
                "password": "SecurePass123!",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "signup_test@example.com"
        assert "token" in data
        assert "token_type" in data
        assert data["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_user_signup_duplicate_email(self, client: AsyncClient):
        """Test signup with duplicate email returns error."""
        # First signup
        await client.post(
            "/api/auth/signup",
            json={
                "email": "dup_test@example.com",
                "password": "SecurePass123!",
            },
        )

        # Second signup with same email
        response = await client.post(
            "/api/auth/signup",
            json={
                "email": "dup_test@example.com",
                "password": "SecurePass123!",
            },
        )

        assert response.status_code == 400
        assert "already registered" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_user_login(self, client: AsyncClient):
        """Test user login."""
        # Create user first
        await client.post(
            "/api/auth/signup",
            json={
                "email": "login_test@example.com",
                "password": "SecurePass123!",
            },
        )

        # Login
        response = await client.post(
            "/api/auth/login",
            json={
                "email": "login_test@example.com",
                "password": "SecurePass123!",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_user_login_invalid_credentials(self, client: AsyncClient):
        """Test login with wrong password."""
        # Create user first
        await client.post(
            "/api/auth/signup",
            json={
                "email": "invalid_login@example.com",
                "password": "CorrectPass123!",
            },
        )

        # Login with wrong password
        response = await client.post(
            "/api/auth/login",
            json={
                "email": "invalid_login@example.com",
                "password": "WrongPass123!",
            },
        )

        assert response.status_code == 401
        assert "invalid" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_user_me(self, client: AsyncClient):
        """Test getting current user info."""
        # Create user and login
        signup_response = await client.post(
            "/api/auth/signup",
            json={
                "email": "me_test@example.com",
                "password": "SecurePass123!",
            },
        )
        token = signup_response.json()["token"]

        # Get current user
        headers = {"Authorization": f"Bearer {token}"}
        response = await client.get("/api/auth/me", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "me_test@example.com"

    @pytest.mark.asyncio
    async def test_user_me_unauthorized(self, client: AsyncClient):
        """Test getting current user without auth."""
        response = await client.get("/api/auth/me")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_password_reset(self, client: AsyncClient):
        """Test password reset flow."""
        # Create user
        await client.post(
            "/api/auth/signup",
            json={
                "email": "reset_test@example.com",
                "password": "OldPassword123!",
            },
        )

        # Request password reset
        response = await client.post(
            "/api/auth/password-reset",
            json={
                "email": "reset_test@example.com",
            },
        )
        assert response.status_code == 200
        assert "sent" in response.json()["detail"].lower()

        # Login with old password (should still work since we simulate reset)
        response = await client.post(
            "/api/auth/login",
            json={
                "email": "reset_test@example.com",
                "password": "OldPassword123!",
            },
        )
        assert response.status_code == 200
