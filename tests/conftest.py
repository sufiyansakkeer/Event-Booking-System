"""
conftest.py — shared fixtures for the entire test suite.

Scoping strategy:
  - postgres_container + async_engine: session-scoped (expensive, start once)
  - db_connection + db_transaction + db_session + client: function-scoped
    Each test gets its OWN rolled-back transaction → full isolation.
  - Data fixtures (registered_user, auth_token, etc.): function-scoped
    so each test starts with a clean slate.
"""

from collections.abc import AsyncGenerator
from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from fastapi_cache import FastAPICache
from fastapi_cache.backends.inmemory import InMemoryBackend
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncSession,
    AsyncTransaction,
    create_async_engine,
)
from testcontainers.postgres import PostgresContainer

from app.db import get_db
from app.main import app
from app.models.base import Base
from app.models.booking import Booking  # noqa: F401
from app.models.event import Event  # noqa: F401
from app.models.user import User  # noqa: F401


# ── Session-scoped: start once, reuse across all tests ────────────────────────


@pytest.fixture(scope="session")
def postgres_container():
    with PostgresContainer("postgres:16-alpine") as pg:
        yield pg


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def async_engine(postgres_container: PostgresContainer):
    url = postgres_container.get_connection_url().replace(
        "postgresql+psycopg2://", "postgresql+asyncpg://"
    )
    engine = create_async_engine(url, echo=False, future=True)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


# ── Function-scoped: each test gets a fresh rolled-back transaction ────────────
# This is the correct isolation pattern. Think of it like Flutter widget tests
# where each test gets a fresh widget tree — no state bleeds between tests.


@pytest_asyncio.fixture
async def db_connection(async_engine) -> AsyncGenerator[AsyncConnection, None]:
    async with async_engine.connect() as conn:
        yield conn


@pytest_asyncio.fixture
async def db_transaction(
    db_connection: AsyncConnection,
) -> AsyncGenerator[AsyncTransaction, None]:
    transaction = await db_connection.begin()
    yield transaction
    # Always rolls back — even if the test committed inside, the outer
    # transaction wraps everything and undoes it.
    await transaction.rollback()


@pytest_asyncio.fixture
async def db_session(
    db_connection: AsyncConnection,
    db_transaction: AsyncTransaction,
) -> AsyncGenerator[AsyncSession, None]:
    session = AsyncSession(bind=db_connection, expire_on_commit=False)
    yield session
    await session.close()


# ── Function-scoped client ─────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    # InMemoryBackend so @cache decorators don't need real Redis.
    FastAPICache.init(InMemoryBackend(), prefix="test")

    with patch("app.services.booking.send_booking_confirmation_email") as mock_task:
        mock_task.delay = MagicMock()

        with patch("app.services.booking.redis_client") as mock_redis:
            mock_redis.set = AsyncMock(return_value=True)
            mock_redis.get = AsyncMock(return_value=None)

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as ac:
                yield ac

    app.dependency_overrides.clear()


# ── Function-scoped data fixtures ──────────────────────────────────────────────
# Each test that needs a user/token/event gets a fresh one in its own
# rolled-back transaction. No cross-test state accumulation.


@pytest_asyncio.fixture
async def registered_user(client: AsyncClient) -> dict[str, Any]:
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "test@example.com",
            "password": "secret123",
            "full_name": "Test User",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


@pytest_asyncio.fixture
async def auth_token(client: AsyncClient, registered_user: dict[str, Any]) -> str:
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": "secret123"},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


@pytest_asyncio.fixture
async def auth_headers(auth_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {auth_token}"}


@pytest_asyncio.fixture
async def created_event(
    client: AsyncClient, auth_headers: dict[str, str]
) -> dict[str, Any]:
    starts_at = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
    resp = await client.post(
        "/api/v1/events",
        json={
            "title": "Test Concert",
            "description": "A great show",
            "venue": "Bangalore Arena",
            "starts_at": starts_at,
            "total_seats": 100,
            "ticket_price": "500.00",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()
