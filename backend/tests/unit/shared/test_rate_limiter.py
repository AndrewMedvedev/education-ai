from unittest.mock import AsyncMock, Mock

import pytest
from redis.exceptions import RedisError

from src.shared.infra.rate_limiter import RateLimiter


@pytest.mark.asyncio
async def test_rate_limiter_allows_request_when_redis_is_unavailable():
    """Разрешает запрос, когда Redis недоступен."""
    redis = Mock()
    redis.register_script.return_value = AsyncMock(side_effect=RedisError("Redis is unavailable"))
    limiter = RateLimiter(redis)

    result = await limiter.check_limit(
        client_id="student",
        endpoint="/courses",
        max_requests=2,
        window_seconds=60,
    )

    assert result.allowed is True
    assert result.current == 1
    assert result.remaining is None
