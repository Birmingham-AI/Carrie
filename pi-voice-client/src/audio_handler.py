"""
Audio Handler for recording and playback.

Handles microphone input and speaker output using PyAudio.
"""

import logging
import pyaudio
import queue
import threading
from typing import Optional, Callable
from .config import config

logger = logging.getLogger(__name__)

# PyAudio format constants
PYAUDIO_FORMAT = pyaudio.paInt16  # 16-bit PCM


class AudioHandler:
    """Handles audio recording and playback."""

    def __init__(
        self,
        on_audio_data: Optional[Callable[[bytes], None]] = None,
    ):
        """
        Initialize audio handler.

        Args:
            on_audio_data: Callback function called with recorded audio chunks (bytes)
        """
        self.on_audio_data = on_audio_data

        # Audio configuration
        self.sample_rate = config.AUDIO_SAMPLE_RATE
        self.channels = config.AUDIO_CHANNELS
        self.chunk_size = config.AUDIO_CHUNK_SIZE
        self.format = PYAUDIO_FORMAT
        self.format_width = pyaudio.get_sample_size(self.format)

        # PyAudio instance
        self.audio = pyaudio.PyAudio()

        # Audio streams
        self.input_stream: Optional[pyaudio.Stream] = None
        self.output_stream: Optional[pyaudio.Stream] = None

        # Recording state
        self.is_recording = False
        self.recording_thread: Optional[threading.Thread] = None

        # Playback queue
        self.playback_queue: queue.Queue = queue.Queue()
        self.is_playing = False
        self.playback_thread: Optional[threading.Thread] = None

        logger.info(
            f"Audio handler initialized: {self.sample_rate}Hz, "
            f"{self.channels} channel(s), chunk_size={self.chunk_size}"
        )

    def start_recording(self) -> None:
        """Start recording from microphone."""
        if self.is_recording:
            logger.warning("Already recording")
            return

        try:
            # Open input stream
            self.input_stream = self.audio.open(
                format=self.format,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.chunk_size,
                stream_callback=self._input_callback,
            )

            self.is_recording = True
            self.input_stream.start_stream()
            logger.info("Started recording")

        except Exception as e:
            logger.error(f"Failed to start recording: {e}")
            self.is_recording = False
            raise

    def stop_recording(self) -> None:
        """Stop recording from microphone."""
        if not self.is_recording:
            return

        try:
            if self.input_stream:
                self.input_stream.stop_stream()
                self.input_stream.close()
                self.input_stream = None

            self.is_recording = False
            logger.info("Stopped recording")

        except Exception as e:
            logger.error(f"Error stopping recording: {e}")

    def _input_callback(
        self, in_data: bytes, frame_count: int, time_info: dict, status: int
    ) -> tuple[Optional[bytes], int]:
        """
        Callback for audio input stream.

        Args:
            in_data: Audio data from microphone
            frame_count: Number of frames
            time_info: Timing information
            status: Status flags

        Returns:
            Tuple of (None, pyaudio.paContinue) to continue streaming
        """
        if status:
            logger.warning(f"Audio input status: {status}")

        if self.on_audio_data and in_data:
            try:
                self.on_audio_data(in_data)
            except Exception as e:
                logger.error(f"Error in audio data callback: {e}")

        return (None, pyaudio.paContinue)

    def play_audio(self, audio_data: bytes) -> None:
        """
        Queue audio data for playback.

        Args:
            audio_data: Audio data to play (PCM format)
        """
        self.playback_queue.put(audio_data)

        # Start playback thread if not already running
        if not self.is_playing:
            self._start_playback()

    def _start_playback(self) -> None:
        """Start playback thread."""
        if self.is_playing:
            return

        try:
            # Open output stream
            self.output_stream = self.audio.open(
                format=self.format,
                channels=self.channels,
                rate=self.sample_rate,
                output=True,
                frames_per_buffer=self.chunk_size,
            )

            self.is_playing = True
            self.playback_thread = threading.Thread(
                target=self._playback_worker, daemon=True
            )
            self.playback_thread.start()
            logger.info("Started playback")

        except Exception as e:
            logger.error(f"Failed to start playback: {e}")
            self.is_playing = False
            raise

    def _playback_worker(self) -> None:
        """Worker thread for audio playback."""
        try:
            while self.is_playing:
                try:
                    # Get audio data from queue (with timeout)
                    audio_data = self.playback_queue.get(timeout=0.1)

                    if self.output_stream and audio_data:
                        self.output_stream.write(audio_data)

                except queue.Empty:
                    # Check if we should continue (queue might be empty temporarily)
                    continue
                except Exception as e:
                    logger.error(f"Error during playback: {e}")

        except Exception as e:
            logger.error(f"Playback worker error: {e}")
        finally:
            self._stop_playback()

    def stop_playback(self) -> None:
        """Stop playback and clear queue."""
        self.is_playing = False
        self._stop_playback()

    def _stop_playback(self) -> None:
        """Internal method to stop playback."""
        try:
            if self.output_stream:
                self.output_stream.stop_stream()
                self.output_stream.close()
                self.output_stream = None

            # Clear queue
            while not self.playback_queue.empty():
                try:
                    self.playback_queue.get_nowait()
                except queue.Empty:
                    break

            logger.info("Stopped playback")

        except Exception as e:
            logger.error(f"Error stopping playback: {e}")

    def get_audio_info(self) -> dict:
        """Get audio configuration information."""
        return {
            "sample_rate": self.sample_rate,
            "channels": self.channels,
            "chunk_size": self.chunk_size,
            "format": self.format,
            "format_width": self.format_width,
        }

    def list_audio_devices(self) -> None:
        """List available audio input and output devices."""
        logger.info("Available audio devices:")
        for i in range(self.audio.get_device_count()):
            info = self.audio.get_device_info_by_index(i)
            logger.info(
                f"  Device {i}: {info['name']} "
                f"(inputs: {info['maxInputChannels']}, "
                f"outputs: {info['maxOutputChannels']})"
            )

    def cleanup(self) -> None:
        """Clean up audio resources."""
        try:
            self.stop_recording()
            self.stop_playback()

            if self.audio:
                self.audio.terminate()

            logger.info("Audio handler cleaned up")

        except Exception as e:
            logger.error(f"Error cleaning up audio handler: {e}")

