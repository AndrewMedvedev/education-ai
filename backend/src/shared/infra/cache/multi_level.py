import asyncio
import logging
import uuid

from .base import Cache

logger = logging.getLogger(__name__)


def build_key(prefix: str, uid: uuid.UUID) -> str:
    return f"{prefix}:{uid}"


class MultiLevelCache[T](Cache[T]):
    def __init__(self, l1_cache: Cache[T], l2_cache: Cache[T]) -> None:
        self.l1_cache = l1_cache
        self.l2_cache = l2_cache

    async def get(self, key: str) -> T | None:
        """В случае промаха L1, устанавливает значение в L1, если нашёлся в L2."""

        if (value := await self.l1_cache.get(key)) is not None:
            return value

        if (value := await self.l2_cache.get(key)) is not None:
            await self.l1_cache.set(key, value)
            return value

        return None

    async def set(self, key: str, value: T, ttl: int | None = None) -> None:
        """Параллельно пишет кеш в два слоя L1 и L2."""

        try:
            async with asyncio.TaskGroup() as tg:
                tg.create_task(self.l1_cache.set(key, value, ttl))
                tg.create_task(self.l2_cache.set(key, value, ttl))
        except ExceptionGroup as eg:
            for _ in eg.exceptions:
                logger.exception(
                    "Error occurred while set key - %s  in multi level cache", key,
                )

    async def delete(self, key: str) -> None:
        """Параллельно удаляет ключ из обоих уровней кэша."""

        try:
            async with asyncio.TaskGroup() as tg:
                tg.create_task(self.l1_cache.delete(key))
                tg.create_task(self.l2_cache.delete(key))
        except ExceptionGroup as eg:
            for _ in eg.exceptions:
                logger.exception(
                    "Error occurred while delete key %s from multi level cache", key,
                )

    async def exists(self, key: str) -> bool:
        """Вернёт True если хотя бы на одном из уровней будет попадание."""

        return await self.l1_cache.exists(key) or await self.l2_cache.exists(key)
