from fastapi import Depends, Request

from src.core.redis import redis_client
from src.shared.domain.exceptions import RateLimitExceededError
from src.shared.infra.rate_limiter import IdentifierFunc, RateLimiter, ip_identifier

rate_limiter = RateLimiter(redis_client)


def get_rate_limiter() -> RateLimiter:
    return rate_limiter


def create_rate_limiter(
    max_requests: int, window_seconds: int, identifier: IdentifierFunc = ip_identifier
):
    """Создание зависимости для проверки лимита запросов."""

    async def dependency(request: Request, limiter: RateLimiter = Depends(get_rate_limiter)):
        client_id = await identifier(request)
        endpoint = request.url.path

        result = await limiter.check_limit(
            client_id=client_id,
            endpoint=endpoint,
            max_requests=max_requests,
            window_seconds=window_seconds,
        )

        if not result.allowed:
            raise RateLimitExceededError(
                "Too many requests",
                details={
                    "Retry_after": "",
                    "X-RateLimit-Limit": f"{max_requests}",
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": f"{int(result.reset_at)}",
                },
            )

        return result

    return dependency
