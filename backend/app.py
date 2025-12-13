import logging
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes import ask_router, upload_router, feedback_router, realtime_router, voice_trace_router
from services.langfuse_tracing import init_langfuse

# Load environment variables
load_dotenv()

# Initialize Langfuse tracing (if enabled via LANGFUSE_ENABLED env var)
init_langfuse()

# Configure logging
logging.basicConfig(level=logging.WARNING)

app = FastAPI(
    title="Carrie Backend API",
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

# Include routers
app.include_router(ask_router)
app.include_router(upload_router)
app.include_router(feedback_router)
app.include_router(realtime_router)
app.include_router(voice_trace_router)


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Carrie Backend API",
        "version": "1.0.0"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
