from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional

from services.rag_service import RAGService
from services.streaming_agent import StreamingMeetingNotesAgent

app = FastAPI(
    title="willAIam Backend API",
    description="RAG API for Birmingham AI community meeting notes",
    version="1.0.0"
)

# CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update with specific origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize RAG service (agent created per-request to allow web search toggle)
rag_service = RAGService()


class QuestionRequest(BaseModel):
    question: str
    messages: Optional[List[Dict[str, str]]] = []
    enable_web_search: Optional[bool] = True


class SearchResult(BaseModel):
    slide: int
    year: int
    month: int
    text: str
    score: float


class QuestionResponse(BaseModel):
    answer: str
    results: List[SearchResult]


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "willAIam Backend API",
        "version": "1.0.0"
    }


@app.post("/api/ask")
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
                yield f"data: {chunk}\n\n"

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


@app.get("/api/search")
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
        results = rag_service.search_meeting_notes(question, top_k)
        return {"results": [SearchResult(**result) for result in results]}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
