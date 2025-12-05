import logging
from fastapi import APIRouter, HTTPException

from models import FeedbackRequest, FeedbackResponse
from services.langfuse_tracing import get_langfuse_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["feedback"])


@router.post("/feedback", response_model=FeedbackResponse)
async def submit_feedback(feedback: FeedbackRequest):
    """
    Submit feedback (like/dislike) for a response.

    This endpoint records user feedback to Langfuse for tracking response quality.

    Request body:
    - trace_id: The trace ID of the response being rated
    - rating: 'like' or 'dislike'
    - comment: Optional comment explaining the rating

    Returns:
    - success: Whether feedback was recorded
    - message: Status message
    """
    if feedback.rating not in ('like', 'dislike'):
        raise HTTPException(status_code=400, detail="Rating must be 'like' or 'dislike'")

    langfuse = get_langfuse_client()

    if not langfuse:
        # Langfuse not enabled, but still accept the feedback gracefully
        logger.info(f"Feedback received (Langfuse disabled): trace={feedback.trace_id}, rating={feedback.rating}")
        return FeedbackResponse(
            success=True,
            message="Feedback received (tracing not enabled)"
        )

    try:
        # Map rating to numeric score for Langfuse
        score_value = 1.0 if feedback.rating == 'like' else 0.0

        # Record score in Langfuse using create_score
        # Note: Langfuse SDK batches and sends asynchronously in background
        langfuse.create_score(
            trace_id=feedback.trace_id,
            name="user_feedback",
            value=score_value,
            comment=feedback.comment,
            data_type="NUMERIC"
        )

        logger.info(f"Feedback recorded: trace={feedback.trace_id}, rating={feedback.rating}")

        return FeedbackResponse(
            success=True,
            message="Thank you for your feedback!"
        )

    except Exception as e:
        logger.error(f"Failed to record feedback: {e}")
        raise HTTPException(status_code=500, detail="Failed to record feedback")
