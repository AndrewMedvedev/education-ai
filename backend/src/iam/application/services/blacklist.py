from datetime import datetime

from src.shared.infra.cache import Cache
from src.shared.utils.time import current_datetime


def _build_cache_key(jti: str) -> str:
    return f"blacklist:{jti}"


async def revoke_token(jti: str, expires_at: datetime, cache: Cache[bool]) -> None:
    """Отзывает токен (записывает в кеш с ttl - оставшийся срок жизни токена)."""

    ttl = int((expires_at - current_datetime()).total_seconds())
    if ttl <= 0:
        return

    key = _build_cache_key(jti)
    await cache.set(key, True, ttl=ttl)


async def is_revoked(jti: str, cache: Cache[bool]) -> bool:
    """Поверяет отозван ли токен."""

    key = _build_cache_key(jti)
    return await cache.exists(key)
