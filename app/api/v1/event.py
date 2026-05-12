from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.dependencies import get_current_user
from app.db import get_db
from app.models.user import User
from app.schemas.event import EventCreateRequest, EventResponse
from app.services.event import EventService


router = APIRouter(prefix="/events", tags=["Events"])


@router.post("", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
async def create_event(
    payload: EventCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EventResponse:
    return await EventService(db=db).create_event(payload=payload)


@router.get(
    "",
    response_model=list[EventResponse],
)
async def list_events(
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[EventResponse]:
    return await EventService(db=db).get_all_events(skip, limit)


@router.get("/{event_id}", response_model=EventResponse)
async def get_event(event_id: int, db: AsyncSession = Depends(get_db)) -> EventResponse:
    return await EventService(db=db).get_event(event_id)
