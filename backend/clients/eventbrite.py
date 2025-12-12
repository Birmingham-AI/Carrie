from os import getenv
import httpx

EVENTBRITE_BASE_URL = "https://www.eventbriteapi.com/v3"

# Shared async httpx client (lazy initialized)
_httpx_client: httpx.AsyncClient | None = None


def get_api_token() -> str | None:
    """Get the Eventbrite API token (read fresh each time)"""
    return getenv("EVENTBRITE_API_TOKEN")


def get_org_id() -> str | None:
    """Get the Eventbrite organization ID"""
    return getenv("EVENTBRITE_ORG_ID")


def get_eventbrite_client() -> httpx.AsyncClient:
    """Get or create async httpx client for Eventbrite API"""
    global _httpx_client
    if _httpx_client is None:
        _httpx_client = httpx.AsyncClient(
            base_url=EVENTBRITE_BASE_URL,
            timeout=30.0,
        )
    return _httpx_client


def is_configured() -> bool:
    """Check if Eventbrite credentials are configured"""
    return bool(get_api_token() and get_org_id())
