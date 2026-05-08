from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING
from app.models.base import Base, TimestampMixin


if TYPE_CHECKING:
    from app.models.booking import Booking


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # One user can have many bookings.
    # lazy="noload" means SQLAlchemy will NEVER automatically load this list.
    # You must explicitly use selectinload() when you want bookings.
    # This prevents accidental N+1 queries — a lesson from P2.

    bookings: Mapped[list["Booking"]] = relationship(
        back_populates="user", lazy="noload"
    )
