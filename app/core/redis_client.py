import redis.asyncio as aioredis  # Uses async Redis client for non-blocking I/O operations

from app.core.config import get_settings

settings = get_settings()

redis_client: aioredis.Redis = aioredis.from_url(  # type: ignore
    settings.REDIS_URL,
    encoding="utf-8",
    decode_responses=True,  # returns str instead of bytes
)
