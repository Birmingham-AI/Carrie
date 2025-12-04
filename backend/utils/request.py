from fastapi import Request


def get_client_ip(request: Request) -> str:
    """
    Extract the real client IP from a request.

    Checks X-Forwarded-For header first (for requests behind proxies/load balancers),
    then falls back to the direct client host.

    Args:
        request: FastAPI Request object

    Returns:
        Client IP address string, or "unknown" if not available
    """
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        # X-Forwarded-For can contain multiple IPs: client, proxy1, proxy2, ...
        # The first one is the original client IP
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"
