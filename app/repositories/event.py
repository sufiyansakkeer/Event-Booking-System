from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Event


class EventRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all(
        self,
        skip: int = 0,
        limit: int = 10,
    ) -> list[Event]:
        result = await self.db.execute(
            select(Event).offset(skip).limit(limit),
        )
        return list(result.scalars().all())

    async def get_by_id(self, event_id: int) -> None | Event:
        result = await self.db.execute(select(Event).where(Event.id == event_id))
        return result.scalar_one_or_none()

    async def create(self, event: Event) -> Event:
        self.db.add(event)
        await self.db.flush()
        await self.db.refresh(event)
        return event
