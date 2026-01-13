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
        self.is_connecting = False  # Track if connection is in progress
        self.current_session_active = False

        # Response text accumulation for voice trace
        self.response_text = ""
        
        # Function call tracking
        self.pending_function_calls: dict = {}
        
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
            
            # Establish persistent WebRTC connection on startup
            logger.info("Establishing WebRTC connection...")
            await self.webrtc_client.connect()
            logger.info("WebRTC connection established and ready")

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
        logger.debug(f"Callback _on_audio_received invoked with {len(audio_data)} bytes of audio")
        if self.audio_handler:
            # Play audio through speakers
            self.audio_handler.play_audio(audio_data)
            logger.debug(f"Queued {len(audio_data)} bytes for playback")
        else:
            logger.warning("Audio handler not available, cannot play audio")

    def _on_webrtc_event(self, event: dict) -> None:
        """
        Handle WebRTC/Realtime API events.

        Args:
            event: Event dictionary from OpenAI Realtime API
        """
        event_type = event.get("type", "")
        logger.debug(f"WebRTC event received: {event_type}")  # Add debug logging

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
            elif item.get("type") == "function_call" and item.get("call_id"):
                # Function call started - track it
                call_id = item["call_id"]
                self.pending_function_calls[call_id] = {
                    "name": item.get("name", ""),
                    "arguments": ""
                }
                logger.info(f"Function call started: {call_id}")

        elif event_type == "response.function_call_arguments.delta":
            # Function call arguments streaming in
            call_id = event.get("call_id", "")
            delta = event.get("delta", "")
            name = event.get("name")
            
            if call_id in self.pending_function_calls:
                self.pending_function_calls[call_id]["arguments"] += delta
                if name:
                    self.pending_function_calls[call_id]["name"] = name
            else:
                # First delta, create entry
                self.pending_function_calls[call_id] = {
                    "name": name or "",
                    "arguments": delta
                }

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
            
            # Get function call info (from deltas or from done event)
            if call_id in self.pending_function_calls:
                func_call = self.pending_function_calls.pop(call_id)
                name = func_call["name"] or event.get("name", "")
                arguments = func_call["arguments"] or event.get("arguments", "")
            else:
                name = event.get("name", "")
                arguments = event.get("arguments", "")
            
            logger.info(f"Function call completed: {name}({arguments})")
            
            # Execute function and send result back
            if self.loop:
                asyncio.run_coroutine_threadsafe(
                    self._execute_and_send_function_result(call_id, name, arguments),
                    self.loop
                )

        elif event_type == "error":
            # Error occurred
            error_msg = event.get("error", {}).get("message", "Unknown error")
            logger.error(f"Realtime API error: {error_msg}")

    async def _execute_and_send_function_result(
        self, call_id: str, name: str, arguments: str
    ) -> None:
        """Execute function and send result back to OpenAI."""
        try:
            from .function_executors import execute_function
            
            # Execute function
            result = await execute_function(name, arguments)
            
            # Log to voice trace
            if self.voice_trace_client:
                await self.voice_trace_client.log_function_call(
                    name, arguments, result["output"]
                )
            
            logger.info(f"Function result: {result['output'][:100]}...")
            
            # Send result back to OpenAI
            if self.webrtc_client:
                await self.webrtc_client.send_event({
                    "type": "conversation.item.create",
                    "item": {
                        "type": "function_call_output",
                        "call_id": call_id,
                        "output": result["output"]
                    }
                })
                
                # Request new response
                await self.webrtc_client.send_event({
                    "type": "response.create"
                })
                
                logger.info("Function result sent, requested new response")
            
        except Exception as e:
            logger.error(f"Error executing function {name}: {e}", exc_info=True)
            
            # Send error back to OpenAI
            if self.webrtc_client:
                await self.webrtc_client.send_event({
                    "type": "conversation.item.create",
                    "item": {
                        "type": "function_call_output",
                        "call_id": call_id,
                        "output": f"Error executing function: {str(e)}"
                    }
                })
                await self.webrtc_client.send_event({
                    "type": "response.create"
                })

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
        """Start recording (connection is already established)."""
        try:
            # Guard against starting while already recording
            if self.is_recording or self.current_session_active:
                logger.warning("Already recording or session active, ignoring")
                return
            
            self.is_recording = True
            self.current_session_active = True

            # Start voice trace session
            if self.voice_trace_client:
                await self.voice_trace_client.start_session()

            # Start audio recording (WebRTC connection already exists)
            if self.audio_handler:
                self.audio_handler.start_recording()

            logger.info("Recording started (using existing WebRTC connection)")

        except Exception as e:
            logger.error(f"Error starting recording: {e}")
            self.is_recording = False
            self.current_session_active = False

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
        """End current session (but keep WebRTC connection alive)."""
        try:
            # End the current session (connection stays alive for next use)
            self.current_session_active = False
            
            # End voice trace session
            if self.voice_trace_client:
                await self.voice_trace_client.end_session()
            
            logger.info("Session ended (WebRTC connection remains open for next use)")
                
        except Exception as e:
            logger.error(f"Error ending session: {e}")

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

            # End current session
            if self.current_session_active:
                await self._close_connection()
            
            # Now close the persistent WebRTC connection
            if self.webrtc_client:
                await self.webrtc_client.cleanup()
                logger.info("WebRTC connection closed")

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

