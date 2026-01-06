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

        # Audio device indices
        self.output_device_index: Optional[int] = None

        # Recording state
        self.is_recording = False
        self.recording_thread: Optional[threading.Thread] = None

        # Playback queue
        self.playback_queue: queue.Queue = queue.Queue()
        self.is_playing = False
        self.playback_thread: Optional[threading.Thread] = None

        # Detect and set USB audio device for output
        self._detect_usb_audio_device()

        # Check and adjust sample rate if needed
        self._validate_sample_rate()

        logger.info(
            f"Audio handler initialized: {self.sample_rate}Hz, "
            f"{self.channels} channel(s), chunk_size={self.chunk_size}"
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

    def play_audio(self, audio_data: bytes) -> None:
        """
        Queue audio data for playback.

        Args:
            audio_data: Audio data to play (PCM format)
        """
        self.playback_queue.put(audio_data)
        logger.debug(f"Queued {len(audio_data)} bytes for playback")

        # Start playback thread if not already running
        if not self.is_playing:
            self._start_playback()

    def _start_playback(self) -> None:
        """Start playback thread."""
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
            }
            
            # Use USB audio device if detected
            if self.output_device_index is not None:
                stream_kwargs["output_device_index"] = self.output_device_index
                device_info = self.audio.get_device_info_by_index(self.output_device_index)
                logger.debug(f"Opening output stream on USB device: {device_info['name']}")
            
            self.output_stream = self.audio.open(**stream_kwargs)

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

