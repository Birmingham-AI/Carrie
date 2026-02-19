from pydantic import BaseModel, Field
from typing import List, Dict, Optional


class QuestionRequest(BaseModel):
    question: str = Field(..., max_length=4000)
    messages: List[Dict[str, str]] = Field(default_factory=list, max_length=50)
    enable_web_search: bool = True


class SearchResult(BaseModel):
    text: str
    timestamp: str
    session_info: str
    score: float


class QuestionResponse(BaseModel):
    answer: str
    results: List[SearchResult]


class YouTubeUploadRequest(BaseModel):
    url: str
    session_info: str
    chunk_size: Optional[int] = 1000
    overlap: Optional[int] = 1
    language: Optional[str] = "en"


class UploadResponse(BaseModel):
    job_id: str
    status: str
    message: str


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    message: str
    source_id: Optional[str] = None
    chunk_count: Optional[int] = None
    error: Optional[str] = None


class FeedbackRequest(BaseModel):
    trace_id: str
    rating: str  # 'like' or 'dislike'
    comment: Optional[str] = None


class FeedbackResponse(BaseModel):
    success: bool
    message: str
