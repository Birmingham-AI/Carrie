"""PDF upload routes."""
import asyncio
import uuid
import logging

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form

from models import UploadResponse
from clients import get_supabase, check_supabase_configured
from actions.process_slides import SlideProcessor
from . import upload_jobs, verify_api_key

router = APIRouter()
logger = logging.getLogger(__name__)


async def process_pdf_upload(job_id: str, pdf_bytes: bytes, filename: str, session_info: str):
    """Background task to process PDF slides and save to Supabase one page at a time."""
    try:
        logger.info(f"[{job_id}] Starting PDF upload for file: {filename}")

        upload_jobs[job_id]["message"] = "Checking if PDF already exists..."

        # Connect to Supabase
        supabase = await get_supabase()

        # Check if already processed (using filename as source_id)
        existing = await supabase.table("sources").select("id").eq(
            "source_type", "pdf"
        ).eq("source_id", filename).execute()

        if existing.data:
            logger.warning(f"[{job_id}] PDF {filename} already processed")
            upload_jobs[job_id] = {
                "status": "failed",
                "message": "PDF already processed",
                "source_id": filename,
                "error": f"PDF {filename} has already been processed and uploaded"
            }
            return

        # Insert source record first (we'll update chunk_count at the end)
        source_data = {
            "source_type": "pdf",
            "source_id": filename,
            "session_info": session_info,
            "chunk_count": 0
        }
        source_result = await supabase.table("sources").insert(source_data).execute()
        source_uuid = source_result.data[0]["id"]
        logger.info(f"[{job_id}] Source record created with ID: {source_uuid}")

        # Process PDF page by page and insert each embedding immediately
        processor = SlideProcessor()
        chunk_count = 0

        async for chunk in processor.stream_from_bytes(pdf_bytes, filename, session_info):
            # Update job status with progress
            upload_jobs[job_id]["message"] = f"Processing slide {chunk['page_num']}/{chunk['total_pages']}..."

            # Insert embedding immediately
            embedding_data = {
                "source_id": source_uuid,
                "text": chunk["text"],
                "timestamp": chunk["timestamp"],
                "embedding": chunk["embedding"]
            }
            await supabase.table("embeddings").insert(embedding_data).execute()
            chunk_count += 1
            upload_jobs[job_id]["chunk_count"] = chunk_count

        # Update source record with final chunk count
        await supabase.table("sources").update({"chunk_count": chunk_count}).eq("id", source_uuid).execute()

        logger.info(f"[{job_id}] Successfully completed processing {chunk_count} slides")
        upload_jobs[job_id] = {
            "status": "completed",
            "message": f"Successfully processed {chunk_count} slides",
            "source_id": filename,
            "chunk_count": chunk_count
        }

    except Exception as e:
        logger.error(f"[{job_id}] Processing failed with error: {str(e)}", exc_info=True)
        upload_jobs[job_id] = {
            "status": "failed",
            "message": "Processing failed",
            "error": str(e)
        }


@router.post("/pdf", response_model=UploadResponse, dependencies=[Depends(verify_api_key)])
async def upload_pdf(
    file: UploadFile = File(...),
    session_info: str = Form(...)
):
    """
    Upload a PDF file for slide processing and embedding.

    This endpoint starts a background job to:
    1. Extract text from PDF slides
    2. Analyze slides using AI
    3. Create embeddings for each slide
    4. Save to Supabase

    Form data:
    - file: PDF file to upload
    - session_info: Description of the session (e.g., "Nov 2024 Birmingham AI Meetup")

    Returns:
    - job_id: ID to track the job status
    - status: Current status ("processing")
    - message: Status message
    """
    check_supabase_configured()

    # Validate file type
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="File must be a PDF"
        )

    # Read file into memory
    pdf_bytes = await file.read()

    if len(pdf_bytes) == 0:
        raise HTTPException(
            status_code=400,
            detail="Empty file uploaded"
        )

    # Generate job ID
    job_id = str(uuid.uuid4())

    # Initialize job status
    upload_jobs[job_id] = {
        "status": "processing",
        "message": "Starting PDF processing...",
        "source_id": file.filename,
        "source_type": "pdf"
    }

    # Start background processing as async task
    asyncio.create_task(process_pdf_upload(job_id, pdf_bytes, file.filename, session_info))

    return UploadResponse(
        job_id=job_id,
        status="processing",
        message="PDF processing job started"
    )
