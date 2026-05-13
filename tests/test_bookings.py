"""
test_bookings.py — tests for POST /api/v1/bookings and PATCH /api/v1/bookings/{id}

Redis (idempotency) and Celery (email task) are mocked in conftest.py.
The mock for redis_client.set returns True by default (SET NX succeeded).
Individual tests override that mock when testing the idempotency return path.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

FUTURE = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()


# ── Helpers ───────────────────────────────────────────────────────────────────


async def _register_and_login(client: AsyncClient, email: str) -> dict:
    """Register a fresh user and return auth headers."""
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "pass1234", "full_name": "Test"},
    )
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "pass1234"},
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def _create_event(client: AsyncClient, headers: dict, seats: int = 50) -> dict:
    """Create a future event with the given number of seats."""
    resp = await client.post(
        "/api/v1/events",
        json={
            "title": "Test Event",
            "venue": "Bangalore",
            "starts_at": FUTURE,
            "total_seats": seats,
            "ticket_price": "200",
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


# ── Create booking ─────────────────────────────────────────────────────────────


class TestCreateBooking:
    async def test_create_booking_success(
        self, client: AsyncClient, auth_headers: dict, created_event: dict
    ):
        """Valid booking returns 201 with correct user_id and event_id."""
        resp = await client.post(
            "/api/v1/bookings",
            json={"event_id": created_event["id"], "notes": "Window seat"},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["event_id"] == created_event["id"]
        assert "id" in body
        assert "user_id" in body

    async def test_create_booking_unauthenticated_returns_401(
        self, client: AsyncClient, created_event: dict
    ):
        """No token → 401 (HTTPBearer rejects missing header)."""
        resp = await client.post(
            "/api/v1/bookings",
            json={"event_id": created_event["id"]},
        )
        assert resp.status_code == 401

    async def test_create_booking_nonexistent_event_returns_404(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Booking for a non-existent event_id returns 404."""
        resp = await client.post(
            "/api/v1/bookings",
            json={"event_id": 999999},
            headers=auth_headers,
        )
        assert resp.status_code == 404

    async def test_booking_limit_enforced(
        self, client: AsyncClient, auth_headers: dict, created_event: dict
    ):
        """
        Service rejects booking when user already has 5 active bookings
        for the same event.

        Why mocked: flushed-but-uncommitted rows aren't visible to subsequent
        queries on the same rolled-back test transaction (READ COMMITTED
        isolation). Making 5 real bookings in a loop and checking the count
        in the same transaction always returns 0. We mock the repo method to
        simulate the 'already has 5' state instead.
        """
        from app.repositories.booking import BookingRepository
        from app.models.booking import Booking

        fake_five = [Booking(status="reserved") for _ in range(5)]

        with patch.object(
            BookingRepository,
            "get_user_bookings_for_event",
            new=AsyncMock(return_value=fake_five),
        ):
            resp = await client.post(
                "/api/v1/bookings",
                json={"event_id": created_event["id"]},
                headers=auth_headers,
            )

        assert resp.status_code == 400
        assert "limit" in resp.json()["detail"].lower()

    async def test_create_booking_no_seats_returns_409(
        self, client: AsyncClient, auth_headers: dict
    ):
        """
        Booking an event with 0 available seats returns 409 Conflict.
        We create an event with 1 seat, book it, then a second user tries.
        """
        event = await _create_event(client, auth_headers, seats=1)

        # First user books the only seat
        resp = await client.post(
            "/api/v1/bookings",
            json={"event_id": event["id"]},
            headers=auth_headers,
        )
        assert resp.status_code == 201

        # Second user tries — different credentials
        headers2 = await _register_and_login(client, "second@example.com")
        resp2 = await client.post(
            "/api/v1/bookings",
            json={"event_id": event["id"]},
            headers=headers2,
        )
        assert resp2.status_code == 409
        assert "seat" in resp2.json()["detail"].lower()


class TestIdempotency:
    async def test_idempotency_key_deduplicates_request(
        self, client: AsyncClient, auth_headers: dict, created_event: dict
    ):
        """
        When SET NX returns False (key already exists), the service looks up
        the existing booking and returns it instead of creating a duplicate.
        """
        # First call — redis mock returns True (key was set), booking created.
        resp1 = await client.post(
            "/api/v1/bookings",
            json={"event_id": created_event["id"], "idempotency_key": "unique-key-abc"},
            headers=auth_headers,
        )
        assert resp1.status_code == 201
        booking_id = resp1.json()["id"]

        # Second call: redis says key already exists (SET NX returns False).
        with patch("app.services.booking.redis_client") as mock_redis:
            mock_redis.set = AsyncMock(return_value=False)

            resp2 = await client.post(
                "/api/v1/bookings",
                json={
                    "event_id": created_event["id"],
                    "idempotency_key": "unique-key-abc",
                },
                headers=auth_headers,
            )
            assert resp2.status_code == 201
            assert resp2.json()["id"] == booking_id


