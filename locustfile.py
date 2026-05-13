from locust import HttpUser, task, between
import uuid


class BookingUser(HttpUser):
    # Each simulated user waits 1-2 seconds between tasks.
    # This mimics real user behavior — not hammering every millisecond.
    wait_time = between(1, 2)

    # Locust calls on_start once per simulated user before running tasks.
    # We register and login here so every user has their own JWT token.
    def on_start(self):
        # Generate unique email per user so they don't conflict in DB.
        self.email = f"user_{uuid.uuid4().hex[:8]}@test.com"
        self.password = "password123"
        self.token: str | None = None
        self.event_id = 6  # assumes event with id=1 exists

        # Register
        self.client.post(
            "/api/v1/auth/register",
            json={
                "email": self.email,
                "password": self.password,
                "full_name": "Load Test User",
            },
        )

        # Login and store the token
        response = self.client.post(
            "/api/v1/auth/login",
            json={
                "email": self.email,
                "password": self.password,
            },
        )
        if response.status_code == 200:
            self.token = response.json().get("access_token")

    def auth_headers(self) -> dict[str, str]:
        # Helper that returns the Authorization header for protected endpoints.
        return {"Authorization": f"Bearer {self.token}"}

    @task(3)
    def list_events(self):
        # Weight 3 — this runs 3x more often than create_booking.
        # Simulates users browsing events more than booking them.
        # This also tests the Redis cache — most of these should be cache hits.
        self.client.get("/api/v1/events")

    @task(1)
    def create_booking(self):
        # Weight 1 — less frequent than browsing.
        # Each booking uses a unique idempotency key so they don't deduplicate.
        if not self.token:
            return

        self.client.post(
            "/api/v1/bookings",
            json={
                "event_id": self.event_id,
                "idempotency_key": uuid.uuid4().hex,
            },
            headers=self.auth_headers(),
        )

    @task(2)
    def get_single_event(self):
        # Weight 2 — viewing a specific event detail page.
        # Tests the per-event Redis cache.
        self.client.get(f"/api/v1/events/{self.event_id}")
