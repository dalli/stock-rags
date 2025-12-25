"""Redis connection and utilities."""

from typing import Any, Optional

import redis.asyncio as redis

from app.config import get_settings

settings = get_settings()


class RedisClient:
    """Redis client for caching operations."""

    def __init__(self) -> None:
        """Initialize Redis client."""
        self.client: Optional[redis.Redis] = None

    async def connect(self) -> None:
        """Connect to Redis."""
        self.client = redis.from_url(settings.redis_url, decode_responses=True)

    async def close(self) -> None:
        """Close Redis connection."""
        if self.client:
            await self.client.close()

    async def get(self, key: str) -> Optional[str]:
        """Get value by key."""
        if not self.client:
            await self.connect()
        return await self.client.get(key)

    async def set(self, key: str, value: Any, expire: Optional[int] = None) -> None:
        """Set value with optional expiration."""
        if not self.client:
            await self.connect()
        await self.client.set(key, value, ex=expire)

    async def delete(self, key: str) -> None:
        """Delete key."""
        if not self.client:
            await self.connect()
        await self.client.delete(key)

    async def check_health(self) -> bool:
        """Check Redis connection health."""
        try:
            if not self.client:
                await self.connect()
            await self.client.ping()
            return True
        except Exception:
            return False


# Global client instance
redis_client = RedisClient()


async def get_redis() -> RedisClient:
    """Get Redis client instance."""
    if not redis_client.client:
        await redis_client.connect()
    return redis_client
