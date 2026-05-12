from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.dependencies import get_current_user
from app.db import get_db
from app.models.user import User
from app.schemas.booking import (
    BookingCreateRequest,
    BookingResponse,
    BookingStatusUpdate,
)
from app.services.booking import BookingService


router = APIRouter(prefix="/bookings", tags=["Bookings"])


@router.post("", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
async def create_booking(
    payload: BookingCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BookingResponse:
    return await BookingService(
        db=db,
    ).create_booking(payload=payload, current_user=current_user)


@router.patch(
    "/{booking_id}", response_model=BookingResponse, status_code=status.HTTP_200_OK
)
async def update_booking_status(
    booking_id: int,
    payload: BookingStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BookingResponse:
    return await BookingService(db).update_booking_status(
        booking_id, payload, current_user
    )
