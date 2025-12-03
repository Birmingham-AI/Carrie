import asyncio
import os
import uuid
import logging
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException, Header

from models import YouTubeUploadRequest, YouTubeUploadResponse, JobStatusResponse
from clients import get_supabase, check_supabase_configured
from actions.transcribe_youtube import YouTubeTranscriber

router = APIRouter(prefix="/api/youtube", tags=["youtube"])
logger = logging.getLogger(__name__)

# In-memory job tracking (for simplicity; use Redis/DB for production)
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


@router.post("/verify-key", dependencies=[Depends(verify_api_key)])
async def verify_key():
    """
    Verify if the provided API key is valid.
    Returns 200 if valid, 401 if invalid.
    """
    return {"valid": True}


async def process_youtube_upload(job_id: str, request: YouTubeUploadRequest):
    """Background task to process YouTube video and save to Supabase."""
    try:
        logger.info(f"[{job_id}] Starting YouTube upload for URL: {request.url}")

        # Extract video ID first
        video_id = YouTubeTranscriber.extract_video_id(request.url)
        if not video_id:
            logger.error(f"[{job_id}] Could not extract video ID from URL: {request.url}")
            upload_jobs[job_id] = {
                "status": "failed",
                "message": "Could not extract video ID from URL",
                "error": f"Invalid YouTube URL: {request.url}"
            }
            return

        logger.info(f"[{job_id}] Extracted video ID: {video_id}")
        upload_jobs[job_id]["video_id"] = video_id
        upload_jobs[job_id]["message"] = "Checking if video already exists..."

        # Connect to Supabase
        logger.debug(f"[{job_id}] Connecting to Supabase...")
        supabase = await get_supabase()

        # Check if already processed
        logger.debug(f"[{job_id}] Checking if video already exists in sources table...")
        existing = await supabase.table("sources").select("id").eq(
            "source_type", "youtube"
        ).eq("source_id", video_id).execute()
        logger.debug(f"[{job_id}] Existing check result: {existing.data}")

        if existing.data:
            logger.warning(f"[{job_id}] Video {video_id} already processed")
            upload_jobs[job_id] = {
                "status": "failed",
                "message": "Video already processed",
                "video_id": video_id,
                "error": f"Video {video_id} has already been transcribed and uploaded"
            }
            return

        upload_jobs[job_id]["message"] = "Fetching transcript and creating embeddings..."
        logger.info(f"[{job_id}] Fetching transcript and creating embeddings...")

        # Transcribe and embed
        transcriber = YouTubeTranscriber(
            chunk_size=request.chunk_size,
            overlap=request.overlap,
            language=request.language
        )
        chunks = await transcriber.transcribe(request.url, request.session_info, save_local=False)
        logger.info(f"[{job_id}] Transcription complete. Got {len(chunks)} chunks")

        upload_jobs[job_id]["message"] = "Saving to Supabase..."
        upload_jobs[job_id]["chunk_count"] = len(chunks)

        # Insert source record
        logger.debug(f"[{job_id}] Inserting source record...")
        source_data = {
            "source_type": "youtube",
            "source_id": video_id,
            "session_info": request.session_info,
            "chunk_count": len(chunks)
        }
        logger.debug(f"[{job_id}] Source data: {source_data}")
        source_result = await supabase.table("sources").insert(source_data).execute()
        logger.debug(f"[{job_id}] Source insert result: {source_result.data}")

        source_uuid = source_result.data[0]["id"]
        logger.info(f"[{job_id}] Source record created with ID: {source_uuid}")

        # Insert embeddings
        logger.info(f"[{job_id}] Inserting {len(chunks)} embeddings...")
        for i, chunk in enumerate(chunks):
            embedding_data = {
                "source_id": source_uuid,
                "text": chunk["text"],
                "timestamp": chunk["timestamp"],
                "embedding": chunk["embedding"]
            }
            logger.debug(f"[{job_id}] Inserting embedding {i+1}/{len(chunks)}")
            await supabase.table("embeddings").insert(embedding_data).execute()

        logger.info(f"[{job_id}] Successfully completed processing {len(chunks)} chunks")
        upload_jobs[job_id] = {
            "status": "completed",
            "message": f"Successfully processed {len(chunks)} chunks",
            "video_id": video_id,
            "chunk_count": len(chunks)
        }

    except Exception as e:
        logger.error(f"[{job_id}] Processing failed with error: {str(e)}", exc_info=True)
        upload_jobs[job_id] = {
            "status": "failed",
            "message": "Processing failed",
            "error": str(e)
        }


@router.post("/upload", response_model=YouTubeUploadResponse, dependencies=[Depends(verify_api_key)])
async def upload_youtube(request: YouTubeUploadRequest):
    """
    Upload a YouTube video for transcription and embedding.

    This endpoint starts a background job to:
    1. Fetch the YouTube transcript
    2. Create embeddings for the transcript chunks
    3. Save to Supabase

    Request body:
    - url: YouTube video URL or video ID
    - session_info: Description of the session (e.g., "Nov 2024 Birmingham AI Meetup")
    - chunk_size: Size of text chunks in characters (default: 1000)
    - overlap: Number of sentences to overlap between chunks (default: 1)
    - language: Language code for transcript (default: "en")

    Returns:
    - job_id: ID to track the job status
    - status: Current status ("processing")
    - message: Status message
    """
    check_supabase_configured()

    # Validate URL format
    video_id = YouTubeTranscriber.extract_video_id(request.url)
    if not video_id:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid YouTube URL: {request.url}"
        )

    # Generate job ID
    job_id = str(uuid.uuid4())

    # Initialize job status
    upload_jobs[job_id] = {
        "status": "processing",
        "message": "Starting transcription...",
        "video_id": video_id
    }

    # Start background processing as async task
    asyncio.create_task(process_youtube_upload(job_id, request))

    return YouTubeUploadResponse(
        job_id=job_id,
        status="processing",
        message="Transcription job started"
    )


@router.get("/status/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """
    Get the status of a YouTube upload job.

    Path parameters:
    - job_id: The job ID returned from /api/youtube/upload

    Returns:
    - job_id: The job ID
    - status: Current status ("processing", "completed", or "failed")
    - message: Status message
    - video_id: YouTube video ID (if available)
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
        video_id=job.get("video_id"),
        chunk_count=job.get("chunk_count"),
        error=job.get("error")
    )


@router.get("/sources")
async def list_youtube_sources():
    """
    List all YouTube sources that have been processed.

    Returns:
    - List of source records with video_id, session_info, and chunk_count
    """
    logger.debug("Fetching YouTube sources list...")
    check_supabase_configured()

    try:
        supabase = await get_supabase()
        logger.debug("Querying sources table...")
        result = await supabase.table("sources").select(
            "id, source_id, session_info, chunk_count, processed_at"
        ).eq("source_type", "youtube").order("processed_at", desc=True).execute()

        logger.info(f"Found {len(result.data)} YouTube sources")
        logger.debug(f"Sources data: {result.data}")
        return {"sources": result.data}
    except Exception as e:
        logger.error(f"Failed to fetch sources: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/sources/{source_id}", dependencies=[Depends(verify_api_key)])
async def delete_youtube_source(source_id: str):
    """
    Delete a YouTube source and its associated embeddings.

    Path parameters:
    - source_id: The UUID of the source record to delete

    Returns:
    - Success message with deleted counts
    """
    logger.debug(f"Deleting YouTube source: {source_id}")
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
