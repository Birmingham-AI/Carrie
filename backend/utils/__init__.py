import os

from fastapi import Request

TRUST_PROXY = os.getenv("TRUST_PROXY", "false").lower() == "true"


def get_client_ip(request: Request) -> str:
    if TRUST_PROXY:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"

__all__ = ["get_client_ip"]
