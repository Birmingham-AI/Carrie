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
from scipy import signal
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

        # Debug audio recording
        self.debug_recording_enabled = config.DEBUG_AUDIO_RECORDING
        self.debug_output_dir = config.DEBUG_AUDIO_OUTPUT_DIR
        self.debug_audio_saved_this_session = False
        self.debug_audio_buffer: list[bytes] = []
        
        if self.debug_recording_enabled:
            logger.info(f"Debug audio recording ENABLED - will save to: {self.debug_output_dir}")
        else:
            logger.debug("Debug audio recording disabled")

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
            # Reset debug recording flag for new session
            self.debug_audio_saved_this_session = False
            self.debug_audio_buffer = []
            
            # Ensure clean state before starting new connection
            # Cancel any existing audio receive task from previous connection
            if self.audio_receive_task:
                logger.warning("Found existing audio_receive_task, cancelling before new connection")
                self.audio_receive_task.cancel()
                try:
                    await self.audio_receive_task
                except (asyncio.CancelledError, Exception):
                    pass
                self.audio_receive_task = None
            
            # Reset connection state
            self.is_connected = False
            
            # Get ephemeral token
            self.ephemeral_key = await self.get_ephemeral_token()

            # Create peer connection
            self.peer_connection = RTCPeerConnection()

            # Create microphone track (always mono for OpenAI)
            self.microphone_track = MicrophoneAudioTrack(
                sample_rate=config.AUDIO_SAMPLE_RATE,
                channels=config.AUDIO_INPUT_CHANNELS,  # Always 1 (mono) for microphone
            )
            self.microphone_track._started = True
            self.peer_connection.addTrack(self.microphone_track)

            # Handle incoming audio track
            @self.peer_connection.on("track")
            def on_track(track: MediaStreamTrack):
                logger.info(f"Received track: {track.kind}, id: {track.id}")
                if track.kind == "audio":
                    # Only start audio receive task if connection is established and task doesn't exist
                    if self.is_connected and not self.audio_receive_task:
                        logger.info("Starting audio receive task")
                        self.audio_receive_task = asyncio.create_task(
                            self._handle_incoming_audio(track)
                        )
                    elif self.audio_receive_task:
                        logger.warning("Audio receive task already exists, ignoring new track")
                    else:
                        logger.warning("Connection not yet established, will start audio handler after connection")
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

            # Set connection state before checking for tracks
            self.is_connected = True
            logger.info("WebRTC connection established")
            
            # Wait a brief moment for tracks to be established
            await asyncio.sleep(0.1)
            
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
            first_frame_timeout = 5.0  # Wait up to 5 seconds for first frame
            subsequent_timeout = 1.0  # 1 second timeout for subsequent frames
            
            # Wait for connection to be fully established
            if not self.is_connected:
                logger.warning("Connection not yet established, waiting...")
                wait_count = 0
                while not self.is_connected and wait_count < 10:
                    await asyncio.sleep(0.1)
                    wait_count += 1
                if not self.is_connected:
                    logger.error("Connection not established after waiting, exiting audio handler")
                    return
            
            while self.is_connected:
                try:
                    # Use longer timeout for first frame (audio may take time to start)
                    timeout = first_frame_timeout if frame_count == 0 else subsequent_timeout
                    # Wait for frame with timeout to allow checking connection status
                    frame = await asyncio.wait_for(track.recv(), timeout=timeout)
                    timeout_count = 0  # Reset timeout counter on successful receive
                    first_frame_timeout = subsequent_timeout  # Use shorter timeout after first frame
                    
                    if frame:
                        frame_count += 1
                        if frame_count == 1:
                            logger.info(
                                f"Received first audio frame from OpenAI: "
                                f"sample_rate={frame.sample_rate}Hz (reported), "
                                f"samples={frame.samples}, "
                                f"format={frame.format}, "
                                f"layout={frame.layout}"
                            )
                            logger.info(
                                f"Output stream configured for: {config.AUDIO_SAMPLE_RATE}Hz, "
                                f"channels: {config.AUDIO_OUTPUT_CHANNELS}"
                            )
                            logger.warning(
                                f"OpenAI metadata reports {frame.sample_rate}Hz, but actual audio data is 96kHz. "
                                f"Will treat as 96kHz and resample to {config.AUDIO_SAMPLE_RATE}Hz for playback."
                            )
                        elif frame_count % 250 == 0:  # Log every 250 frames (less verbose)
                            logger.info(f"Received {frame_count} audio frames from OpenAI")
                        
                        if self.on_audio_received:
                            try:
                                # Convert AudioFrame to bytes (PCM 16-bit)
                                import numpy as np

                                # Convert to numpy array (in native format)
                                array = frame.to_ndarray()

                                # Detect layout information FIRST (before any conversion)
                                is_stereo = False
                                num_channels = 1
                                try:
                                    if hasattr(frame.layout, 'name'):
                                        is_stereo = frame.layout.name == 'stereo'
                                    if hasattr(frame.layout, 'channels'):
                                        num_channels = len(frame.layout.channels)
                                    elif hasattr(frame.layout, 'channel_count'):
                                        num_channels = frame.layout.channel_count
                                except:
                                    pass

                                # Log first frame details
                                if frame_count == 1:
                                    logger.info(
                                        f"Frame format: layout={frame.layout}, dtype={array.dtype}, "
                                        f"shape={array.shape}, samples={frame.samples}"
                                    )

                                # Handle dtype conversion and stereo-to-mono in one pass
                                if array.dtype == np.float32 or array.dtype == np.float64:
                                    # Float audio: normalized -1.0 to 1.0
                                    
                                    # Handle channel conversion
                                    if is_stereo and config.AUDIO_OUTPUT_CHANNELS == 1:
                                        # Convert stereo to mono (mix both channels)
                                        # Reshape if needed for interleaved data
                                        if len(array.shape) == 2 and array.shape[0] == 1 and array.shape[1] == frame.samples * 2:
                                            # Interleaved stereo: reshape to planar
                                            array = array.reshape(2, frame.samples)
                                        
                                        if len(array.shape) == 2 and array.shape[0] == 2:
                                            # Planar stereo: average at float level (safe here)
                                            array = (array[0] + array[1]) / 2.0
                                        elif len(array.shape) == 1:
                                            # Interleaved: take left channel
                                            array = array[::2]
                                        else:
                                            # Unknown format: take first channel
                                            array = array[0] if len(array.shape) == 2 else array
                                    elif is_stereo and config.AUDIO_OUTPUT_CHANNELS == 2:
                                        # Keep stereo as-is, just ensure proper shape
                                        # Reshape if needed for interleaved data
                                        if len(array.shape) == 2 and array.shape[0] == 1 and array.shape[1] == frame.samples * 2:
                                            # Interleaved stereo: reshape to planar [2, samples]
                                            array = array.reshape(2, frame.samples)
                                        # If already planar [2, samples], keep as-is
                                    elif len(array.shape) == 2 and config.AUDIO_OUTPUT_CHANNELS == 1:
                                        # Multi-channel non-stereo audio, output wants mono: take first channel
                                        array = array[0]
                                    elif len(array.shape) == 1 and config.AUDIO_OUTPUT_CHANNELS == 2:
                                        # Mono input but stereo output requested: duplicate to both channels
                                        array = np.array([array, array])
                                    
                                    # Scale to int16 range
                                    audio_array = (np.clip(array, -1.0, 1.0) * 32767).astype(np.int16)
                                    
                                    if frame_count == 1:
                                        logger.info(f"Converted float to int16, shape={audio_array.shape}, max_amp={np.abs(audio_array).max()}")

                                elif array.dtype == np.int16:
                                    # Already int16
                                    
                                    # Handle channel conversion
                                    if is_stereo and config.AUDIO_OUTPUT_CHANNELS == 1:
                                        # Convert stereo to mono (mix both channels with SUM+CLIP to preserve volume)
                                        # Reshape if needed for interleaved data
                                        if len(array.shape) == 2 and array.shape[0] == 1 and array.shape[1] == frame.samples * 2:
                                            # Interleaved stereo: reshape to planar
                                            array = array.reshape(2, frame.samples)
                                        
                                        if len(array.shape) == 2 and array.shape[0] == 2:
                                            # Planar stereo: SUM and clip (preserves volume)
                                            audio_array = np.clip(
                                                array[0].astype(np.int32) + array[1].astype(np.int32),
                                                -32768, 32767
                                            ).astype(np.int16)
                                            
                                            if frame_count == 1:
                                                logger.info(f"Stereo->mono with sum+clip, max_amp={np.abs(audio_array).max()}")
                                        elif len(array.shape) == 1:
                                            # Interleaved: take left channel
                                            audio_array = array[::2]
                                        else:
                                            # Unknown: use first channel or flatten
                                            audio_array = array[0] if len(array.shape) == 2 else array
                                    elif is_stereo and config.AUDIO_OUTPUT_CHANNELS == 2:
                                        # Keep stereo as-is, just ensure proper shape
                                        # Reshape if needed for interleaved data
                                        if len(array.shape) == 2 and array.shape[0] == 1 and array.shape[1] == frame.samples * 2:
                                            # Interleaved stereo: reshape to planar [2, samples]
                                            array = array.reshape(2, frame.samples)
                                        # If already planar [2, samples], keep as-is
                                        audio_array = array
                                    elif len(array.shape) == 2 and config.AUDIO_OUTPUT_CHANNELS == 1:
                                        # Multi-channel non-stereo audio, output wants mono: take first channel
                                        audio_array = array[0]
                                    elif len(array.shape) == 1 and config.AUDIO_OUTPUT_CHANNELS == 2:
                                        # Mono input but stereo output requested: duplicate to both channels
                                        audio_array = np.array([array, array])
                                    else:
                                        # Already correct format
                                        audio_array = array
                                    
                                    if frame_count == 1:
                                        logger.info(f"Using int16 audio, shape={audio_array.shape}, max_amp={np.abs(audio_array).max()}")
                                else:
                                    # Unexpected dtype: convert to int16
                                    logger.warning(f"Unexpected dtype {array.dtype}, converting to int16")
                                    audio_array = array.astype(np.int16)
                                    if len(array.shape) == 2:
                                        audio_array = array[0]

                                # Resample if sample rate mismatch
                                # IMPORTANT: OpenAI sends 96kHz audio but frame.sample_rate may incorrectly report 48kHz
                                # Always treat OpenAI audio as 96kHz regardless of frame metadata
                                # Using Kaiser window for high-quality downsampling to reduce aliasing artifacts
                                actual_source_rate = 96000  # OpenAI's actual output rate
                                target_rate = config.AUDIO_SAMPLE_RATE
                                
                                if actual_source_rate != target_rate:
                                    # Handle resampling for both mono and stereo
                                    if len(audio_array.shape) == 2 and audio_array.shape[0] == 2:
                                        # Stereo: resample each channel independently
                                        original_samples = audio_array.shape[1]
                                        target_samples = int(original_samples * target_rate / actual_source_rate)
                                        
                                        if frame_count == 1:
                                            logger.info(
                                                f"Resampling stereo OpenAI audio: {actual_source_rate}Hz -> {target_rate}Hz "
                                                f"({original_samples} samples per channel -> {target_samples} samples per channel)"
                                            )
                                            logger.info("Using FFT-based resampling for high quality 2:1 downsampling")
                                        
                                        # Resample each channel
                                        left_resampled = signal.resample(audio_array[0], target_samples)
                                        right_resampled = signal.resample(audio_array[1], target_samples)
                                        
                                        # Clip and convert to int16
                                        left_int16 = np.clip(left_resampled, -32768, 32767).astype(np.int16)
                                        right_int16 = np.clip(right_resampled, -32768, 32767).astype(np.int16)
                                        
                                        # Stack back to planar [2, samples]
                                        audio_array = np.array([left_int16, right_int16])
                                        
                                    else:
                                        # Mono: resample as before
                                        original_samples = len(audio_array)
                                        target_samples = int(original_samples * target_rate / actual_source_rate)
                                        
                                        if frame_count == 1:
                                            logger.info(
                                                f"Resampling mono OpenAI audio: {actual_source_rate}Hz -> {target_rate}Hz "
                                                f"({original_samples} samples -> {target_samples} samples)"
                                            )
                                            logger.info("Using FFT-based resampling for high quality 2:1 downsampling")
                                        
                                        resampled_float = signal.resample(audio_array, target_samples)
                                        audio_array = np.clip(resampled_float, -32768, 32767).astype(np.int16)
                                else:
                                    if frame_count == 1:
                                        logger.info(
                                            f"No resampling needed: actual rate {actual_source_rate}Hz matches output rate {target_rate}Hz"
                                        )
                                
                                # Convert stereo planar to interleaved if needed (PyAudio expects interleaved)
                                if len(audio_array.shape) == 2 and audio_array.shape[0] == 2:
                                    # Planar stereo [2, samples] -> Interleaved [samples*2] (L,R,L,R,L,R...)
                                    left_channel = audio_array[0]
                                    right_channel = audio_array[1]
                                    interleaved = np.empty((audio_array.shape[1] * 2,), dtype=np.int16)
                                    interleaved[0::2] = left_channel   # Left channel at even indices
                                    interleaved[1::2] = right_channel  # Right channel at odd indices
                                    audio_array = interleaved
                                    
                                    if frame_count == 1:
                                        logger.info("Converted stereo planar to interleaved format for PyAudio")
                                
                                # Convert to bytes
                                audio_data = audio_array.tobytes()
                                
                                # Check audio quality periodically (not just first frame)
                                if frame_count == 1:
                                    # Check if audio contains actual sound
                                    non_zero_samples = np.count_nonzero(audio_array)
                                    max_amplitude = np.abs(audio_array).max()
                                    # Only log if there's actual audio content (skip silence)
                                    if non_zero_samples > 0 or max_amplitude > 0:
                                        logger.info(
                                            f"First frame: {len(audio_data)} bytes, "
                                            f"non-zero: {non_zero_samples}/{len(audio_array)}, "
                                            f"max_amp: {max_amplitude}"
                                        )
                                    else:
                                        logger.warning("First audio frame is all zeros (silence) - OpenAI may not have generated response")
                                    
                                    if max_amplitude > 0 and max_amplitude < 100:
                                        logger.warning(f"Audio amplitude very low (max: {max_amplitude})")
                                elif frame_count == 10:
                                    # Check 10th frame to verify audio is actually coming through
                                    non_zero_samples = np.count_nonzero(audio_array)
                                    max_amplitude = np.abs(audio_array).max()
                                    if non_zero_samples == 0:
                                        logger.error("ERROR: 10th frame is still all zeros - no audio received!")
                                    elif max_amplitude < 100:
                                        logger.warning(f"10th frame amplitude still low (max: {max_amplitude})")
                                    else:
                                        logger.info(f"10th frame has audio: max_amp={max_amplitude}, non_zero={non_zero_samples}/{len(audio_array)}")
                                
                                # Debug: Save first response audio to file
                                if (self.debug_recording_enabled 
                                    and not self.debug_audio_saved_this_session 
                                    and len(audio_data) > 0):
                                    # Check if audio contains actual sound (not just silence)
                                    non_zero_samples = np.count_nonzero(audio_array)
                                    if non_zero_samples > 0:
                                        self.debug_audio_buffer.append(audio_data)
                                        
                                        # Save after 10 seconds of audio (10s * 48000Hz * 2 bytes = ~960KB)
                                        total_bytes = sum(len(chunk) for chunk in self.debug_audio_buffer)
                                        target_bytes = 10 * config.AUDIO_SAMPLE_RATE * config.AUDIO_FORMAT_BYTES
                                        
                                        # Log progress on first frame
                                        if len(self.debug_audio_buffer) == 1:
                                            logger.info(
                                                f"Debug recording started: target={target_bytes} bytes "
                                                f"({target_bytes / (config.AUDIO_SAMPLE_RATE * config.AUDIO_FORMAT_BYTES):.1f}s)"
                                            )
                                        
                                        if total_bytes >= target_bytes:
                                            logger.info(f"Debug recording threshold reached: {total_bytes}/{target_bytes} bytes, saving file...")
                                            self._save_debug_audio()
                                            self.debug_audio_saved_this_session = True
                                            self.debug_audio_buffer = []  # Clear buffer
                                        elif len(self.debug_audio_buffer) % 100 == 0:
                                            # Log progress every 100 chunks
                                            logger.debug(
                                                f"Debug recording progress: {total_bytes}/{target_bytes} bytes "
                                                f"({len(self.debug_audio_buffer)} chunks buffered)"
                                            )
                                    elif frame_count == 1:
                                        logger.warning("Debug recording: first frame is silence, skipping")
                                
                                self.on_audio_received(audio_data)
                            except Exception as e:
                                logger.error(f"Error processing audio frame {frame_count}: {e}", exc_info=True)
                        else:
                            logger.warning("on_audio_received callback not set")
                    else:
                        logger.debug("Received None frame from track")
                except asyncio.TimeoutError:
                    timeout_count += 1
                    # Wait longer before giving up - audio might still be coming
                    max_timeouts = 10 if frame_count == 0 else 5  # Changed from 3 to 5
                    
                    if timeout_count >= max_timeouts:
                        if frame_count == 0:
                            logger.error(
                                f"No audio frames received after {timeout_count * timeout:.1f} seconds. "
                                f"Connection: {self.is_connected}. Exiting handler."
                            )
                        else:
                            logger.info(
                                f"No audio frames for {timeout_count} seconds after {frame_count} frames. "
                                f"Stream complete. Exiting handler."
                            )
                        break
                    
                    # Log periodically, more frequently for first frame wait
                    log_interval = 5 if frame_count == 0 else 10
                    if timeout_count % log_interval == 0:
                        logger.debug(
                            f"No audio frames received for {timeout_count * timeout:.1f} seconds "
                            f"(connection: {self.is_connected}, frames received: {frame_count})"
                        )
                    continue
        except asyncio.CancelledError:
            logger.info("Audio receive handler cancelled")
        except Exception as e:
            logger.error(f"Error handling incoming audio: {e}", exc_info=True)
        finally:
            if frame_count == 0:
                logger.warning(
                    f"Audio receive handler finished without processing any frames. "
                    f"Connection state: {self.is_connected}"
                )
            else:
                logger.info(f"Audio receive handler finished after processing {frame_count} frames")

    def _save_debug_audio(self) -> None:
        """Save debug audio buffer to file for verification."""
        try:
            import os
            from datetime import datetime
            
            logger.info(f"Starting debug audio save: {len(self.debug_audio_buffer)} chunks buffered")
            
            # Create output directory if it doesn't exist
            os.makedirs(self.debug_output_dir, exist_ok=True)
            logger.debug(f"Output directory created/verified: {self.debug_output_dir}")
            
            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"debug_audio_{timestamp}.pcm"
            filepath = os.path.join(self.debug_output_dir, filename)
            logger.debug(f"Writing to file: {filepath}")
            
            # Write audio data
            with open(filepath, "wb") as f:
                for chunk in self.debug_audio_buffer:
                    f.write(chunk)
            
            # Calculate duration
            total_bytes = sum(len(chunk) for chunk in self.debug_audio_buffer)
            total_samples = total_bytes // config.AUDIO_FORMAT_BYTES
            duration_sec = total_samples / config.AUDIO_SAMPLE_RATE
            
            logger.info(
                f"✓ DEBUG AUDIO SAVED: {filepath}"
            )
            logger.info(
                f"  Size: {total_bytes} bytes ({duration_sec:.1f}s)"
            )
            logger.info(
                f"  Format: {config.AUDIO_SAMPLE_RATE}Hz, {config.AUDIO_OUTPUT_CHANNELS}ch, 16-bit PCM"
            )
            logger.info(
                f"  To play: aplay -f S16_LE -r {config.AUDIO_SAMPLE_RATE} -c {config.AUDIO_OUTPUT_CHANNELS} {filepath}"
            )
            
        except Exception as e:
            logger.error(f"Failed to save debug audio: {e}", exc_info=True)

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
            # Set connection state to False FIRST to stop handlers
            self.is_connected = False
            
            # Cancel and cleanup audio receive task immediately
            if self.audio_receive_task:
                if not self.audio_receive_task.done():
                    self.audio_receive_task.cancel()
                    # Don't wait for it - just cancel and move on
                self.audio_receive_task = None
            
            # Close data channel
            if self.data_channel:
                try:
                    self.data_channel.close()
                except:
                    pass
                self.data_channel = None
            
            # Stop microphone track
            if self.microphone_track:
                self.microphone_track._started = False
                self.microphone_track = None
            
            # Close peer connection
            if self.peer_connection:
                try:
                    await asyncio.wait_for(self.peer_connection.close(), timeout=2.0)
                except asyncio.TimeoutError:
                    logger.warning("Peer connection close timed out")
                except Exception as e:
                    logger.debug(f"Error closing peer connection: {e}")
                self.peer_connection = None
            
            self.ephemeral_key = None
            logger.info("WebRTC connection cleaned up")
            
        except Exception as e:
            logger.error(f"Error cleaning up WebRTC connection: {e}")

