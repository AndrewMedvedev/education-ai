import pytest

from src.shared.infra.rate_limiter import RateLimiter


@pytest.mark.asyncio
async def test_rate_limiter_blocks_request_above_sliding_window_limit(redis_client):
    """Блокирует запрос, который превышает лимит в скользящем окне."""
    limiter = RateLimiter(redis_client)

    first = await limiter.check_limit("student", "/courses", max_requests=2, window_seconds=60)
    second = await limiter.check_limit("student", "/courses", max_requests=2, window_seconds=60)
    third = await limiter.check_limit("student", "/courses", max_requests=2, window_seconds=60)

    assert first.allowed is True
    assert second.allowed is True
    assert third.allowed is False
