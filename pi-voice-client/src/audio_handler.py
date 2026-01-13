"""
Audio Handler for recording and playback.

Handles microphone input and speaker output using PyAudio.
"""

import logging
import pyaudio
import queue
import threading
import os
from pathlib import Path
from typing import Optional, Callable
import numpy as np
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
        self.input_channels = config.AUDIO_INPUT_CHANNELS  # Always mono for microphone
        self.output_channels = config.AUDIO_OUTPUT_CHANNELS  # Stereo or mono for speakers
        self.channels = self.output_channels  # Legacy: for backward compatibility with playback code
        self.chunk_size = config.AUDIO_CHUNK_SIZE
        self.format = PYAUDIO_FORMAT
        self.format_width = pyaudio.get_sample_size(self.format)

        # PyAudio instance
        self.audio = pyaudio.PyAudio()

        # Audio streams
        self.input_stream: Optional[pyaudio.Stream] = None
        self.output_stream: Optional[pyaudio.Stream] = None

        # Audio device indices
        self.output_device_index: Optional[int] = None

        # Recording state
        self.is_recording = False
        self.recording_thread: Optional[threading.Thread] = None

        # Playback queue
        self.playback_queue: queue.Queue = queue.Queue()
        self.is_playing = False
        self.playback_thread: Optional[threading.Thread] = None
        
        # Track consecutive empty callbacks for auto-stop
        self.empty_callback_count = 0
        self.max_empty_callbacks = 3000  # ~30 seconds at 100 callbacks/sec (adjust based on chunk_size)
        self.write_count = 0  # Track number of audio chunks written

        # Detect and set USB audio device for output
        self._detect_usb_audio_device()

        # Check and adjust sample rate if needed
        self._validate_sample_rate()

        logger.info(
            f"Audio handler initialized: {self.sample_rate}Hz, "
            f"input={self.input_channels}ch (mono), output={self.output_channels}ch, "
            f"chunk_size={self.chunk_size}"
        )
        if self.output_device_index is not None:
            output_info = self.audio.get_device_info_by_index(self.output_device_index)
            logger.info(f"Using USB audio output device: {output_info['name']} (index {self.output_device_index})")
        else:
            logger.info("Using default audio output device")

    def _detect_usb_audio_device(self) -> None:
        """
        Detect USB audio device from /proc/asound/modules and find corresponding PyAudio device.
        
        Sets self.output_device_index to the PyAudio device index if found.
        """
        try:
            # Read /proc/asound/modules to find USB audio devices
            modules_path = Path("/proc/asound/modules")
            if not modules_path.exists():
                logger.debug("/proc/asound/modules not found, using default audio device")
                return

            usb_audio_module_numbers = []
            with open(modules_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if 'snd_usb_audio' in line.lower():
                        # Extract module number (first field)
                        parts = line.split()
                        if parts:
                            usb_audio_module_numbers.append(parts[0])
            
            if not usb_audio_module_numbers:
                logger.debug("No snd_usb_audio modules found in /proc/asound/modules, using default audio device")
                return

            logger.info(f"Found USB audio module numbers: {', '.join(usb_audio_module_numbers)}")
            
            # Find PyAudio device that matches USB audio
            # Try multiple matching strategies:
            # 1. Match by device name containing "USB" or "usb"
            # 2. Match by ALSA device name (hw:X,0 where X is module number)
            device_count = self.audio.get_device_count()
            for i in range(device_count):
                try:
                    device_info = self.audio.get_device_info_by_index(i)
                    device_name = device_info.get('name', '')
                    device_name_lower = device_name.lower()
                    
                    # Check if this device has output channels
                    if device_info.get('maxOutputChannels', 0) == 0:
                        continue
                    
                    # Strategy 1: Check if device name contains USB-related keywords
                    usb_keywords = ['usb', 'snd_usb_audio']
                    if any(keyword in device_name_lower for keyword in usb_keywords):
                        self.output_device_index = i
                        logger.info(
                            f"Found USB audio output device by name: {device_name} "
                            f"(index {i}, {device_info['maxOutputChannels']} output channels)"
                        )
                        return
                    
                    # Strategy 2: Check if ALSA device name matches module number
                    # PyAudio device names might be like "hw:1,0" where 1 is the module number
                    for module_num in usb_audio_module_numbers:
                        if f"hw:{module_num}," in device_name or f"plughw:{module_num}," in device_name:
                            self.output_device_index = i
                            logger.info(
                                f"Found USB audio output device by ALSA name: {device_name} "
                                f"(index {i}, module {module_num}, {device_info['maxOutputChannels']} output channels)"
                            )
                            return
                            
                except Exception as e:
                    logger.debug(f"Error checking device {i}: {e}")
                    continue

            # If we found USB modules but no matching PyAudio device, log a warning
            logger.warning(
                f"Found USB audio modules ({', '.join(usb_audio_module_numbers)}) in /proc/asound/modules "
                f"but no matching PyAudio output device. Using default audio device."
            )
            logger.debug("Available audio output devices:")
            for i in range(device_count):
                try:
                    device_info = self.audio.get_device_info_by_index(i)
                    if device_info.get('maxOutputChannels', 0) > 0:
                        logger.debug(f"  Device {i}: {device_info.get('name', 'unknown')}")
                except:
                    pass

        except Exception as e:
            logger.warning(f"Error detecting USB audio device: {e}. Using default audio device.")

    def _validate_sample_rate(self) -> None:
        """Validate sample rate based on device capabilities."""
        try:
            # Get default input device
            default_input = self.audio.get_default_input_device_info()
            default_rate = int(default_input['defaultSampleRate'])
            device_name = default_input['name']
            
            logger.info(
                f"Default audio input device: {device_name} "
                f"(default sample rate: {default_rate}Hz)"
            )
            
            # Check if configured rate is supported
            try:
                # Try to open a test stream with the configured rate
                test_stream = self.audio.open(
                    format=self.format,
                    channels=self.channels,
                    rate=self.sample_rate,
                    input=True,
                    frames_per_buffer=self.chunk_size,
                )
                test_stream.close()
                logger.debug(f"Sample rate {self.sample_rate}Hz is supported by device")
                return  # Configured rate works
            except Exception as e:
                error_msg = str(e)
                logger.warning(
                    f"Sample rate {self.sample_rate}Hz may not be supported by audio device. "
                    f"Device default: {default_rate}Hz. Error: {error_msg}\n"
                    f"If recording fails, try one of the following:\n"
                    f"1. Configure ALSA to support {self.sample_rate}Hz\n"
                    f"2. Use a different audio device that supports {self.sample_rate}Hz\n"
                    f"3. Change AUDIO_SAMPLE_RATE in .env to a supported rate (e.g., {default_rate})"
                )
                # Don't change the rate automatically - let it fail with a clear error when recording starts
                # The user needs to either fix ALSA config or change the config
            
        except Exception as e:
            # If validation itself fails, log warning but continue
            # The actual error will be caught when trying to start recording
            logger.warning(f"Could not validate sample rate: {e}. Will attempt to use configured rate.")

    def start_recording(self) -> None:
        """Start recording from microphone."""
        if self.is_recording:
            logger.warning("Already recording")
            return

        try:
            # Open input stream (always mono for microphone)
            self.input_stream = self.audio.open(
                format=self.format,
                channels=self.input_channels,  # Use input_channels (mono)
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.chunk_size,
                stream_callback=self._input_callback,
            )

            self.is_recording = True
            self.input_stream.start_stream()
            logger.info(f"Started recording (mono, {self.sample_rate}Hz)")

        except Exception as e:
            error_msg = str(e)
            if "Invalid sample rate" in error_msg or "-9997" in error_msg:
                logger.error(
                    f"Failed to start recording: {error_msg}\n"
                    f"The audio device does not support {self.sample_rate}Hz.\n"
                    f"To fix this:\n"
                    f"1. Check your audio device's supported sample rates: arecord -l && arecord --dump-hw-params\n"
                    f"2. Try configuring ALSA to support {self.sample_rate}Hz\n"
                    f"3. Change AUDIO_SAMPLE_RATE in .env to a supported rate (common: 16000, 44100, 48000)"
                )
            else:
                logger.error(f"Failed to start recording: {error_msg}")
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

    def _output_callback(
        self, 
        in_data: bytes,  # Not used for output, but required by PyAudio signature
        frame_count: int, 
        time_info: dict, 
        status: int
    ) -> tuple[Optional[bytes], int]:
        """
        Callback for audio output stream.
        
        Args:
            in_data: Not used for output streams, but required by PyAudio signature
            frame_count: Number of frames requested
            time_info: Timing information
            status: Status flags
            
        Returns:
            Tuple of (audio_data_bytes, pyaudio.paContinue or pyaudio.paComplete)
        """
        if status:
            logger.warning(f"Audio output status: {status}")
        
        # Calculate required bytes
        bytes_needed = frame_count * self.channels * self.format_width
        
        try:
            # Try to get audio data from queue (non-blocking)
            audio_data = self.playback_queue.get_nowait()
            self.empty_callback_count = 0  # Reset empty counter on successful get
            
            # Log first few chunks with audio analysis
            if self.write_count < 10:
                import numpy as np
                audio_array = np.frombuffer(audio_data, dtype=np.int16)
                non_zero = np.count_nonzero(audio_array)
                max_amp = np.abs(audio_array).max() if len(audio_array) > 0 else 0
                logger.info(
                    f"Callback playing chunk {self.write_count + 1}: {len(audio_data)} bytes, "
                    f"non-zero={non_zero}/{len(audio_array)}, max_amp={max_amp}"
                )
            
            # Verify audio data size matches what we need
            if len(audio_data) != bytes_needed:
                # This should rarely happen now that play_audio() splits chunks, but handle gracefully
                if len(audio_data) < bytes_needed:
                    # Pad with silence if too small
                    logger.debug(
                        f"Audio chunk smaller than expected: got {len(audio_data)} bytes, "
                        f"expected {bytes_needed} bytes. Padding with silence."
                    )
                    audio_data += b'\x00' * (bytes_needed - len(audio_data))
                else:
                    # If larger, split it: use what we need and queue the remainder
                    remainder = audio_data[bytes_needed:]
                    audio_data = audio_data[:bytes_needed]
                    if len(remainder) > 0:
                        # Queue the remainder for next callback
                        self.playback_queue.put(remainder)
                        logger.debug(
                            f"Audio chunk larger than expected: split into {bytes_needed} bytes "
                            f"and queued {len(remainder)} bytes remainder"
                        )
            
            self.write_count += 1
            # Only log every 100 chunks to reduce verbosity
            if self.write_count % 100 == 0:
                queue_size = self.playback_queue.qsize()
                logger.info(
                    f"Callback: played {self.write_count} chunks, queue_size={queue_size}"
                )
            
            return (audio_data, pyaudio.paContinue)
            
        except queue.Empty:
            # Queue is empty - generate silence to keep stream alive
            self.empty_callback_count += 1
            
            # Log periodically for debugging (less frequently)
            if self.empty_callback_count % 1000 == 0:
                logger.debug(
                    f"Callback: queue empty (count: {self.empty_callback_count}/{self.max_empty_callbacks})"
                )
            
            # Generate silence bytes
            silence = b'\x00' * bytes_needed
            
            # Stop stream if queue has been empty for too long AND we've written some data
            # This allows initial silence but stops after extended empty period
            if self.empty_callback_count >= self.max_empty_callbacks and self.write_count > 0:
                logger.info(
                    f"Output callback: queue empty for {self.max_empty_callbacks} callbacks "
                    f"after writing {self.write_count} chunks. Stopping stream."
                )
                self.is_playing = False
                return (None, pyaudio.paComplete)
            
            # Return silence to keep stream alive
            return (silence, pyaudio.paContinue)
            
        except Exception as e:
            logger.error(f"Error in output callback: {e}", exc_info=True)
            # Return silence on error to prevent stream from stopping abruptly
            silence = b'\x00' * bytes_needed
            return (silence, pyaudio.paContinue)

    def play_audio(self, audio_data: bytes) -> None:
        """
        Queue audio data for playback.

        Args:
            audio_data: Audio data to play (PCM format)
        """
        if not audio_data:
            logger.warning("Attempted to queue empty audio data")
            return
        
        # Calculate expected chunk size based on stream configuration
        # This matches what the callback expects: chunk_size frames × channels × bytes per sample
        expected_chunk_size = self.chunk_size * self.channels * self.format_width
        
        # Log chunk size for verification on first call
        if not hasattr(self, '_chunk_size_logged'):
            logger.info(
                f"Audio playback chunk configuration: "
                f"chunk_size={self.chunk_size} frames, "
                f"channels={self.channels}, "
                f"format_width={self.format_width} bytes, "
                f"expected_chunk_size={expected_chunk_size} bytes"
            )
            self._chunk_size_logged = True
        
        # Check if audio contains actual sound (not just silence)
        import numpy as np
        audio_array = np.frombuffer(audio_data, dtype=np.int16)
        non_zero_samples = np.count_nonzero(audio_array)
        max_amplitude = np.abs(audio_array).max() if len(audio_array) > 0 else 0
        
        # Split large chunks into callback-sized chunks
        # This handles cases where WebRTC sends larger chunks than the callback expects
        offset = 0
        chunks_queued = 0
        while offset < len(audio_data):
            chunk = audio_data[offset:offset + expected_chunk_size]
            if len(chunk) > 0:
                self.playback_queue.put(chunk)
                chunks_queued += 1
                offset += len(chunk)
            else:
                break
        
        queue_size = self.playback_queue.qsize()
        # Only log audio characteristics for non-silence chunks (or if queue is large)
        # This reduces log spam from silence
        # if non_zero_samples > 0 or max_amplitude > 0:
        #     # Has actual audio content - log it
        #     if chunks_queued > 1:
        #         logger.info(
        #             f"Queued {len(audio_data)} bytes ({chunks_queued} chunks): "
        #             f"non-zero={non_zero_samples}/{len(audio_array)}, "
        #             f"max_amp={max_amplitude}, queue_size={queue_size}"
        #         )
        #     else:
        #         logger.debug(f"Queued {len(audio_data)} bytes ({chunks_queued} chunks, queue_size={queue_size})")
        # elif queue_size > 20:
        #     # Queue getting large, even with silence - log warning
        #     logger.warning(f"Queued silence, but queue_size is high: {queue_size}")

        # Start playback if not already playing
        if not self.is_playing:
            logger.info("Starting playback (was not playing)")
            self._start_playback()

    def _start_playback(self) -> None:
        """Start playback using callback-based streaming."""
        if self.is_playing:
            return

        try:
            # Open output stream (use USB audio device if detected)
            stream_kwargs = {
                "format": self.format,
                "channels": self.channels,
                "rate": self.sample_rate,
                "output": True,
                "frames_per_buffer": self.chunk_size,
                "stream_callback": self._output_callback,
            }
            
            # Use USB audio device if detected
            if self.output_device_index is not None:
                stream_kwargs["output_device_index"] = self.output_device_index
                device_info = self.audio.get_device_info_by_index(self.output_device_index)
                logger.info(
                    f"Opening output stream on USB device: {device_info['name']} "
                    f"(index {self.output_device_index}, rate: {self.sample_rate}Hz, "
                    f"channels: {self.channels}, format: {self.format})"
                )
            else:
                default_output = self.audio.get_default_output_device_info()
                logger.info(
                    f"Opening output stream on default device: {default_output['name']} "
                    f"(rate: {self.sample_rate}Hz, channels: {self.channels})"
                )
            
            logger.info(
                f"Config AUDIO_SAMPLE_RATE: {config.AUDIO_SAMPLE_RATE}Hz, "
                f"self.sample_rate: {self.sample_rate}Hz, "
                f"stream will use: {stream_kwargs['rate']}Hz"
            )
            
            self.output_stream = self.audio.open(**stream_kwargs)
            
            # Start the stream explicitly
            self.output_stream.start_stream()
            logger.info(f"Output stream started, active: {self.output_stream.is_active()}")
            
            # Get the actual stream parameters to verify
            try:
                # PyAudio streams don't expose rate directly, but we can check the device
                device_index = stream_kwargs.get("output_device_index")
                if device_index is not None:
                    device_info = self.audio.get_device_info_by_index(device_index)
                    device_rate = int(device_info.get('defaultSampleRate', 0))
                    logger.info(
                        f"Output stream opened: requested={self.sample_rate}Hz, "
                        f"device default={device_rate}Hz, active={self.output_stream.is_active()}"
                    )
                    if device_rate > 0 and abs(device_rate - self.sample_rate) > 100:
                        logger.warning(
                            f"Device default rate ({device_rate}Hz) differs significantly from "
                            f"requested rate ({self.sample_rate}Hz). Audio may play at wrong speed!"
                        )
                else:
                    default_output = self.audio.get_default_output_device_info()
                    device_rate = int(default_output.get('defaultSampleRate', 0))
                    logger.info(
                        f"Output stream opened: requested={self.sample_rate}Hz, "
                        f"device default={device_rate}Hz, active={self.output_stream.is_active()}"
                    )
                    if device_rate > 0 and abs(device_rate - self.sample_rate) > 100:
                        logger.warning(
                            f"Device default rate ({device_rate}Hz) differs significantly from "
                            f"requested rate ({self.sample_rate}Hz). Audio may play at wrong speed!"
                        )
            except Exception as e:
                logger.warning(f"Could not verify stream rate: {e}")
            logger.info(
                f"Output stream opened successfully, active: {self.output_stream.is_active()}"
            )

            # Reset callback tracking counters
            self.empty_callback_count = 0
            self.write_count = 0
            
            self.is_playing = True
            logger.info("Started playback (callback-based)")

        except Exception as e:
            logger.error(f"Failed to start playback: {e}")
            self.is_playing = False
            raise

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

            # Reset callback tracking counters
            self.empty_callback_count = 0
            self.write_count = 0

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

    def test_playback(self, duration_seconds: float = 1.0, frequency: int = 440) -> bool:
        """
        Test playback by generating and playing a test tone.
        
        Args:
            duration_seconds: Duration of test tone in seconds
            frequency: Frequency of test tone in Hz (default: 440Hz = A4)
            
        Returns:
            True if test tone was played successfully, False otherwise
        """
        try:
            logger.info(f"Testing playback with {frequency}Hz tone for {duration_seconds} seconds")
            
            # Generate test tone
            sample_rate = self.sample_rate
            num_samples = int(sample_rate * duration_seconds)
            t = np.linspace(0, duration_seconds, num_samples, False)
            tone = np.sin(2 * np.pi * frequency * t)
            
            # Convert to int16 PCM
            tone_int16 = (tone * 32767 * 0.5).astype(np.int16)  # 50% volume
            tone_bytes = tone_int16.tobytes()
            
            # Play the tone using play_audio (callback will handle it)
            if not self.is_playing:
                self._start_playback()
            
            # Wait a bit for stream to start
            import time
            time.sleep(0.1)
            
            # Queue the test tone - callback will play it automatically
            self.play_audio(tone_bytes)
            
            # Wait for playback to complete (approximate)
            time.sleep(duration_seconds + 0.1)
            
            logger.info("Test tone queued for playback")
            return True
                
        except Exception as e:
            logger.error(f"Error testing playback: {e}", exc_info=True)
            return False

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

