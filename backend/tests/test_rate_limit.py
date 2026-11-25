import pytest
from fastapi import HTTPException

from app.core.rate_limit import SlidingWindowRateLimiter


@pytest.mark.asyncio
async def test_rate_limiter_allows_within_limit_and_blocks_excess():
    limiter = SlidingWindowRateLimiter(max_requests=3, window_seconds=60)
    await limiter.check("login:10.0.0.1")
    await limiter.check("login:10.0.0.1")
    await limiter.check("login:10.0.0.1")

    with pytest.raises(HTTPException) as exc:
        await limiter.check("login:10.0.0.1")
    assert exc.value.status_code == 429
    assert int(exc.value.headers["Retry-After"]) >= 1

    # Outro IP não deve ser afetado
    await limiter.check("login:10.0.0.2")
