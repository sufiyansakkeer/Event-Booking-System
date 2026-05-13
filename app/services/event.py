from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from app.models.event import Event
from app.models.user import User
from app.repositories.event import EventRepository
from app.schemas.event import EventCreateRequest, EventResponse


class EventService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.event_repo = EventRepository(db=db)

    async def create_event(
        self, payload: EventCreateRequest, current_user: User
    ) -> EventResponse:
        event = Event(
            title=payload.title,
            description=payload.description,
            venue=payload.venue,
            starts_at=payload.starts_at,
            total_seats=payload.total_seats,
            # available_seats starts equal to total_seats at creation.
            # It decreases as bookings are made.
            available_seats=payload.total_seats,
            ticket_price=payload.ticket_price,
            created_by=current_user.id,
        )
        created_event = await self.event_repo.create(event)
        await self.db.commit()
        await self.db.refresh(created_event)
        return EventResponse.model_validate(created_event)

    async def get_all_events(
        self, skip: int = 0, limit: int = 10
    ) -> list[EventResponse]:
        results = await self.event_repo.get_all(skip, limit)
        return [EventResponse.model_validate(event) for event in results]

    async def get_event(self, event_id: int) -> EventResponse:
        event = await self.event_repo.get_by_id(event_id)
        if not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Event with id {event_id} not found",
            )
        return EventResponse.model_validate(event)
