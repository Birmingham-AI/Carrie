"""
WebRTC Client for connecting to OpenAI Realtime API.

Establishes WebRTC connection and handles audio streaming and events.
"""

import logging
import json
import asyncio
import struct
import time
import numpy as np
from typing import Optional, Callable
import httpx
from aiortc import RTCPeerConnection, RTCSessionDescription, MediaStreamTrack
from av import AudioFrame as AVAudioFrame
from .config import config

logger = logging.getLogger(__name__)


class MicrophoneAudioTrack(MediaStreamTrack):
    """Audio track that streams microphone input from PyAudio."""

    kind = "audio"

    def __init__(self, sample_rate: int = 24000, channels: int = 1):
        """
        Initialize microphone audio track.

        Args:
            sample_rate: Audio sample rate
            channels: Number of audio channels
        """
        super().__init__()
        self.sample_rate = sample_rate
        self.channels = channels
        self.audio_queue: asyncio.Queue = asyncio.Queue()
        self._started = False
        self._pts = 0  # Presentation timestamp counter

    def add_audio_data(self, audio_data: bytes) -> None:
        """
        Add audio data to be sent.

        Args:
            audio_data: PCM audio data (16-bit, mono)
        """
        if self._started:
            self.audio_queue.put_nowait(audio_data)

    async def recv(self) -> Optional[AVAudioFrame]:
        """
        Receive audio frame to send through WebRTC.

        Returns:
            AudioFrame for WebRTC transmission
        """
        try:
            # Get audio data from queue
            audio_data = await asyncio.wait_for(self.audio_queue.get(), timeout=0.1)

            # Convert bytes to numpy array
            # audio_data is 16-bit PCM, mono
            num_samples = len(audio_data) // 2
            samples = np.frombuffer(audio_data, dtype=np.int16)

            # Create AV AudioFrame from numpy array
            # from_ndarray expects shape (channels, samples) for multi-channel
            # or (samples,) for mono, but we need to ensure it's a 2D array
            if self.channels == 1:
                samples_array = samples.reshape(1, -1)  # Shape: (1, num_samples)
            else:
                # For stereo, reshape appropriately
                samples_array = samples.reshape(self.channels, -1)

            frame = AVAudioFrame.from_ndarray(
                samples_array, format="s16", layout="mono" if self.channels == 1 else "stereo"
            )
            frame.rate = self.sample_rate
            frame.pts = self._pts
            self._pts += num_samples  # Increment PTS by number of samples

            return frame

        except asyncio.TimeoutError:
            # Return silence if no data available
            num_samples = self.sample_rate // 10  # 100ms of silence
            silence_samples = np.zeros(num_samples, dtype=np.int16)
            samples_array = silence_samples.reshape(1, -1)  # Shape: (1, num_samples)
            
            frame = AVAudioFrame.from_ndarray(
                samples_array, format="s16", layout="mono" if self.channels == 1 else "stereo"
            )
            frame.rate = self.sample_rate
            frame.pts = self._pts
            self._pts += num_samples
            return frame
        except Exception as e:
            logger.error(f"Error in microphone track recv: {e}")
            return None


