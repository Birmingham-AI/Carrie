"""
Configuration management for Raspberry Pi Voice Client.

Loads configuration from environment variables with sensible defaults.
"""

import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from .env file if it exists
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)


class Config:
    """Application configuration loaded from environment variables."""

    # Backend API Configuration
    API_BASE_URL: str = os.getenv("API_BASE_URL", "http://localhost:8001")

    # GPIO Configuration
    BUTTON_GPIO_PIN: int = int(os.getenv("BUTTON_GPIO_PIN", "18"))

    # Audio Configuration
    # AUDIO_SAMPLE_RATE: Playback sample rate (must be supported by your USB device)
    # OpenAI sends 48kHz audio via WebRTC (matching most USB audio devices)
    AUDIO_SAMPLE_RATE: int = int(os.getenv("AUDIO_SAMPLE_RATE", "48000"))
    
    # Microphone input is always MONO (OpenAI requires mono input)
    AUDIO_INPUT_CHANNELS: int = 1
    
    # Speaker output can be MONO or STEREO (set to match your USB device)
    AUDIO_OUTPUT_CHANNELS: int = int(os.getenv("AUDIO_CHANNELS", "1"))
    
    # Legacy support: AUDIO_CHANNELS sets output channels
    AUDIO_CHANNELS: int = AUDIO_OUTPUT_CHANNELS
    
    AUDIO_CHUNK_SIZE: int = int(os.getenv("AUDIO_CHUNK_SIZE", "480"))

    # Audio format (OpenAI Realtime API requirements)
    AUDIO_FORMAT_BITS: int = 16  # 16-bit PCM
    AUDIO_FORMAT_BYTES: int = 2  # 2 bytes per sample

    # Debug Configuration
    DEBUG_AUDIO_RECORDING: bool = os.getenv("DEBUG_AUDIO_RECORDING", "false").lower() == "true"
    DEBUG_AUDIO_OUTPUT_DIR: str = os.getenv("DEBUG_AUDIO_OUTPUT_DIR", "/tmp/willAIam_debug")

    @classmethod
    def get_audio_format(cls) -> dict:
        """Get audio format dictionary for PyAudio."""
        return {
            "sample_rate": cls.AUDIO_SAMPLE_RATE,
            "channels": cls.AUDIO_CHANNELS,
            "format_bits": cls.AUDIO_FORMAT_BITS,
            "chunk_size": cls.AUDIO_CHUNK_SIZE,
        }

    @classmethod
    def validate(cls) -> list[str]:
        """Validate configuration and return list of errors (empty if valid)."""
        errors = []

        if not cls.API_BASE_URL:
            errors.append("API_BASE_URL is required")

        if cls.BUTTON_GPIO_PIN < 1 or cls.BUTTON_GPIO_PIN > 40:
            errors.append(f"BUTTON_GPIO_PIN must be between 1 and 40, got {cls.BUTTON_GPIO_PIN}")

        if cls.AUDIO_SAMPLE_RATE < 8000 or cls.AUDIO_SAMPLE_RATE > 48000:
            errors.append(f"AUDIO_SAMPLE_RATE must be between 8000 and 48000, got {cls.AUDIO_SAMPLE_RATE}")

        if cls.AUDIO_OUTPUT_CHANNELS not in [1, 2]:
            errors.append(f"AUDIO_CHANNELS must be 1 (mono) or 2 (stereo), got {cls.AUDIO_OUTPUT_CHANNELS}")

        if cls.AUDIO_CHUNK_SIZE < 100 or cls.AUDIO_CHUNK_SIZE > 4096:
            errors.append(f"AUDIO_CHUNK_SIZE must be between 100 and 4096, got {cls.AUDIO_CHUNK_SIZE}")

        return errors

    @classmethod
    def __repr__(cls) -> str:
        """String representation of configuration."""
        return (
            f"Config("
            f"API_BASE_URL={cls.API_BASE_URL}, "
            f"BUTTON_GPIO_PIN={cls.BUTTON_GPIO_PIN}, "
            f"AUDIO_SAMPLE_RATE={cls.AUDIO_SAMPLE_RATE}, "
            f"AUDIO_INPUT_CHANNELS={cls.AUDIO_INPUT_CHANNELS}, "
            f"AUDIO_OUTPUT_CHANNELS={cls.AUDIO_OUTPUT_CHANNELS}, "
            f"AUDIO_CHUNK_SIZE={cls.AUDIO_CHUNK_SIZE}, "
            f"DEBUG_AUDIO_RECORDING={cls.DEBUG_AUDIO_RECORDING}, "
            f"DEBUG_AUDIO_OUTPUT_DIR={cls.DEBUG_AUDIO_OUTPUT_DIR}"
            f")"
        )


# Global config instance
config = Config()