# ── Update booking status ──────────────────────────────────────────────────────


class TestUpdateBookingStatus:
    async def _book(
        self,
        client: AsyncClient,
        headers: dict,
        event_id: int,
        idempotency_key: str = "test-key",
    ) -> dict:
        resp = await client.post(
            "/api/v1/bookings",
            json={"event_id": event_id, "idempotency_key": idempotency_key},
            headers=headers,
        )
        assert resp.status_code == 201, resp.text
        return resp.json()

    async def test_confirm_booking_success(
        self, client: AsyncClient, auth_headers: dict, created_event: dict
    ):
        """reserved → confirmed via PATCH with action=confirmed returns 200."""
        booking = await self._book(client, auth_headers, created_event["id"])
        resp = await client.patch(
            f"/api/v1/bookings/{booking['id']}",
            json={"action": "confirmed"},
            headers=auth_headers,
        )
        assert resp.status_code == 200

    async def test_cancel_booking_success(
        self, client: AsyncClient, auth_headers: dict, created_event: dict
    ):
        """reserved → cancelled via PATCH returns 200."""
        booking = await self._book(
            client, auth_headers, created_event["id"], idempotency_key="cancel-test"
        )
        resp = await client.patch(
            f"/api/v1/bookings/{booking['id']}",
            json={"action": "cancelled"},
            headers=auth_headers,
        )
        assert resp.status_code == 200

    async def test_invalid_transition_returns_400(
        self, client: AsyncClient, auth_headers: dict, created_event: dict
    ):
        """
        cancelled → confirmed is an invalid state machine transition.
        Cancel first, then try to confirm — expect 400.
        """
        booking = await self._book(
            client, auth_headers, created_event["id"], idempotency_key="invalid-trans"
        )
        await client.patch(
            f"/api/v1/bookings/{booking['id']}",
            json={"action": "cancelled"},
            headers=auth_headers,
        )
        resp = await client.patch(
            f"/api/v1/bookings/{booking['id']}",
            json={"action": "confirmed"},
            headers=auth_headers,
        )
        assert resp.status_code == 400

    async def test_update_another_users_booking_returns_404(
        self, client: AsyncClient, auth_headers: dict, created_event: dict
    ):
        """A user cannot update another user's booking — returns 404."""
        booking = await self._book(
            client, auth_headers, created_event["id"], idempotency_key="ownership-test"
        )
        headers_b = await _register_and_login(client, "userb@example.com")
        resp = await client.patch(
            f"/api/v1/bookings/{booking['id']}",
            json={"action": "confirmed"},
            headers=headers_b,
        )
        assert resp.status_code == 404

    async def test_update_nonexistent_booking_returns_404(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Patching a non-existent booking ID returns 404."""
        resp = await client.patch(
            "/api/v1/bookings/999999",
            json={"action": "confirmed"},
            headers=auth_headers,
        )
        assert resp.status_code == 404

    async def test_cancel_within_one_hour_returns_400(
        self, client: AsyncClient, auth_headers: dict, db_session
    ):
        """
        Cancelling within 1 hour of event start is rejected with 400.
        Event is written directly to db_session to bypass the Pydantic
        future-date validator (which would reject a 30-min-future starts_at).
        """
        from sqlalchemy import select
        from app.models.event import Event
        from app.models.user import User

        result = await db_session.execute(
            select(User).where(User.email == "test@example.com")
        )
        user = result.scalar_one()

        soon = datetime.now(timezone.utc) + timedelta(minutes=30)
        event = Event(
            title="Imminent Event",
            venue="Stage",
            starts_at=soon,
            total_seats=10,
            available_seats=10,
            ticket_price=100,
            created_by=user.id,
        )
        db_session.add(event)
        await db_session.flush()
        await db_session.refresh(event)

        booking_resp = await client.post(
            "/api/v1/bookings",
            json={"event_id": event.id, "idempotency_key": "cancel-window-test"},
            headers=auth_headers,
        )
        assert booking_resp.status_code == 201, booking_resp.text

        resp = await client.patch(
            f"/api/v1/bookings/{booking_resp.json()['id']}",
            json={"action": "cancelled"},
            headers=auth_headers,
        )
        assert resp.status_code == 400
        assert "1 hour" in resp.json()["detail"].lower()
