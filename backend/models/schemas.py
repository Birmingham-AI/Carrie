from pydantic import BaseModel
from typing import List, Dict, Optional


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
