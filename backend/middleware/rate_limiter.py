import os
import time
from fastapi import Request, HTTPException

TRUST_PROXY = os.getenv("TRUST_PROXY", "false").lower() == "true"


def get_client_ip(request: Request) -> str:
    if TRUST_PROXY:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


class RateLimiter:
    """
    In-memory sliding window rate limiter.

    Note: With Cloud Run scaling, limits are per-instance, not global.
    Each instance maintains its own request counts.
    """

    def __init__(self, requests_per_minute: int = 15):
        self.requests_per_minute = requests_per_minute
        self.window_seconds = 60
        self.requests: dict[str, list[float]] = {}
        self.last_cleanup = time.time()

    def _cleanup_old_requests(self, client_ip: str, current_time: float) -> None:
        """Remove requests outside the sliding window."""
        if client_ip not in self.requests:
            return

        cutoff = current_time - self.window_seconds
        self.requests[client_ip] = [
            ts for ts in self.requests[client_ip] if ts > cutoff
        ]
        if not self.requests[client_ip]:
            del self.requests[client_ip]

    def _cleanup_stale_entries(self, current_time: float) -> None:
        """Periodically remove stale client entries from memory."""
        if current_time - self.last_cleanup < self.window_seconds:
            return

        cutoff = current_time - self.window_seconds
        for client_ip, timestamps in list(self.requests.items()):
            fresh = [ts for ts in timestamps if ts > cutoff]
            if fresh:
                self.requests[client_ip] = fresh
            else:
                del self.requests[client_ip]
        self.last_cleanup = current_time

    def check_rate_limit(self, request: Request) -> None:
        """
        Check if request is within rate limit.

        Raises:
            HTTPException: 429 if rate limit exceeded
        """
        client_ip = get_client_ip(request)
        current_time = time.time()

        self._cleanup_stale_entries(current_time)
        self._cleanup_old_requests(client_ip, current_time)

        client_requests = self.requests.setdefault(client_ip, [])

        if len(client_requests) >= self.requests_per_minute:
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded. Maximum {self.requests_per_minute} requests per minute.",
                headers={"Retry-After": "60"}
            )

        client_requests.append(current_time)


# Global rate limiter instance
rate_limiter = RateLimiter(requests_per_minute=15)
