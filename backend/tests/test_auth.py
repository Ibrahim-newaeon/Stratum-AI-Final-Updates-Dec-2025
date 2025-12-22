"""
Stratum AI - Authentication Tests
Tests for login, registration, token refresh, and password reset flows.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User, Tenant
from app.core.security import (
    create_password_reset_token,
    verify_password_reset_token,
    verify_password,
    get_password_hash,
)


class TestLogin:
    """Tests for the login endpoint."""

    @pytest.mark.asyncio
    async def test_login_success(
        self, client: AsyncClient, test_user: User, test_tenant: Tenant
    ):
        """Test successful login with valid credentials."""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "testuser@example.com",
                "password": "TestPassword123",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "access_token" in data["data"]
        assert "refresh_token" in data["data"]
        assert data["data"]["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_login_invalid_email(self, client: AsyncClient):
        """Test login with non-existent email."""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "SomePassword123",
            },
        )

        assert response.status_code == 401
        assert "Invalid email or password" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_login_invalid_password(
        self, client: AsyncClient, test_user: User
    ):
        """Test login with wrong password."""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "testuser@example.com",
                "password": "WrongPassword123",
            },
        )

        assert response.status_code == 401
        assert "Invalid email or password" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_login_inactive_user(
        self, client: AsyncClient, async_session: AsyncSession, test_user: User
    ):
        """Test login with inactive user account."""
        # Deactivate user
        test_user.is_active = False
        await async_session.commit()

        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "testuser@example.com",
                "password": "TestPassword123",
            },
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_login_missing_email(self, client: AsyncClient):
        """Test login with missing email."""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "password": "SomePassword123",
            },
        )

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_login_missing_password(self, client: AsyncClient):
        """Test login with missing password."""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "testuser@example.com",
            },
        )

        assert response.status_code == 422  # Validation error


class TestRegistration:
    """Tests for the registration endpoint."""

    @pytest.mark.asyncio
    async def test_register_success(
        self, client: AsyncClient, test_tenant: Tenant
    ):
        """Test successful user registration."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "NewPassword123",
                "full_name": "New User",
                "tenant_id": test_tenant.id,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["email"] == "newuser@example.com"

    @pytest.mark.asyncio
    async def test_register_duplicate_email(
        self, client: AsyncClient, test_user: User, test_tenant: Tenant
    ):
        """Test registration with existing email."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "testuser@example.com",  # Already exists
                "password": "AnotherPassword123",
                "full_name": "Another User",
                "tenant_id": test_tenant.id,
            },
        )

        assert response.status_code == 400
        assert "already registered" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_register_weak_password_no_uppercase(
        self, client: AsyncClient, test_tenant: Tenant
    ):
        """Test registration with password missing uppercase."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "weakpassword123",  # No uppercase
                "full_name": "New User",
                "tenant_id": test_tenant.id,
            },
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_register_weak_password_no_digit(
        self, client: AsyncClient, test_tenant: Tenant
    ):
        """Test registration with password missing digit."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "WeakPassword",  # No digit
                "full_name": "New User",
                "tenant_id": test_tenant.id,
            },
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_register_short_password(
        self, client: AsyncClient, test_tenant: Tenant
    ):
        """Test registration with too short password."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "Short1",  # Less than 8 chars
                "full_name": "New User",
                "tenant_id": test_tenant.id,
            },
        )

        assert response.status_code == 422


class TestTokenRefresh:
    """Tests for the token refresh endpoint."""

    @pytest.mark.asyncio
    async def test_refresh_token_success(
        self, client: AsyncClient, test_user: User
    ):
        """Test successful token refresh."""
        # First login to get tokens
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "testuser@example.com",
                "password": "TestPassword123",
            },
        )
        refresh_token = login_response.json()["data"]["refresh_token"]

        # Use refresh token to get new tokens
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "access_token" in data["data"]
        assert "refresh_token" in data["data"]

    @pytest.mark.asyncio
    async def test_refresh_token_invalid(self, client: AsyncClient):
        """Test token refresh with invalid token."""
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "invalid_token"},
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_refresh_token_access_token_rejected(
        self, client: AsyncClient, test_user: User
    ):
        """Test that access token cannot be used as refresh token."""
        # First login to get tokens
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "testuser@example.com",
                "password": "TestPassword123",
            },
        )
        access_token = login_response.json()["data"]["access_token"]

        # Try to use access token as refresh token
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": access_token},
        )

        assert response.status_code == 401


