"""
test_auth.py — tests for POST /api/v1/auth/register and /api/v1/auth/login
"""

import pytest
from httpx import AsyncClient


class TestRegister:
    async def test_register_success(self, client: AsyncClient):
        """New user with valid payload returns 201 and correct fields."""
        resp = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "strongpassword",
                "full_name": "New User",
            },
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["email"] == "newuser@example.com"
        assert body["full_name"] == "New User"
        assert body["is_active"] is True
        # Password must never be returned
        assert "password" not in body
        assert "hashed_password" not in body

    async def test_register_duplicate_email_returns_409(self, client: AsyncClient):
        """Registering the same email twice returns 409 Conflict."""
        payload = {
            "email": "duplicate@example.com",
            "password": "secret",
            "full_name": "First",
        }
        first = await client.post("/api/v1/auth/register", json=payload)
        assert first.status_code == 201

        second = await client.post("/api/v1/auth/register", json=payload)
        assert second.status_code == 409
        assert "already registered" in second.json()["detail"].lower()

    async def test_register_invalid_email_returns_422(self, client: AsyncClient):
        """Malformed email fails Pydantic validation before hitting the service."""
        resp = await client.post(
            "/api/v1/auth/register",
            json={"email": "not-an-email", "password": "x", "full_name": "Y"},
        )
        assert resp.status_code == 422

    async def test_register_missing_fields_returns_422(self, client: AsyncClient):
        """Missing required fields return 422."""
        resp = await client.post(
            "/api/v1/auth/register",
            json={"email": "ok@example.com"},  # password and full_name missing
        )
        assert resp.status_code == 422


class TestLogin:
    async def test_login_success_returns_token(
        self, client: AsyncClient, registered_user: dict
    ):
        """Valid credentials return access_token and token_type=bearer."""
        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "secret123"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body
        assert body["token_type"] == "bearer"
        # Token should be a non-empty string
        assert isinstance(body["access_token"], str)
        assert len(body["access_token"]) > 0

    async def test_login_wrong_password_returns_401(
        self, client: AsyncClient, registered_user: dict
    ):
        """Wrong password returns 401 Unauthorized."""
        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "wrongpassword"},
        )
        assert resp.status_code == 401
        assert "invalid" in resp.json()["detail"].lower()

    async def test_login_unknown_email_returns_401(self, client: AsyncClient):
        """Non-existent email returns 401, not 404 — avoids user enumeration."""
        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": "ghost@example.com", "password": "whatever"},
        )
        assert resp.status_code == 401

    async def test_login_invalid_email_format_returns_422(self, client: AsyncClient):
        """Malformed email in login payload returns 422 before the service runs."""
        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": "not-email", "password": "x"},
        )
        assert resp.status_code == 422
