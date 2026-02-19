"""
Langfuse Tracing Integration

This module provides conditional Langfuse tracing for the OpenAI Agents SDK.
Tracing is controlled via the LANGFUSE_ENABLED environment variable.

Uses both:
- Native Langfuse SDK for parent spans with input/output
- OpenInference instrumentation for capturing agent tool calls
"""

import os
import base64
import logging

logger = logging.getLogger(__name__)

LANGFUSE_ENABLED = os.getenv("LANGFUSE_ENABLED", "false").lower() == "true"

_langfuse_client = None


def init_langfuse():
    """
    Initialize Langfuse tracing if enabled via environment variable.

    Required environment variables when enabled:
    - LANGFUSE_ENABLED: Set to "true" to enable tracing
    - LANGFUSE_PUBLIC_KEY: Your Langfuse public key
    - LANGFUSE_SECRET_KEY: Your Langfuse secret key
    - LANGFUSE_BASE_URL: Langfuse host URL (optional, defaults to US cloud)
    """
    global _langfuse_client

    logger.info(f"[LANGFUSE] init_langfuse called. LANGFUSE_ENABLED={LANGFUSE_ENABLED}")

    if not LANGFUSE_ENABLED:
        logger.info("[LANGFUSE] Tracing disabled")
        return

    public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
    secret_key = os.getenv("LANGFUSE_SECRET_KEY")
    base_url = os.getenv("LANGFUSE_BASE_URL", "https://us.cloud.langfuse.com")

    # Initialize native Langfuse client
    from langfuse import Langfuse

    _langfuse_client = Langfuse(
        public_key=public_key,
        secret_key=secret_key,
        host=base_url
    )

    if not _langfuse_client.auth_check():
        logger.error(f"[LANGFUSE] Authentication FAILED for {base_url}")
        _langfuse_client = None
        return

    logger.info(f"[LANGFUSE] Authentication successful for {base_url}")

    # Set up OpenInference instrumentation to capture agent tool calls
    # Configure OTLP exporter to send to Langfuse
    auth = base64.b64encode(f"{public_key}:{secret_key}".encode()).decode()
    endpoint = f"{base_url}/api/public/otel/v1/traces"
    headers = {"Authorization": f"Basic {auth}"}

    from opentelemetry import trace
    from opentelemetry.sdk import trace as trace_sdk
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from openinference.instrumentation.openai_agents import OpenAIAgentsInstrumentor

    # Create and set global TracerProvider
    tracer_provider = trace_sdk.TracerProvider()
    tracer_provider.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint, headers=headers))
    )
    trace.set_tracer_provider(tracer_provider)

    # Instrument OpenAI Agents SDK
    OpenAIAgentsInstrumentor().instrument(tracer_provider=tracer_provider)

    logger.info("Langfuse tracing enabled (native SDK + OpenInference)")


def get_langfuse_client():
    """Get the Langfuse client instance (or None if not enabled)"""
    return _langfuse_client


# Voice tracing functions
_voice_sessions = {}


def create_voice_trace(session_id: str, user_id: str) -> str:
    """
    Initialize a voice session for tracing.
    Returns the session_id which is used to group traces.
    """
    if not _langfuse_client:
        logger.warning("[LANGFUSE] Client not initialized - voice trace skipped")
        return ""

    logger.info(f"[LANGFUSE] Initializing voice session: {session_id}")

    # Store session info for creating per-turn traces
    _voice_sessions[session_id] = {
        "user_id": user_id,
        "turn_count": 0,
        "current_turn": {
            "user_input": None,
            "assistant_output": None,
            "function_calls": []
        }
    }

    logger.info(f"[LANGFUSE] Voice session initialized: {session_id}")
    return session_id


