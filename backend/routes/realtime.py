"""
Realtime API routes for voice interaction

This module provides endpoints for establishing WebRTC connections
to OpenAI's Realtime API for speech-to-speech interaction.
"""

import httpx
from os import getenv
from pathlib import Path
from fastapi import APIRouter, HTTPException, Request

from middleware import rate_limiter

router = APIRouter(prefix="/v1/realtime", tags=["realtime"])

OPENAI_API_KEY = getenv("OPENAI_API_KEY")


def load_voice_prompt() -> str:
    """Load the Carrie prompt for voice interaction."""
    prompt_path = Path(__file__).parent.parent / "prompts" / "carrie_voice.txt"
    if prompt_path.exists():
        with open(prompt_path, "r") as f:
            return f.read()
    # Fall back to main prompt if voice-specific doesn't exist
    prompt_path = Path(__file__).parent.parent / "prompts" / "carrie.txt"
    with open(prompt_path, "r") as f:
        return f.read()


@router.post("/session")
async def create_realtime_session(request: Request):
    """
    Create an ephemeral token for WebRTC connection to OpenAI Realtime API.

    The frontend uses this token to establish a direct WebRTC connection
    to OpenAI for speech-to-speech interaction.

    Returns:
        Ephemeral session credentials including client_secret
    """
    rate_limiter.check_rate_limit(request)

    if not OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="OpenAI API key not configured")

    instructions = load_voice_prompt()

    # Remove template placeholders from voice prompt
    from datetime import datetime
    instructions = instructions.replace("{current_date}", datetime.now().strftime("%d %B %Y"))

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.openai.com/v1/realtime/sessions",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "gpt-realtime",
                "modalities": ["audio", "text"],
                "voice": "shimmer",
                "instructions": instructions,
                "tools": [
                    {
                        "type": "function",
                        "name": "meeting_notes",
                        "description": "Query Birmingham AI community meeting notes. Supports two actions: 'list_sessions' to see available meetings, and 'search' to find content within meetings.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "action": {
                                    "type": "string",
                                    "enum": ["list_sessions", "search"],
                                    "description": "Action to perform. Use 'list_sessions' to see what meetings/sessions exist (e.g., 'what meetings happened in November?'). Use 'search' to find specific content within meetings (e.g., 'what was discussed about AI ethics?')."
                                },
                                "filter": {
                                    "type": "string",
                                    "description": "For 'list_sessions' action: filter term to narrow results (e.g., 'November', 'Engineering', '2025')"
                                },
                                "query": {
                                    "type": "string",
                                    "description": "For 'search' action: the search query to find relevant content"
                                },
                                "top_k": {
                                    "type": "integer",
                                    "description": "For 'search' action: number of results to return (default: 5)",
                                    "default": 5
                                },
                                "session_filter": {
                                    "type": "string",
                                    "description": "For 'search' action: filter for specific session. Use format '[Domain] breakout [Month] [Year]' (e.g., 'Engineering breakout November 2025') or 'General meetup [Month] [Year]'."
                                }
                            },
                            "required": ["action"]
                        }
                    },
                    {
                        "type": "function",
                        "name": "eventbrite",
                        "description": "Get Birmingham AI events from Eventbrite. Supports two actions: 'list' for upcoming events, and 'details' for full information about a specific event.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "action": {
                                    "type": "string",
                                    "enum": ["list", "details"],
                                    "description": "Action to perform. Use 'list' to see upcoming events. Use 'details' to get full description and agenda for a specific event."
                                },
                                "limit": {
                                    "type": "integer",
                                    "description": "For 'list' action: number of events to return (default: 3)",
                                    "default": 3
                                },
                                "event_id": {
                                    "type": "string",
                                    "description": "For 'details' action: the event ID to get full details for"
                                }
                            },
                            "required": ["action"]
                        }
                    }
                ],
                "input_audio_transcription": {
                    "model": "whisper-1"
                },
                "turn_detection": {
                    "type": "server_vad",
                    "threshold": 0.5,
                    "prefix_padding_ms": 300,
                    "silence_duration_ms": 500
                }
            },
            timeout=30.0
        )

        if response.status_code != 200:
            error_detail = response.text
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Failed to create realtime session: {error_detail}"
            )

        return response.json()
