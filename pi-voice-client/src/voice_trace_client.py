"""
Voice Trace Client for logging events to the backend API.

Integrates with the voice trace API endpoints for observability.
"""

import logging
import time
import uuid
from typing import Optional, Literal
import httpx
from .config import config

logger = logging.getLogger(__name__)


class VoiceTraceClient:
    """Client for voice trace API integration."""

    def __init__(self):
        """Initialize voice trace client."""
        self.api_base_url = config.API_BASE_URL
        self.session_id: Optional[str] = None
        self.trace_id: Optional[str] = None
        self.enabled = False
        self.start_time: Optional[float] = None
        self.message_count = 0

    async def start_session(self) -> bool:
        """
        Start a new voice trace session.

        Returns:
            True if tracing is enabled, False otherwise
        """
        try:
            # Generate unique session ID
            self.session_id = str(uuid.uuid4())
            self.start_time = time.time()
            self.message_count = 0

            # Call start endpoint
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(
                    f"{self.api_base_url}/v1/voice/trace/start",
                    json={"session_id": self.session_id},
                )

                if response.status_code == 200:
                    data = response.json()
                    self.trace_id = data.get("trace_id", "")
                    self.enabled = data.get("enabled", False)

                    if self.enabled:
                        logger.info(f"Voice trace session started: {self.session_id}")
                    else:
                        logger.debug("Voice trace disabled on backend")
                else:
                    logger.warning(
                        f"Failed to start voice trace: {response.status_code} - {response.text}"
                    )
                    self.enabled = False

        except Exception as e:
            logger.error(f"Error starting voice trace session: {e}")
            self.enabled = False

        return self.enabled

    async def log_event(
        self,
        event_type: Literal["user_transcript", "assistant_response", "function_call"],
        content: str,
        metadata: Optional[dict] = None,
    ) -> None:
        """
        Log a voice event.

        Args:
            event_type: Type of event (user_transcript, assistant_response, function_call)
            content: Event content
            metadata: Optional metadata dictionary
        """
        if not self.enabled or not self.trace_id:
            return

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(
                    f"{self.api_base_url}/v1/voice/trace/event",
                    json={
                        "trace_id": self.trace_id,
                        "event_type": event_type,
                        "content": content,
                        "metadata": metadata or {},
                    },
                )

                if response.status_code == 200:
                    logger.debug(f"Logged {event_type} event")
                else:
                    logger.warning(
                        f"Failed to log event: {response.status_code} - {response.text}"
                    )

        except Exception as e:
            # Non-blocking: log error but don't raise
            logger.debug(f"Error logging event (non-blocking): {e}")

    async def log_user_transcript(self, transcript: str) -> None:
        """Log user transcript."""
        await self.log_event("user_transcript", transcript)
        self.message_count += 1

    async def log_assistant_response(self, response: str) -> None:
        """Log assistant response."""
        await self.log_event("assistant_response", response)

    async def log_function_call(self, function_name: str, arguments: str, result: str = "") -> None:
        """Log function call."""
        await self.log_event(
            "function_call",
            f"{function_name}({arguments})",
            metadata={"result": result} if result else None,
        )

    async def end_session(self) -> None:
        """End the voice trace session."""
        if not self.enabled or not self.trace_id:
            return

        try:
            # Calculate duration
            duration_ms = 0
            if self.start_time:
                duration_ms = int((time.time() - self.start_time) * 1000)

            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(
                    f"{self.api_base_url}/v1/voice/trace/end",
                    json={
                        "trace_id": self.trace_id,
                        "duration_ms": duration_ms,
                        "message_count": self.message_count,
                    },
                )

                if response.status_code == 200:
                    logger.info(
                        f"Voice trace session ended: {self.session_id} "
                        f"({self.message_count} messages, {duration_ms}ms)"
                    )
                else:
                    logger.warning(
                        f"Failed to end voice trace: {response.status_code} - {response.text}"
                    )

        except Exception as e:
            # Non-blocking: log error but don't raise
            logger.debug(f"Error ending voice trace session (non-blocking): {e}")
        finally:
            # Reset state
            self.session_id = None
            self.trace_id = None
            self.enabled = False
            self.start_time = None
            self.message_count = 0