class WebRTCClient:
    """WebRTC client for OpenAI Realtime API."""

    def __init__(
        self,
        on_audio_received: Optional[Callable[[bytes], None]] = None,
        on_event: Optional[Callable[[dict], None]] = None,
    ):
        """
        Initialize WebRTC client.

        Args:
            on_audio_received: Callback for received audio chunks
            on_event: Callback for Realtime API events
        """
        self.api_base_url = config.API_BASE_URL
        self.on_audio_received = on_audio_received
        self.on_event = on_event

        self.peer_connection: Optional[RTCPeerConnection] = None
        self.data_channel = None
        self.microphone_track: Optional[MicrophoneAudioTrack] = None
        self.ephemeral_key: Optional[str] = None
        self.is_connected = False
        self.audio_receive_task: Optional[asyncio.Task] = None

    async def get_ephemeral_token(self) -> str:
        """
        Get ephemeral token from backend.

        Returns:
            Ephemeral key for OpenAI API
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.api_base_url}/v1/realtime/session",
                    headers={"Content-Type": "application/json"},
                )

                if response.status_code != 200:
                    raise Exception(
                        f"Failed to create session: {response.status_code} - {response.text}"
                    )

                data = response.json()
                ephemeral_key = data.get("client_secret", {}).get("value")

                if not ephemeral_key:
                    raise Exception("No ephemeral key received from backend")

                logger.info("Got ephemeral token from backend")
                return ephemeral_key

        except Exception as e:
            logger.error(f"Error getting ephemeral token: {e}")
            raise

    async def connect(self) -> None:
        """Establish WebRTC connection to OpenAI Realtime API."""
        try:
            # Get ephemeral token
            self.ephemeral_key = await self.get_ephemeral_token()

            # Create peer connection
            self.peer_connection = RTCPeerConnection()

            # Create microphone track
            self.microphone_track = MicrophoneAudioTrack(
                sample_rate=config.AUDIO_SAMPLE_RATE,
                channels=config.AUDIO_CHANNELS,
            )
            self.microphone_track._started = True
            self.peer_connection.addTrack(self.microphone_track)

            # Handle incoming audio track
            @self.peer_connection.on("track")
            def on_track(track: MediaStreamTrack):
                logger.info(f"Received track: {track.kind}, id: {track.id}")
                if track.kind == "audio":
                    logger.info("Starting audio receive task")
                    self.audio_receive_task = asyncio.create_task(
                        self._handle_incoming_audio(track)
                    )
                else:
                    logger.warning(f"Received non-audio track: {track.kind}")

            # Create data channel for events
            self.data_channel = self.peer_connection.createDataChannel("oai-events")
            self.data_channel.on("message", self._handle_data_channel_message)

            # Create offer
            offer = await self.peer_connection.createOffer()
            await self.peer_connection.setLocalDescription(offer)

            # Exchange SDP with OpenAI
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://api.openai.com/v1/realtime?model=gpt-realtime",
                    headers={
                        "Authorization": f"Bearer {self.ephemeral_key}",
                        "Content-Type": "application/sdp",
                    },
                    content=offer.sdp,
                )

                # OpenAI returns 201 (Created) for successful SDP exchange, not 200
                if response.status_code not in [200, 201]:
                    raise Exception(
                        f"Failed to establish WebRTC connection: {response.status_code} - {response.text}"
                    )

                answer_sdp = response.text
                await self.peer_connection.setRemoteDescription(
                    RTCSessionDescription(sdp=answer_sdp, type="answer")
                )

            self.is_connected = True
            logger.info("WebRTC connection established")
            
            # Check for existing tracks (they might be available immediately)
            receivers = self.peer_connection.getReceivers()
            logger.info(f"Connection has {len(receivers)} receivers, {len(self.peer_connection.getSenders())} senders")
            for receiver in receivers:
                if receiver.track:
                    logger.info(f"Found existing receiver track: {receiver.track.kind}, id: {receiver.track.id}")
                    if receiver.track.kind == "audio" and not self.audio_receive_task:
                        logger.info("Starting audio receive task for existing track")
                        self.audio_receive_task = asyncio.create_task(
                            self._handle_incoming_audio(receiver.track)
                        )

        except Exception as e:
            logger.error(f"Error establishing WebRTC connection: {e}")
            await self.cleanup()
            raise

    def send_audio(self, audio_data: bytes) -> None:
        """
        Send audio data to OpenAI.

        Args:
            audio_data: PCM audio data (16-bit, mono)
        """
        if self.microphone_track and self.is_connected:
            self.microphone_track.add_audio_data(audio_data)

    async def _handle_incoming_audio(self, track: MediaStreamTrack) -> None:
        """
        Handle incoming audio from OpenAI.

        Args:
            track: Audio track from peer connection
        """
        logger.info("Audio receive handler started")
        try:
            frame_count = 0
            timeout_count = 0
            while self.is_connected:
                try:
                    # Wait for frame with timeout to allow checking connection status
                    frame = await asyncio.wait_for(track.recv(), timeout=1.0)
                    timeout_count = 0  # Reset timeout counter on successful receive
                    
                    if frame:
                        frame_count += 1
                        if frame_count == 1:
                            logger.info(f"Received first audio frame from OpenAI: {frame.sample_rate}Hz, {frame.samples} samples")
                        elif frame_count % 50 == 0:  # Log every 50 frames
                            logger.info(f"Received {frame_count} audio frames from OpenAI")
                        
                        if self.on_audio_received:
                            # Convert AudioFrame to bytes (PCM 16-bit)
                            # frame is an av.AudioFrame
                            import numpy as np

                            # Convert to numpy array
                            array = frame.to_ndarray()
                            logger.debug(f"Frame array shape: {array.shape}, dtype: {array.dtype}")

                            # Convert to 16-bit PCM bytes
                            # array shape: (channels, samples) or (samples,)
                            if len(array.shape) == 2:
                                # Multi-channel: take first channel or mix
                                audio_data = array[0].astype(np.int16).tobytes()
                            else:
                                # Mono
                                audio_data = array.astype(np.int16).tobytes()

                            logger.debug(f"Converted to {len(audio_data)} bytes of PCM audio")
                            self.on_audio_received(audio_data)
                        else:
                            logger.warning("on_audio_received callback not set")
                    else:
                        logger.debug("Received None frame from track")
                except asyncio.TimeoutError:
                    timeout_count += 1
                    if timeout_count % 10 == 0:  # Log every 10 timeouts
                        logger.debug(f"No audio frames received for {timeout_count} seconds (connection: {self.is_connected})")
                    continue
        except asyncio.CancelledError:
            logger.info("Audio receive handler cancelled")
        except Exception as e:
            logger.error(f"Error handling incoming audio: {e}", exc_info=True)

    def _handle_data_channel_message(self, message: str) -> None:
        """
        Handle messages from data channel.

        Args:
            message: JSON message string
        """
        try:
            event = json.loads(message)
            event_type = event.get("type", "")

            logger.debug(f"Received event: {event_type}")

            if self.on_event:
                self.on_event(event)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse data channel message: {e}")
        except Exception as e:
            logger.error(f"Error handling data channel message: {e}")

    async def send_event(self, event: dict) -> None:
        """
        Send event through data channel.

        Args:
            event: Event dictionary to send
        """
        if self.data_channel:
            state = self.data_channel.readyState
            logger.debug(f"Data channel state: {state}, event type: {event.get('type', 'unknown')}")
            if state == "open":
                try:
                    event_json = json.dumps(event)
                    self.data_channel.send(event_json)
                    logger.debug(f"Sent event: {event.get('type', 'unknown')}")
                except Exception as e:
                    logger.error(f"Error sending event: {e}")
            else:
                logger.warning(f"Data channel not open (state: {state}), cannot send event: {event.get('type', 'unknown')}")
        else:
            logger.warning("Data channel not available, cannot send event")

    async def cleanup(self) -> None:
        """Clean up WebRTC connection."""
        try:
            self.is_connected = False

            # Cancel audio receive task
            if self.audio_receive_task:
                self.audio_receive_task.cancel()
                try:
                    await self.audio_receive_task
                except asyncio.CancelledError:
                    pass
                self.audio_receive_task = None

            if self.data_channel:
                self.data_channel.close()
                self.data_channel = None

            if self.microphone_track:
                self.microphone_track._started = False

            if self.peer_connection:
                await self.peer_connection.close()
                self.peer_connection = None

            self.microphone_track = None
            self.ephemeral_key = None

            logger.info("WebRTC connection cleaned up")

        except Exception as e:
            logger.error(f"Error cleaning up WebRTC connection: {e}")

