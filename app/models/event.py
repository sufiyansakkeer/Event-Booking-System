from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING
from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.booking import Booking


class Event(Base, TimestampMixin):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    venue: Mapped[str] = mapped_column(String(255), nullable=False)

    # When the event actually happens — used to reject bookings for past events.
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Total seats available at creation time. Never changes after creation.
    total_seats: Mapped[int] = mapped_column(Integer, nullable=False)

    # version_id is the optimistic lock counter.
    # SQLAlchemy increments this automatically on every UPDATE.
    # If two transactions read version=5 and both try to update,
    # the first one wins (sets version=6), the second one finds
    # version=6 != 5 and raises StaleDataError.
    # In Dart terms: imagine a shared counter that acts as a mutex.
    version_id: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )  # for optimistic locking

    bookings: Mapped[list["Booking"]] = relationship(
        back_populates="event", lazy="noload"
    )

    # This tells SQLAlchemy WHICH column to use as the version counter
    # and HOW to increment it (version_id_generator=True means auto-increment).
    __mapper_args__ = {  # __mapper_args__ is the ORM mapper configuration
        "version_id_col": version_id,  # "version_id_col" is build-in sql alchemy
        "version_id_generator": True,  # this one is also build-in
    }
