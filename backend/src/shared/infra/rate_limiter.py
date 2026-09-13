from typing import ClassVar

import logging
import random
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from fastapi import Request
from redis.asyncio import Redis
from redis.exceptions import RedisError
from starlette.applications import ASGIApp
from starlette.middleware.base import BaseHTTPMiddleware

from src.shared.domain.exceptions import RateLimitExceededError

logger = logging.getLogger(__name__)


# Lua скрипт реализующий алгоритм скользящего окна
SLIDING_WINDOW_LUA_SCRIPT = """
-- rate_limit.lua
local key = KEYS[1]
local now_ms = tonumber(ARGV[1])
local window_ms = tonumber(ARGV[2])
local limit = tonumber(ARGV[3])
local member = ARGV[4]

-- 1. Удаление записей старше окна
redis.call('ZREMRANGEBYSCORE', key, '-inf', now_ms - window_ms)

-- 2. Текущее количество запросов в окне
local current = redis.call('ZCARD', key)

-- 3. Проверка лимита
if current < limit then
    redis.call('ZADD', key, now_ms, member)
    current = current + 1
    redis.call('EXPIRE', key, math.ceil(window_ms / 1000) + 10)
    return {1, current}   -- {allowed, count_after_insert}
else
    redis.call('EXPIRE', key, math.ceil(window_ms / 1000) + 10)
    return {0, current}   -- {denied, count_before_insert}
end
"""

# Функции для идентификации запросов клиентов
type IdentifierFunc = Callable[[Request], Awaitable[str]]


async def ip_identifier(request: Request) -> str:  # noqa: RUF029
    """
    Идентификация клиента по IP адресу (учитывает X-Forwarded-For при наличии прокси).
    """

    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded is not None:
        return forwarded.split(",")[0].strip()

    return "unknown" if request.client.host is None else request.client.host


@dataclass
class RateLimitConfig:
    """Параметры для конфигурации Rate Limiter."""

    max_requests: int
    window_seconds: int
    identifier: IdentifierFunc | None = None


@dataclass
class RateLimitResult:
    """Результат проверки ограничителя запросов."""

    allowed: bool
    current: int
    remaining: int | None
    reset_at: float


class RateLimiter:
    def __init__(self, redis: Redis, prefix: str = "rate_limiter") -> None:
        self.redis = redis
        self.prefix = prefix
        self._script = self.redis.register_script(SLIDING_WINDOW_LUA_SCRIPT)

    async def check_limit(
            self, client_id: str, endpoint: str, max_requests, window_seconds: int
    ) -> RateLimitResult:
        key = f"{self.prefix}:{endpoint}:{client_id}"

        now_ms = time.time_ns() // 1_000_000
        window_ms = window_seconds * 1000
        member = f"{now_ms}_{random.getrandbits(32):08x}"

        try:
            allowed, current_count = await self._script(
                keys=[key], args=[now_ms, window_ms, max_requests, member]
            )
            remaining = max(0, max_requests - current_count)
            reset_at = (now_ms + window_ms) / 1000.0

            return RateLimitResult(
                allowed=bool(allowed),
                current=current_count,
                remaining=remaining,
                reset_at=reset_at,
            )
        except RedisError:
            logger.exception("Error occurred while redis_client rate limit check key")
            reset_at = (now_ms / 1000.0) + window_seconds
            return RateLimitResult(allowed=True, current=1, remaining=None, reset_at=reset_at)


class RateLimitMiddleware(BaseHTTPMiddleware):
    _registry: ClassVar[dict[tuple[str, str], RateLimitConfig]] = {}

    def __init__(
            self, app: ASGIApp, redis: Redis, fallback_identifier: IdentifierFunc = ip_identifier
    ) -> None:
        super().__init__(app)
        self.limiter = RateLimiter(redis)
        self.fallback_identifier = fallback_identifier

    @classmethod
    def register(cls, path: str, method: str, config: RateLimitConfig):
        """Настройка ограничителя для конкретного endpoint."""

        path = path.rstrip("/")
        cls._registry[path, method.upper()] = config

    async def dispatch(self, request: Request, call_next):
        path = request.url.path.rstrip("/")
        method = request.method
        config = self._registry.get((path, method))

        if config is None:
            return await call_next(request)

        identifier = config.identifier or self.fallback_identifier
        client_id = await identifier(request)

        result = await self.limiter.check_limit(
            client_id=client_id,
            endpoint=path,
            max_requests=config.max_requests,
            window_seconds=config.window_seconds
        )

        if not result.allowed:
            raise RateLimitExceededError(
                "Too many requests",
                details={
                    "Retry_after": "",
                    "X-RateLimit-Limit": f"{config.max_requests}",
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": f"{int(result.reset_at)}",
                },
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = f"{config.max_requests}"
        response.headers["X-RateLimit-Remaining"] = f"{result.remaining}"
        response.headers["X-RateLimit-Reset"] = f"{int(result.reset_at)}"

        return response