class TestForgotPassword:
    """Tests for the forgot password endpoint."""

    @pytest.mark.asyncio
    async def test_forgot_password_existing_email(
        self, client: AsyncClient, test_user: User
    ):
        """Test forgot password with existing email."""
        response = await client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "testuser@example.com"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        # Should always return success message (security)
        assert "password reset link" in data["data"]["message"].lower()

    @pytest.mark.asyncio
    async def test_forgot_password_nonexistent_email(self, client: AsyncClient):
        """Test forgot password with non-existent email (should still return success)."""
        response = await client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "nonexistent@example.com"},
        )

        # Should return success to prevent email enumeration
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_forgot_password_invalid_email_format(self, client: AsyncClient):
        """Test forgot password with invalid email format."""
        response = await client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "not-an-email"},
        )

        assert response.status_code == 422


class TestResetPassword:
    """Tests for the reset password endpoint."""

    @pytest.mark.asyncio
    async def test_reset_password_success(
        self, client: AsyncClient, test_user: User, async_session: AsyncSession
    ):
        """Test successful password reset."""
        # Generate a valid reset token
        reset_token = create_password_reset_token("testuser@example.com")

        response = await client.post(
            "/api/v1/auth/reset-password",
            json={
                "token": reset_token,
                "new_password": "NewSecurePassword123",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "reset successfully" in data["data"]["message"].lower()

        # Verify password was actually changed by trying to login
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "testuser@example.com",
                "password": "NewSecurePassword123",
            },
        )
        assert login_response.status_code == 200

    @pytest.mark.asyncio
    async def test_reset_password_invalid_token(self, client: AsyncClient):
        """Test password reset with invalid token."""
        response = await client.post(
            "/api/v1/auth/reset-password",
            json={
                "token": "invalid_token",
                "new_password": "NewPassword123",
            },
        )

        assert response.status_code == 400
        assert "Invalid or expired" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_reset_password_weak_password(
        self, client: AsyncClient, test_user: User
    ):
        """Test password reset with weak password."""
        reset_token = create_password_reset_token("testuser@example.com")

        response = await client.post(
            "/api/v1/auth/reset-password",
            json={
                "token": reset_token,
                "new_password": "weak",  # Too short, no uppercase, no digit
            },
        )

        assert response.status_code == 422


class TestLogout:
    """Tests for the logout endpoint."""

    @pytest.mark.asyncio
    async def test_logout_success(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test successful logout."""
        response = await client.post(
            "/api/v1/auth/logout",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_logout_without_token(self, client: AsyncClient):
        """Test logout without authentication."""
        response = await client.post("/api/v1/auth/logout")

        # Should still succeed (graceful logout)
        assert response.status_code == 200


class TestSecurityFunctions:
    """Unit tests for security utility functions."""

    def test_password_hash_and_verify(self):
        """Test password hashing and verification."""
        password = "TestPassword123"
        hashed = get_password_hash(password)

        assert hashed != password
        assert verify_password(password, hashed)
        assert not verify_password("WrongPassword", hashed)

    def test_password_reset_token_creation_and_verification(self):
        """Test password reset token creation and verification."""
        email = "test@example.com"
        token = create_password_reset_token(email)

        # Verify token
        verified_email = verify_password_reset_token(token)
        assert verified_email == email

    def test_password_reset_token_invalid(self):
        """Test invalid password reset token."""
        result = verify_password_reset_token("invalid_token")
        assert result is None
