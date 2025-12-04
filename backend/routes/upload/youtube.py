"""YouTube upload routes."""
import asyncio
import uuid
import logging

from fastapi import APIRouter, Depends, HTTPException

from models import YouTubeUploadRequest, UploadResponse
from clients import get_supabase, check_supabase_configured
from actions.transcribe_youtube import YouTubeTranscriber
from . import upload_jobs, verify_api_key

router = APIRouter()
logger = logging.getLogger(__name__)


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
        upload_jobs[job_id]["source_id"] = video_id
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
                "source_id": video_id,
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
            "source_id": video_id,
            "chunk_count": len(chunks)
        }

    except Exception as e:
        logger.error(f"[{job_id}] Processing failed with error: {str(e)}", exc_info=True)
        upload_jobs[job_id] = {
            "status": "failed",
            "message": "Processing failed",
            "error": str(e)
        }


@router.post("/youtube", response_model=UploadResponse, dependencies=[Depends(verify_api_key)])
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
        "source_id": video_id,
        "source_type": "youtube"
    }

    # Start background processing as async task
    asyncio.create_task(process_youtube_upload(job_id, request))

    return UploadResponse(
        job_id=job_id,
        status="processing",
        message="Transcription job started"
    )
