from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.exc import StaleDataError
from transitions import MachineError
from app.core.booking_state_machine import BookingStateMachine
from app.core.redis_client import redis_client  # type: ignore
from app.models.booking import Booking
from app.models.user import User
from app.repositories.booking import BookingRepository
from app.repositories.event import EventRepository
from app.schemas.booking import (
    BookingCreateRequest,
    BookingResponse,
    BookingStatusUpdate,
)
from app.tasks.email_tasks import send_booking_confirmation_email


class BookingService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.booking_repo = BookingRepository(db)
        self.event_repo = EventRepository(db)

    async def create_booking(
        self, payload: BookingCreateRequest, current_user: User
    ) -> BookingResponse:

        # ── IDEMPOTENCY CHECK via Redis ────────────────────────────────
        # SET NX = set only if key does not exist. Atomic operation.
        # First request  → key absent  → SET NX succeeds → process booking.
        # Retry request  → key present → SET NX fails    → return existing.
        # This is like checking a cache before doing expensive work in Flutter.
        if payload.idempotency_key:
            redis_key = f"idempotency:{payload.idempotency_key}"
            was_set = await redis_client.set(
                redis_key,
                "pending",
                nx=True,  # only set if not already present
                ex=86400,  # auto-delete after 24 hours
            )
            if not was_set:
                # Key already exists. Check if it's "pending" or "done".
                # Duplicate request — return existing booking from Postgres.
                existing = await self.booking_repo.get_by_idempotency_key(
                    payload.idempotency_key
                )
                if existing:
                    return BookingResponse.model_validate(existing)

        # Event check
        event = await self.event_repo.get_by_id(event_id=payload.event_id)
        if not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Event not found",
            )

        if event.starts_at <= datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot book past or ongoing events",
            )

        # Business rule - 5 booking per user

        user_bookings = await self.booking_repo.get_user_bookings_for_event(
            user_id=current_user.id, event_id=payload.event_id
        )
        if len(user_bookings) >= 5:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Booking limit exceeded for this event",
            )

        # ── BUSINESS RULE: seats available ────────────────────────────
        if event.available_seats <= 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="No seats available",
            )
        # ── OPTIMISTIC LOCKING + BOOKING CREATION ─────────────────────
        # We decrement available_seats and create the booking inside one
        # try block. If another request already changed this event row
        # between our read and our write, SQLAlchemy detects the
        # version_id mismatch and raises StaleDataError.
        # We catch it, rollback everything, and tell the client to retry.
        try:
            event.available_seats -= 1

            booking = Booking(
                user_id=current_user.id,
                event_id=payload.event_id,
                status="reserved",
                notes=payload.notes,
                idempotency_key=payload.idempotency_key,
            )
            # Repo: add + flush + refresh — gets booking.id from DB.
            booking = await self.booking_repo.create(booking=booking)

            await self.db.commit()
            await self.db.refresh(booking)

            # Now that booking.id exists, update Redis key with the real ID.
            # Future retries can use this to find the booking in Postgres.
            if payload.idempotency_key:
                await redis_client.set(
                    f"idempotency:{payload.idempotency_key}",
                    str(booking.id),
                    ex=86400,
                )
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            ) from e
        except StaleDataError as e:
            # Another request won the race — undo everything.
            await self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Booking conflict — please try again",
            ) from e

        # ── BACKGROUND TASK ────────────────────────────────────────────
        # .delay() drops a message in Redis and returns immediately.
        # The Celery worker picks it up and runs the email task separately.
        # The HTTP response is already on its way to the client by the time
        # the email is actually sent.
        send_booking_confirmation_email.delay(
            user_email=current_user.email,
            event_name=event.title,
            booking_id=booking.id,
        )

        return BookingResponse.model_validate(booking)

    async def update_booking_status(
        self,
        booking_id: int,
        payload: BookingStatusUpdate,
        current_user: User,
    ) -> BookingResponse:
        booking = await self.booking_repo.get_by_id(booking_id=booking_id)
        if not booking or booking.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Booking not found",
            )

        # ── CANCELLATION WINDOW ────────────────────────────────────────
        # Check this BEFORE the state machine so the error message is clear.
        # If cancelling within 1 hour of event start, reject.
        if payload.action == "cancelled":
            event = await self.event_repo.get_by_id(booking.event_id)
            if event:
                time_until_event = event.starts_at - datetime.now(timezone.utc)
                if time_until_event.total_seconds() < 3600:  # 1 hour = 3600 seconds
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Cannot cancel booking within 1 hour of event start",
                    )

                # seat goes back to the event pool
                event.available_seats += 1

        # ── STATE MACHINE ──────────────────────────────────────────────
        # Rehydrate the machine with the booking's current persisted state.
        # Then attempt the requested transition.
        # MachineError = invalid transition (e.g. cancelled → confirmed).
        try:
            machine = BookingStateMachine(current_state=booking.status)
            new_state = machine.apply(payload.action)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            ) from e
        except MachineError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot {payload.action} booking from {booking.status} state",
            ) from e

        booking.status = new_state
        await self.db.commit()
        await self.db.refresh(booking)
        return BookingResponse.model_validate(booking)
