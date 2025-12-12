from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from middleware import rate_limiter
from models import QuestionRequest, SearchResult
from services.rag_service import RAGService
from services.streaming_agent import StreamingMeetingNotesAgent
from services.eventbrite_service import EventbriteService
from clients.eventbrite import is_configured as eventbrite_configured
from utils import get_client_ip

router = APIRouter(prefix="/v1", tags=["chat"])

# Initialize RAG service (agent created per-request to allow web search toggle)
rag_service = RAGService()


@router.post("/chat")
async def ask_question(request: Request, question_request: QuestionRequest):
    """
    Ask a question and get a streaming response.

    The agent will use RAGService as a tool to search meeting notes and
    optionally use web search for additional context.

    Request body:
    - question: The question to ask
    - messages: Optional conversation history [{"role": "user/assistant", "content": "..."}]
    - enable_web_search: Whether to allow web search (default: True)

    Returns:
    Server-Sent Events stream with the answer
    """
    rate_limiter.check_rate_limit(request)

    try:
        # Get client IP for tracing (handles X-Forwarded-For for proxied requests)
        client_ip = get_client_ip(request)

        # Create agent with requested configuration
        agent = StreamingMeetingNotesAgent(
            rag_service,
            enable_web_search=question_request.enable_web_search
        )

        async def generate():
            # Stream the answer from the agent with conversation history
            async for chunk_type, data in agent.stream_answer(
                question_request.question,
                question_request.messages,
                user_id=client_ip
            ):
                if chunk_type == "trace_id":
                    # Send trace ID as a special event
                    yield f"event: trace_id\ndata: {data}\n\n"
                else:
                    # Send text chunk
                    escaped_chunk = data.replace('\n', '\\n')
                    yield f"data: {escaped_chunk}\n\n"

            # Send completion marker
            yield "data: [DONE]\n\n"

        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            }
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/search")
async def search_notes(request: Request, question: str, top_k: int = 5, session_filter: str = None):
    """
    Search meeting notes without answer synthesis.

    Query parameters:
    - question: The search query
    - top_k: Number of top results to return (default: 5)
    - session_filter: Optional filter for session type or date

    Returns:
    - List of search results with similarity scores
    """
    rate_limiter.check_rate_limit(request)

    try:
        results = await rag_service.search_meeting_notes(question, top_k, session_filter)
        return {"results": [SearchResult(**result) for result in results]}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/sessions")
async def list_sessions(request: Request, filter: str = None):
    """
    List available sessions/meetings.

    Query parameters:
    - filter: Optional filter term (e.g., "November", "Engineering", "2025")

    Returns:
    - List of sessions with session_info and chunk_count
    """
    rate_limiter.check_rate_limit(request)

    try:
        sessions = await rag_service.list_sessions(filter)
        return {"sessions": sessions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/events")
async def get_events(request: Request, action: str = "list", limit: int = 3, event_id: str = None):
    """
    Get Birmingham AI events from Eventbrite.

    Query parameters:
    - action: "list" for upcoming events, "details" for full event info (default: "list")
    - limit: Number of events to return for list action (default: 3)
    - event_id: Event ID for details action

    Returns:
    - List of events (action=list) or single event with full details (action=details)
    """
    rate_limiter.check_rate_limit(request)

    if not eventbrite_configured():
        raise HTTPException(status_code=503, detail="Eventbrite integration not configured")

    try:
        eventbrite_service = EventbriteService()

        if action == "details":
            if not event_id:
                raise HTTPException(status_code=400, detail="event_id required for details action")
            event = await eventbrite_service.get_event_details(event_id)
            if not event:
                raise HTTPException(status_code=404, detail="Event not found")
            return {"event": event}
        else:
            events = await eventbrite_service.get_upcoming_events(limit)
            return {"events": events}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch events: {str(e)}")
