from typing import Protocol

import logging
import uuid

from redis.asyncio import Redis

from .base import Cache

logger = logging.getLogger(__name__)

_TRUE_STRINGS = ("true", "1")


def build_key(prefix: str, uid: uuid.UUID) -> str:
    return f"{prefix}:{uid}"


class Serializer[T](Protocol):

    def dumps(self, value: T) -> bytes: ...

    def loads(self, value: bytes) -> T: ...


class PrimitiveSerializer[T]:
    def __init__(self, cast_type: type[T]) -> None:
        self._cast_type = cast_type

    def dumps(self, value: T) -> bytes:
        if isinstance(value, bytes):
            return value

        return str(value).encode("utf-8")

    def loads(self, value: bytes) -> T:
        if self._cast_type is bytes:
            return value

        value_str = value.decode("utf-8")

        if self._cast_type is bool:
            return value_str.lower() in _TRUE_STRINGS

        return self._cast_type(value_str)


class RedisCache[T](Cache[T]):

    def __init__(
            self,
            redis: Redis,
            serializer: Serializer[T],
            ttl: int | None = None
    ) -> None:
        self.redis = redis
        self.serializer = serializer
        self.ttl = ttl

    async def get(self, key: str) -> T | None:
        if (raw := await self.redis.get(key)) is None:
            return None

        return self.serializer.loads(raw)

    async def set(self, key: str, value: T, ttl: int | None = None) -> None:
        raw = self.serializer.dumps(value)

        effective_ttl = ttl if ttl is not None else self.ttl

        await self.redis.set(key, raw, ex=effective_ttl)

    async def delete(self, key: str) -> None:
        await self.redis.delete(key)

    async def exists(self, key: str) -> bool:
        result = await self.redis.exists(key)
        return result > 0
