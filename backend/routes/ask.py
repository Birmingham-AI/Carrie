from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from models import QuestionRequest, SearchResult
from services.rag_service import RAGService
from services.streaming_agent import StreamingMeetingNotesAgent

router = APIRouter(prefix="/v1", tags=["chat"])

# Initialize RAG service (agent created per-request to allow web search toggle)
rag_service = RAGService()


@router.post("/chat")
async def ask_question(request: QuestionRequest):
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
    try:
        # Create agent with requested configuration
        agent = StreamingMeetingNotesAgent(
            rag_service,
            enable_web_search=request.enable_web_search
        )

        async def generate():
            # Stream the answer from the agent with conversation history
            async for chunk in agent.stream_answer(request.question, request.messages):
                # Escape newlines in chunk to preserve them in SSE format
                # SSE interprets bare newlines as message delimiters, so we encode them
                escaped_chunk = chunk.replace('\n', '\\n')
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
async def search_notes(question: str, top_k: int = 5):
    """
    Search meeting notes without answer synthesis.

    Query parameters:
    - question: The search query
    - top_k: Number of top results to return (default: 5)

    Returns:
    - List of search results with similarity scores
    """
    try:
        results = await rag_service.search_meeting_notes(question, top_k)
        return {"results": [SearchResult(**result) for result in results]}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
