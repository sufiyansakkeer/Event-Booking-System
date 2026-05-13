"""
test_events.py — tests for /api/v1/events
"""

from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

FUTURE = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
PAST = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()


class TestCreateEvent:
    async def test_create_event_success(self, client: AsyncClient, auth_headers: dict):
        """Authenticated user can create a future event — returns 201 with full fields."""
        resp = await client.post(
            "/api/v1/events",
            json={
                "title": "Rock Night",
                "description": "Live rock music",
                "venue": "MG Road",
                "starts_at": FUTURE,
                "total_seats": 50,
                "ticket_price": "299.99",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["title"] == "Rock Night"
        assert body["venue"] == "MG Road"
        assert body["total_seats"] == 50
        # available_seats should equal total_seats at creation
        assert body["available_seats"] == 50
        assert "id" in body
        assert "created_at" in body

    async def test_create_event_unauthenticated_returns_403(self, client: AsyncClient):
        """No token → 401 (HTTPBearer rejects missing header)."""
        resp = await client.post(
            "/api/v1/events",
            json={
                "title": "X",
                "venue": "Y",
                "starts_at": FUTURE,
                "total_seats": 10,
                "ticket_price": "100",
            },
        )
        # HTTPBearer raises 401 when Authorization header is absent
        assert resp.status_code == 401

    async def test_create_event_past_date_returns_422(
        self, client: AsyncClient, auth_headers: dict
    ):
        """starts_at in the past fails the Pydantic field_validator — returns 422."""
        resp = await client.post(
            "/api/v1/events",
            json={
                "title": "Old Gig",
                "venue": "Somewhere",
                "starts_at": PAST,
                "total_seats": 10,
                "ticket_price": "100",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 422

    async def test_create_event_zero_seats_returns_422(
        self, client: AsyncClient, auth_headers: dict
    ):
        """total_seats=0 fails Field(gt=0) validation — returns 422."""
        resp = await client.post(
            "/api/v1/events",
            json={
                "title": "Empty Venue",
                "venue": "Nowhere",
                "starts_at": FUTURE,
                "total_seats": 0,
                "ticket_price": "100",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 422

    async def test_create_event_missing_required_field_returns_422(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Missing venue returns 422."""
        resp = await client.post(
            "/api/v1/events",
            json={
                "title": "No Venue",
                "starts_at": FUTURE,
                "total_seats": 10,
                "ticket_price": "100",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 422


class TestListEvents:
    async def test_list_events_returns_200(
        self, client: AsyncClient, created_event: dict
    ):
        """GET /events returns 200 with a list containing at least the created event."""
        resp = await client.get("/api/v1/events")
        assert resp.status_code == 200
        body = resp.json()
        assert isinstance(body, list)
        ids = [e["id"] for e in body]
        assert created_event["id"] in ids

    async def test_list_events_no_auth_required(self, client: AsyncClient):
        """Listing events is public — no token needed."""
        resp = await client.get("/api/v1/events")
        assert resp.status_code == 200

    async def test_list_events_pagination(
        self, client: AsyncClient, auth_headers: dict
    ):
        """skip and limit query params are respected."""
        # Create 3 events
        for i in range(3):
            await client.post(
                "/api/v1/events",
                json={
                    "title": f"Event {i}",
                    "venue": "Hall",
                    "starts_at": FUTURE,
                    "total_seats": 10,
                    "ticket_price": "100",
                },
                headers=auth_headers,
            )

        resp = await client.get("/api/v1/events?skip=0&limit=2")
        assert resp.status_code == 200
        assert len(resp.json()) <= 2


class TestGetEvent:
    async def test_get_event_by_id_success(
        self, client: AsyncClient, created_event: dict
    ):
        """GET /events/{id} returns the correct event."""
        event_id = created_event["id"]
        resp = await client.get(f"/api/v1/events/{event_id}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == event_id
        assert body["title"] == created_event["title"]

    async def test_get_event_not_found_returns_404(self, client: AsyncClient):
        """Non-existent event ID returns 404."""
        resp = await client.get("/api/v1/events/999999")
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()
