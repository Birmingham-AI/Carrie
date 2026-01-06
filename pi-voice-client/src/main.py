"""
Main application for Raspberry Pi Voice Client.

Coordinates all components: button, audio, WebRTC, and voice trace.
"""

import asyncio
import logging
import signal
import sys
from typing import Optional

from .config import config
from .button_handler import ButtonHandler
from .audio_handler import AudioHandler
from .webrtc_client import WebRTCClient
from .voice_trace_client import VoiceTraceClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class VoiceClientApp:
    """Main application class."""

    def __init__(self):
        """Initialize the application."""
        # Components
        self.button_handler: Optional[ButtonHandler] = None
        self.audio_handler: Optional[AudioHandler] = None
        self.webrtc_client: Optional[WebRTCClient] = None
        self.voice_trace_client: Optional[VoiceTraceClient] = None

        # State
        self.is_running = False
        self.is_recording = False
        self.current_session_active = False

        # Response text accumulation for voice trace
        self.response_text = ""
        
        # Event loop reference for thread-safe scheduling
        self.loop: Optional[asyncio.AbstractEventLoop] = None

    async def initialize(self) -> None:
        """Initialize all components."""
        try:
            # Store reference to event loop for thread-safe callbacks
            self.loop = asyncio.get_running_loop()
            
            # Validate configuration
            errors = config.validate()
            if errors:
                logger.error("Configuration errors:")
                for error in errors:
                    logger.error(f"  - {error}")
                raise Exception("Invalid configuration")

            logger.info(f"Configuration: {config}")

            # Initialize voice trace client
            self.voice_trace_client = VoiceTraceClient()

            # Initialize audio handler
            self.audio_handler = AudioHandler(on_audio_data=self._on_audio_data)

            # Initialize WebRTC client
            self.webrtc_client = WebRTCClient(
                on_audio_received=self._on_audio_received,
                on_event=self._on_webrtc_event,
            )

            # Initialize button handler
            self.button_handler = ButtonHandler(
                on_press=self._on_button_press,
                on_release=self._on_button_release,
            )

            logger.info("All components initialized")

        except Exception as e:
            logger.error(f"Failed to initialize: {e}")
            raise

    def _on_audio_data(self, audio_data: bytes) -> None:
        """
        Handle audio data from microphone.

        Args:
            audio_data: PCM audio data
        """
        if self.webrtc_client and self.is_recording:
            # Send audio to WebRTC client
            self.webrtc_client.send_audio(audio_data)

    def _on_audio_received(self, audio_data: bytes) -> None:
        """
        Handle audio data received from OpenAI.

        Args:
            audio_data: PCM audio data
        """
        logger.info(f"Received {len(audio_data)} bytes of audio from OpenAI")
        if self.audio_handler:
            # Play audio through speakers
            self.audio_handler.play_audio(audio_data)
        else:
            logger.warning("Audio handler not available, cannot play audio")

    def _on_webrtc_event(self, event: dict) -> None:
        """
        Handle WebRTC/Realtime API events.

        Args:
            event: Event dictionary from OpenAI Realtime API
        """
        event_type = event.get("type", "")

        # Handle different event types
        if event_type == "conversation.item.input_audio_transcription.completed":
            # User transcript received
            transcript = event.get("transcript", "")
            if transcript and self.voice_trace_client:
                asyncio.create_task(
                    self.voice_trace_client.log_user_transcript(transcript)
                )
            logger.info(f"User: {transcript}")

        elif event_type == "response.text.delta":
            # Response text delta
            delta = event.get("delta", "")
            self.response_text += delta

        elif event_type == "response.audio_transcript.delta":
            # Response audio transcript delta
            delta = event.get("delta", "")
            self.response_text += delta

        elif event_type == "response.output_item.added":
            # Response started
            item = event.get("item", {})
            if item.get("type") == "message":
                logger.info("Assistant response started")
                self.response_text = ""  # Reset for new response

        elif event_type == "response.done":
            # Response completed
            if self.response_text and self.voice_trace_client:
                asyncio.create_task(
                    self.voice_trace_client.log_assistant_response(self.response_text)
                )
            logger.info(f"Assistant: {self.response_text}")
            self.response_text = ""
            
            # Close the connection now that response is complete
            if self.loop:
                asyncio.run_coroutine_threadsafe(self._close_connection(), self.loop)

        elif event_type == "response.function_call_arguments.done":
            # Function call completed
            call_id = event.get("call_id", "")
            name = event.get("name", "")
            arguments = event.get("arguments", "")
            if name and self.voice_trace_client:
                asyncio.create_task(
                    self.voice_trace_client.log_function_call(name, arguments)
                )
            logger.info(f"Function call: {name}({arguments})")

        elif event_type == "error":
            # Error occurred
            error_msg = event.get("error", {}).get("message", "Unknown error")
            logger.error(f"Realtime API error: {error_msg}")

    def _on_button_press(self) -> None:
        """Handle button press (start recording)."""
        if self.is_recording:
            logger.warning("Already recording, ignoring button press")
            return

        logger.info("Button pressed - starting recording")
        # Schedule coroutine from callback thread using the main event loop
        if self.loop:
            asyncio.run_coroutine_threadsafe(self._start_recording(), self.loop)
        else:
            logger.error("Event loop not available, cannot start recording")

    def _on_button_release(self) -> None:
        """Handle button release (stop recording and send)."""
        if not self.is_recording:
            return

        logger.info("Button released - stopping recording")
        # Schedule coroutine from callback thread using the main event loop
        if self.loop:
            asyncio.run_coroutine_threadsafe(self._stop_recording(), self.loop)
        else:
            logger.error("Event loop not available, cannot stop recording")

    async def _start_recording(self) -> None:
        """Start recording and establish connection."""
        try:
            self.is_recording = True

            # Start voice trace session
            if self.voice_trace_client:
                await self.voice_trace_client.start_session()

            # Start audio recording
            if self.audio_handler:
                self.audio_handler.start_recording()

            # Establish WebRTC connection
            if self.webrtc_client:
                await self.webrtc_client.connect()
                self.current_session_active = True

            logger.info("Recording started and connection established")

        except Exception as e:
            logger.error(f"Error starting recording: {e}")
            await self._stop_recording()

    async def _stop_recording(self) -> None:
        """Stop recording but keep connection open for response."""
        try:
            self.is_recording = False

            # Stop audio recording (but keep connection open)
            if self.audio_handler:
                self.audio_handler.stop_recording()

            # Signal to OpenAI that input is complete
            if self.webrtc_client and self.current_session_active:
                # Send input_audio_buffer.commit event to signal input is complete
                try:
                    await self.webrtc_client.send_event({
                        "type": "input_audio_buffer.commit"
                    })
                    logger.info("Signaled input complete to OpenAI - waiting for response")
                except Exception as e:
                    logger.error(f"Failed to send input_audio_buffer.commit event: {e}")
            else:
                logger.warning("Cannot send commit event: WebRTC client not available or session not active")

            # DON'T close connection here - wait for response.done event
            # The connection will be closed when response.done is received

            logger.info("Recording stopped, waiting for response...")

        except Exception as e:
            logger.error(f"Error stopping recording: {e}")
            # If there's an error, still try to close connection
            await self._close_connection()
    
    async def _close_connection(self) -> None:
        """Close WebRTC connection after response is complete."""
        try:
            if self.webrtc_client and self.current_session_active:
                await self.webrtc_client.cleanup()
                self.current_session_active = False
                logger.info("WebRTC connection closed after response")
            
            # End voice trace session
            if self.voice_trace_client:
                await self.voice_trace_client.end_session()
                
        except Exception as e:
            logger.error(f"Error closing connection: {e}")

    async def run(self) -> None:
        """Run the application main loop."""
        try:
            await self.initialize()
            self.is_running = True

            logger.info("Application started. Press button to record.")

            # Main event loop - keep running until stopped
            while self.is_running:
                await asyncio.sleep(1)

        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
        finally:
            await self.cleanup()

    async def cleanup(self) -> None:
        """Clean up all resources."""
        logger.info("Cleaning up...")

        try:
            # Stop recording if active
            if self.is_recording:
                self.is_recording = False
                if self.audio_handler:
                    self.audio_handler.stop_recording()

            # Close connection and end voice trace
            if self.current_session_active:
                await self._close_connection()
            elif self.webrtc_client:
                # If connection exists but wasn't active, just cleanup
                await self.webrtc_client.cleanup()

            # Clean up components
            if self.audio_handler:
                self.audio_handler.cleanup()

            if self.button_handler:
                self.button_handler.cleanup()

            logger.info("Cleanup complete")

        except Exception as e:
            logger.error(f"Error during cleanup: {e}")


def main():
    """Main entry point."""
    app = VoiceClientApp()

    # Setup signal handlers for graceful shutdown
    def signal_handler(sig, frame):
        logger.info("Received signal, shutting down...")
        app.is_running = False

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Run the application
    try:
        asyncio.run(app.run())
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

