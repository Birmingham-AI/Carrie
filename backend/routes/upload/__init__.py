"""Upload routes module - handles YouTube and PDF uploads."""
import os
from typing import Dict

from fastapi import APIRouter, Depends, Header, HTTPException

# Shared in-memory job tracking (for simplicity; use Redis/DB for production)
upload_jobs: Dict[str, Dict] = {}


def verify_api_key(x_api_key: str = Header(None)):
    """Verify the API key for protected endpoints."""
    expected_key = os.getenv("UPLOAD_API_KEY")
    if not expected_key:
        raise HTTPException(
            status_code=500,
            detail="UPLOAD_API_KEY not configured on server"
        )
    if not x_api_key or x_api_key != expected_key:
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing API key"
        )


# Create the main router
router = APIRouter(prefix="/api/upload", tags=["upload"])


@router.post("/verify-key", dependencies=[Depends(verify_api_key)])
async def verify_key():
    """
    Verify if the provided API key is valid.
    Returns 200 if valid, 401 if invalid.
    """
    return {"valid": True}


# Import and include sub-routers
from .youtube import router as youtube_router
from .pdf import router as pdf_router
from .sources import router as sources_router

router.include_router(youtube_router)
router.include_router(pdf_router)
router.include_router(sources_router)
