from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, field_validator


class EventCreateRequest(BaseModel):
    title: str
    description: str | None = None
    venue: str
    starts_at: datetime
    total_seats: int
    ticket_price: Decimal

    @field_validator("starts_at")
    @classmethod
    def must_be_future(cls, v: datetime) -> datetime:
        if v <= datetime.now(tz=v.tzinfo):
            raise ValueError("Start time must be in the future.")
        return v


class EventResponse(BaseModel):
    id: int
    title: str
    description: str | None = None
    venue: str
    starts_at: datetime
    total_seats: int
    available_seats: int
    ticket_price: Decimal
    created_at: datetime

    model_config = {"from_attributes": True}
