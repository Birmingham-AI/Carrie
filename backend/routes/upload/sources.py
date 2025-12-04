"""Shared source management routes."""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from models import JobStatusResponse
from clients import get_supabase, check_supabase_configured
from . import upload_jobs, verify_api_key

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/status/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """
    Get the status of an upload job (YouTube or PDF).

    Path parameters:
    - job_id: The job ID returned from upload endpoint

    Returns:
    - job_id: The job ID
    - status: Current status ("processing", "completed", or "failed")
    - message: Status message
    - video_id: YouTube video ID or PDF filename (if available)
    - chunk_count: Number of chunks processed (if completed)
    - error: Error message (if failed)
    """
    if job_id not in upload_jobs:
        raise HTTPException(
            status_code=404,
            detail=f"Job not found: {job_id}"
        )

    job = upload_jobs[job_id]
    return JobStatusResponse(
        job_id=job_id,
        status=job.get("status", "unknown"),
        message=job.get("message", ""),
        video_id=job.get("source_id"),  # Keep as video_id for API compatibility
        chunk_count=job.get("chunk_count"),
        error=job.get("error")
    )


@router.get("/sources")
async def list_sources(source_type: Optional[str] = Query(None, description="Filter by source type: youtube or pdf")):
    """
    List all sources that have been processed.

    Query parameters:
    - source_type: Optional filter by type ("youtube" or "pdf")

    Returns:
    - List of source records with source_id, session_info, and chunk_count
    """
    logger.debug("Fetching sources list...")
    check_supabase_configured()

    try:
        supabase = await get_supabase()
        query = supabase.table("sources").select(
            "id, source_type, source_id, session_info, chunk_count, processed_at"
        )

        if source_type:
            query = query.eq("source_type", source_type)

        result = await query.order("processed_at", desc=True).execute()

        logger.info(f"Found {len(result.data)} sources")
        return {"sources": result.data}
    except Exception as e:
        logger.error(f"Failed to fetch sources: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/sources/{source_id}", dependencies=[Depends(verify_api_key)])
async def delete_source(source_id: str):
    """
    Delete a source and its associated embeddings.

    Path parameters:
    - source_id: The UUID of the source record to delete

    Returns:
    - Success message with deleted counts
    """
    logger.debug(f"Deleting source: {source_id}")
    check_supabase_configured()

    try:
        supabase = await get_supabase()

        # First delete associated embeddings (foreign key constraint)
        embeddings_result = await supabase.table("embeddings").delete().eq(
            "source_id", source_id
        ).execute()
        embeddings_deleted = len(embeddings_result.data) if embeddings_result.data else 0

        # Then delete the source record
        source_result = await supabase.table("sources").delete().eq(
            "id", source_id
        ).execute()

        if not source_result.data:
            raise HTTPException(
                status_code=404,
                detail=f"Source not found: {source_id}"
            )

        logger.info(f"Deleted source {source_id} and {embeddings_deleted} embeddings")
        return {
            "message": "Source deleted successfully",
            "source_id": source_id,
            "embeddings_deleted": embeddings_deleted
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete source: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