def add_voice_generation(
    trace_id: str,  # This is actually session_id
    event_type: str,
    content: str,
    metadata: dict = None
) -> None:
    """
    Add an event to the current turn. Creates a trace when a turn completes.
    Event types: user_transcript, assistant_response, function_call
    """
    session_id = trace_id  # Renamed for clarity
    if not _langfuse_client or session_id not in _voice_sessions:
        return

    session = _voice_sessions[session_id]
    turn = session["current_turn"]

    if event_type == "user_transcript":
        # New user input - if we have a pending turn, flush it first
        if turn["user_input"] and turn["assistant_output"]:
            _flush_turn(session_id)
        turn["user_input"] = content
        logger.info(f"[LANGFUSE] User transcript: {content[:50]}...")

    elif event_type == "assistant_response":
        turn["assistant_output"] = content
        logger.info(f"[LANGFUSE] Assistant response: {content[:50]}...")
        # Flush the turn now that we have both input and output
        if turn["user_input"]:
            _flush_turn(session_id)

    elif event_type == "function_call":
        # Store both the call and the result from metadata
        turn["function_calls"].append({
            "call": content,
            "result": metadata.get("result", "") if metadata else ""
        })
        logger.info(f"[LANGFUSE] Function call: {content[:50]}...")


def _flush_turn(session_id: str) -> None:
    """
    Create a Langfuse trace for the completed turn.
    """
    if session_id not in _voice_sessions:
        return

    session = _voice_sessions[session_id]
    turn = session["current_turn"]
    session["turn_count"] += 1
    turn_num = session["turn_count"]

    user_input = turn["user_input"] or "No input"
    assistant_output = turn["assistant_output"] or "No output"
    function_calls = turn["function_calls"]

    # Generate unique trace ID for this turn
    trace_id = _langfuse_client.create_trace_id(seed=f"{session_id}-turn-{turn_num}")

    # Create the trace for this turn
    with _langfuse_client.start_as_current_span(
        name="voice-turn",
        input=user_input,
        trace_context={"trace_id": trace_id}
    ) as span:
        span.update_trace(
            user_id=session["user_id"],
            session_id=session_id,  # Groups all turns together
            tags=["carrie", "voice-mode"],
            metadata={
                "mode": "realtime-webrtc",
                "turn_number": turn_num
            }
        )

        # Create child spans for each function call
        for i, func_data in enumerate(function_calls):
            try:
                func_call = func_data.get("call", "") if isinstance(func_data, dict) else func_data
                func_result = func_data.get("result", "") if isinstance(func_data, dict) else ""

                # Parse function call string to extract name and args
                # Format: "function_name({args})"
                if "(" in func_call:
                    func_name = func_call.split("(")[0]
                    func_args = func_call[len(func_name)+1:-1]  # Remove name( and )
                else:
                    func_name = "tool_call"
                    func_args = func_call

                with _langfuse_client.start_as_current_span(
                    name=func_name,
                    input=func_args
                ) as tool_span:
                    tool_span.update(
                        output=func_result[:1000] if func_result else None,  # Truncate long results
                        metadata={"tool_index": i}
                    )
            except Exception as e:
                logger.error(f"[LANGFUSE] Error creating tool span: {e}")

        span.update(output=assistant_output)

    logger.info(f"[LANGFUSE] Flushed turn {turn_num} for session {session_id}")

    # Reset current turn
    session["current_turn"] = {
        "user_input": None,
        "assistant_output": None,
        "function_calls": []
    }


def end_voice_trace(trace_id: str, duration_ms: int, message_count: int) -> None:
    """
    End a voice session - flush any pending turn and cleanup.
    """
    session_id = trace_id  # trace_id is actually session_id
    if not _langfuse_client or session_id not in _voice_sessions:
        return

    session = _voice_sessions.get(session_id)
    if not session:
        return

    # Flush any pending turn
    turn = session["current_turn"]
    if turn["user_input"] or turn["assistant_output"]:
        _flush_turn(session_id)

    # Cleanup session
    _voice_sessions.pop(session_id, None)
    _langfuse_client.flush()
    logger.info(f"[LANGFUSE] Ended voice session: {session_id} ({session['turn_count']} turns, {duration_ms}ms)")
