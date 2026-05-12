from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.booking import Booking
from app.models.event import Event
from app.models.user import User


class BookingRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, booking_id: int) -> Booking | None:
        result = await self.db.execute(select(Booking).where(Booking.id == booking_id))
        return result.scalar_one_or_none()

    async def get_by_idempotency_key(self, key: str) -> Booking | None:
        result = await self.db.execute(
            select(Booking).where(Booking.idempotency_key == key)
        )
        return result.scalar_one_or_none()

    async def get_user_bookings_for_event(
        self, user_id: int, event_id: int
    ) -> list[Booking]:
        result = await self.db.execute(
            select(Booking).where(
                User.id == user_id, Event.id == event_id, Booking.status != "cancelled"
            )
        )
        return list(result.scalars().all())

    async def create(self, booking: Booking) -> Booking:
        self.db.add(booking)
        await self.db.flush()
        await self.db.refresh(booking)
        return booking
