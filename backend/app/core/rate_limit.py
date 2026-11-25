"""Limitador de taxa (rate limiting) em memória com janela deslizante por IP."""
import asyncio
import math
import time
from collections import defaultdict, deque
from typing import Callable, Deque, Dict

from fastapi import HTTPException, Request, status

from app.core.security import get_client_ip


class SlidingWindowRateLimiter:
    """Controla o número máximo de requisições por chave dentro de uma janela de tempo."""

    def __init__(self, max_requests: int, window_seconds: int) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._hits: Dict[str, Deque[float]] = defaultdict(deque)
        self._lock = asyncio.Lock()

    async def check(self, key: str) -> None:
        """Registra uma tentativa para `key` e levanta HTTP 429 se o limite for excedido."""
        now = time.monotonic()
        cutoff = now - self.window_seconds
        async with self._lock:
            bucket = self._hits[key]
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()
            if len(bucket) >= self.max_requests:
                retry_after = max(1, math.ceil(self.window_seconds - (now - bucket[0])))
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Muitas tentativas em sequência. Aguarde alguns instantes e tente novamente.",
                    headers={"Retry-After": str(retry_after)},
                )
            bucket.append(now)


def rate_limit(scope: str, max_requests: int, window_seconds: int) -> Callable:
    """Cria uma dependência FastAPI que limita requisições por IP para o escopo informado."""
    limiter = SlidingWindowRateLimiter(max_requests=max_requests, window_seconds=window_seconds)

    async def _dependency(request: Request) -> None:
        client_ip = get_client_ip(request)
        await limiter.check(f"{scope}:{client_ip}")

    return _dependency
