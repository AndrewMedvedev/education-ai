from langgraph.checkpoint.redis.aio import AsyncRedisSaver
from redis.asyncio import Redis

from .config import redis_config

__all__ = ["checkpointer", "redis_client"]

redis_client = Redis(  # ruff: ignore[non-empty-init-module]
    host=redis_config.host,
    port=redis_config.port,
    db=redis_config.db,
    password=redis_config.password,
    decode_responses=True,
)

checkpointer = AsyncRedisSaver(  # ruff: ignore[non-empty-init-module]
    redis_client=redis_client,
    ttl={
        "default_ttl": 60 * 10,  # Истекают контрольные точки через 5 часов
        "refresh_on_read": True,  # Сбросить время истечения срока действия при чтении контрольных точек  # ruff:ignore[line-too-long]
    },
)
