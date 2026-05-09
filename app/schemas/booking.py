from pydantic import BaseModel


class BookingCreateRequest(BaseModel):
    event_id: int
    notes: str | None = None
    # Client generates this UUID before sending the request.
    # If the request fails and they retry, the same key prevents double booking.
    # Think of it like a Dio request ID you'd use to deduplicate retries.
    idempotency_key: str | None = None


class BookingResponse(BaseModel):
    id: int
    event_id: int
    user_id: int
    notes: str | None = None
    idempotency_key: str | None

    model_config = {"from_attributes": True}


class BookingStatusUpdate(BaseModel):
    # Used when confirming or cancelling a booking.
    # valid values: "confirmed"| "cancelled"
    action: str
