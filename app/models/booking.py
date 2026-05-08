from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING
from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.event import Event


class Booking(Base, TimestampMixin):
    __tablename__ = "bookings"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id"), nullable=False)

    # The state machine will control what values go here.
    # Valid values: "reserved" | "confirmed" | "cancelled"
    # Starts as "reserved" when a booking is first created.
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="reserved")

    # Idempotency key — a unique string the client sends with the request.
    # If the same key comes in twice, we return the existing booking
    # instead of creating a duplicate. Prevents double-booking on network retry.
    # Like a request deduplication ID — similar to how you'd handle
    # duplicate Dio retries on the Flutter side.
    idempotency_key: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True, index=True
    )

    notes: Mapped[str] = mapped_column(Text, nullable=True)

    # Relationships to User and Event models.
    user: Mapped["User"] = relationship(back_populates="bookings", lazy="noload")
    event: Mapped["Event"] = relationship(back_populates="bookings", lazy="noload")
