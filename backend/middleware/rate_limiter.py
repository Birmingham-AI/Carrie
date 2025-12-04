import time
from collections import defaultdict
from fastapi import Request, HTTPException

from utils import get_client_ip


class RateLimiter:
    """
    In-memory sliding window rate limiter.

    Note: With Cloud Run scaling, limits are per-instance, not global.
    Each instance maintains its own request counts.
    """

    def __init__(self, requests_per_minute: int = 15):
        self.requests_per_minute = requests_per_minute
        self.window_seconds = 60
        self.requests: dict[str, list[float]] = defaultdict(list)

    def _cleanup_old_requests(self, client_ip: str, current_time: float) -> None:
        """Remove requests outside the sliding window."""
        cutoff = current_time - self.window_seconds
        self.requests[client_ip] = [
            ts for ts in self.requests[client_ip] if ts > cutoff
        ]

    def check_rate_limit(self, request: Request) -> None:
        """
        Check if request is within rate limit.

        Raises:
            HTTPException: 429 if rate limit exceeded
        """
        client_ip = get_client_ip(request)
        current_time = time.time()

        self._cleanup_old_requests(client_ip, current_time)

        if len(self.requests[client_ip]) >= self.requests_per_minute:
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded. Maximum {self.requests_per_minute} requests per minute.",
                headers={"Retry-After": "60"}
            )

        self.requests[client_ip].append(current_time)


# Global rate limiter instance
rate_limiter = RateLimiter(requests_per_minute=15)
