"""
Voice Trace API Routes

Provides endpoints for logging voice mode events to Langfuse.
Since voice mode uses WebRTC (browser -> OpenAI directly),
the frontend sends events here for observability.
"""

import logging
from fastapi import APIRouter, Request
from pydantic import BaseModel
from typing import Optional, Literal
from services.langfuse_tracing import (
    create_voice_trace,
    add_voice_generation,
    end_voice_trace,
    LANGFUSE_ENABLED
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/voice", tags=["voice"])


class VoiceTraceStartRequest(BaseModel):
    session_id: str


class VoiceTraceStartResponse(BaseModel):
    trace_id: str
    enabled: bool


class VoiceEventRequest(BaseModel):
    trace_id: str
    event_type: Literal["user_transcript", "assistant_response", "function_call"]
    content: str
    metadata: Optional[dict] = None


class VoiceEventResponse(BaseModel):
    success: bool


class VoiceTraceEndRequest(BaseModel):
    trace_id: str
    duration_ms: int
    message_count: int


class VoiceTraceEndResponse(BaseModel):
    success: bool


@router.post("/trace/start", response_model=VoiceTraceStartResponse)
async def start_voice_trace(request: VoiceTraceStartRequest, req: Request):
    """
    Start a new voice trace session.
    Called when voice mode connects.
    """
    print(f"[VOICE TRACE] Start requested. LANGFUSE_ENABLED={LANGFUSE_ENABLED}")

    if not LANGFUSE_ENABLED:
        print("[VOICE TRACE] Langfuse disabled")
        return VoiceTraceStartResponse(trace_id="", enabled=False)

    user_id = req.client.host if req.client else "unknown"
    trace_id = create_voice_trace(
        session_id=request.session_id,
        user_id=user_id
    )

    print(f"[VOICE TRACE] Created trace: {trace_id}")
    return VoiceTraceStartResponse(trace_id=trace_id, enabled=True)


@router.post("/trace/event", response_model=VoiceEventResponse)
async def log_voice_event(request: VoiceEventRequest):
    """
    Log a voice event (transcript, response, or function call).
    """
    if not LANGFUSE_ENABLED:
        return VoiceEventResponse(success=True)

    add_voice_generation(
        trace_id=request.trace_id,
        event_type=request.event_type,
        content=request.content,
        metadata=request.metadata
    )

    return VoiceEventResponse(success=True)


@router.post("/trace/end", response_model=VoiceTraceEndResponse)
async def end_voice_trace_session(request: VoiceTraceEndRequest):
    """
    End a voice trace session.
    Called when voice mode disconnects.
    """
    if not LANGFUSE_ENABLED:
        return VoiceTraceEndResponse(success=True)

    end_voice_trace(
        trace_id=request.trace_id,
        duration_ms=request.duration_ms,
        message_count=request.message_count
    )

    return VoiceTraceEndResponse(success=True)
