# Raspberry Pi Voice Client

A standalone Python application for Raspberry Pi that provides push-to-talk voice interaction with the Carrie AI system.

## Hardware Requirements

- Raspberry Pi (Model 3B+ or newer recommended)
- USB microphone or 3.5mm microphone with USB adapter
- Speakers or headphones (3.5mm or USB)
- Push button (momentary switch)
- Jumper wires for GPIO connection
- Optional: Resistor (10kΩ) for pull-up/pull-down if button doesn't have built-in resistor

## Software Requirements

- Raspberry Pi OS (or compatible Linux distribution)
- Python 3.9 or higher

**IMPORTANT: Install system dependencies BEFORE installing Python packages:**

```bash
sudo apt-get update
sudo apt-get install -y portaudio19-dev python3-dev build-essential swig liblgpio-dev
```

These are required for building PyAudio and rpi-lgpio. Without them, `pip install -r requirements.txt` will fail with compilation errors.

**Note:** `liblgpio-dev` provides the system `lgpio` library that `rpi-lgpio` Python package depends on.

## Setup

1. **Clone the repository** (if not already done):
   ```bash
   cd /path/to/willAIam
   ```

2. **Navigate to the project directory**:
   ```bash
   cd pi-voice-client
   ```

3. **Install system dependencies** (REQUIRED - do this first):
   ```bash
   sudo apt-get update
   sudo apt-get install -y portaudio19-dev python3-dev build-essential swig liblgpio-dev
   ```
   
   **Note:** These must be installed BEFORE creating the virtual environment and installing Python packages. PyAudio and rpi-lgpio require these system libraries to compile. The `liblgpio-dev` package provides the system `lgpio` library that the Python `rpi-lgpio` package depends on.

4. **Create virtual environment** (recommended):
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

5. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

6. **Configure environment variables**:
   ```bash
   cp .env.example .env
   nano .env  # Edit with your settings
   ```

   Key settings:
   - `API_BASE_URL`: Your backend API URL (default: `http://localhost:8001`)
   - `BUTTON_GPIO_PIN`: GPIO pin number for button (default: 22)
   - Audio settings: Usually don't need to change defaults

7. **Wire the button**:
   - Connect one side of button to GPIO pin (default: GPIO 22)
   - Connect other side to GND
   - Optional: Add 10kΩ pull-up resistor between GPIO pin and 3.3V

## GPIO Pin Configuration

Default button pin: **GPIO 22** (Physical pin 15)

To use a different pin, set `BUTTON_GPIO_PIN` in `.env` file.

Common GPIO pins:
- GPIO 22 (Physical pin 15) - Default
- GPIO 23 (Physical pin 16)
- GPIO 24 (Physical pin 18)
- GPIO 25 (Physical pin 22)

## Running the Application

```bash
# Activate virtual environment (if using one)
source venv/bin/activate

# Run the application as a module (recommended)
python -m src.main
```

**Note:** The application uses relative imports, so it must be run as a module using `python -m src.main`. Running `python src/main.py` directly will not work due to import path issues.

## Usage

1. **Press and hold the button** to start recording
2. **Speak your question** while holding the button
3. **Release the button** to send the audio and get a response
4. The response will play automatically through your speakers

## Troubleshooting

### Audio Issues

**No audio input detected:**
- Check microphone is connected and recognized: `arecord -l`
- Test microphone: `arecord -d 5 test.wav && aplay test.wav`
- Verify audio device permissions

**No audio output:**
- Check speakers are connected: `aplay -l`
- Test speakers: `speaker-test -t sine -f 1000`
- Adjust volume: `alsamixer`

### GPIO Issues

**Button not detected:**
- Verify wiring (GPIO pin to button to GND)
- Check GPIO pin number in `.env` matches your wiring
- Test button with: `gpio readall` (if installed)
- Ensure button makes good contact

**Multiple triggers from single press:**
- Add hardware debouncing (capacitor or resistor)
- Check button quality (may need better switch)

### Network Issues

**Cannot connect to backend API:**
- Verify `API_BASE_URL` in `.env` is correct
- Check backend is running: `curl http://localhost:8001/`
- Check network connectivity: `ping <backend-host>`
- Verify firewall allows connections

**WebRTC connection fails:**
- Check OpenAI API key is configured on backend
- Verify backend `/v1/realtime/session` endpoint works
- Check internet connection (WebRTC requires stable connection)

### Installation Issues

**PyAudio build fails with "portaudio.h: No such file or directory":**
- This means system dependencies are missing
- Install required packages: `sudo apt-get install -y portaudio19-dev python3-dev build-essential swig`
- Then retry: `pip install -r requirements.txt`

**rpi-lgpio build fails with "swig: command not found":**
- Install swig: `sudo apt-get install -y swig build-essential python3-dev liblgpio-dev`
- Then retry: `pip install -r requirements.txt`

**rpi-lgpio build fails with "cannot find -llgpio":**
- This means the system `lgpio` library is missing
- Install: `sudo apt-get install -y liblgpio-dev`
- Then retry: `pip install -r requirements.txt`

**rpi-lgpio installation issues:**
- Ensure ALL system dependencies are installed: `sudo apt-get install -y build-essential python3-dev swig liblgpio-dev`
- The `liblgpio-dev` package provides the system library that rpi-lgpio Python package links against
- rpi-lgpio is required for newer Raspberry Pi kernels (6.6+). Older kernels may use RPi.GPIO
- Ensure you're running on a Raspberry Pi (not emulated)
- Check Python version: `python3 --version` (needs 3.9+)

**WebRTC/aiortc Issues:**
- Ensure system dependencies are installed: `sudo apt-get install portaudio19-dev python3-dev`
- Try reinstalling: `pip install --upgrade aiortc`
- Check Python version: `python3 --version` (needs 3.9+)

## Configuration

Edit `.env` file to customize:

- `API_BASE_URL`: Backend API URL
- `BUTTON_GPIO_PIN`: GPIO pin for button
- `AUDIO_SAMPLE_RATE`: Audio sample rate for playback (default: 48000 Hz)
  - Must match a rate supported by your USB audio device
  - OpenAI sends 48kHz audio via WebRTC
  - 48000Hz is supported by most USB audio devices
- `AUDIO_CHANNELS`: Audio channels (1 = mono, 2 = stereo)
- `AUDIO_CHUNK_SIZE`: Audio buffer size in frames
- `DEBUG_AUDIO_RECORDING`: Enable debug audio recording (default: false)
- `DEBUG_AUDIO_OUTPUT_DIR`: Directory for debug audio files (default: /tmp/willAIam_debug)

## Debug Audio Recording

To verify that audio is being received correctly, you can enable debug audio recording to save the first 10 seconds of each response to a file.

### Enable Debug Recording

Edit `.env` file:

```bash
DEBUG_AUDIO_RECORDING=true
DEBUG_AUDIO_OUTPUT_DIR=/tmp/willAIam_debug
```

### Playback Saved Audio

Debug audio is saved as raw PCM format. To play it back:

```bash
# The log will show the exact aplay command to use
aplay -f S16_LE -r 48000 -c 1 /tmp/willAIam_debug/debug_audio_20260109_120000.pcm
```

Parameters:
- `-f S16_LE`: 16-bit signed little-endian PCM
- `-r 48000`: Sample rate (48kHz)
- `-c 1`: Mono audio

### Notes

- Only the first response per session is saved (button press/release cycle)
- Files are saved with timestamp: `debug_audio_YYYYMMDD_HHMMSS.pcm`
- Silence-only audio is not saved (only saves if non-zero samples detected)
- The output directory is created automatically if it doesn't exist

## Architecture

The application consists of several components:

- **Button Handler**: Monitors GPIO button for push-to-talk
- **Audio Handler**: Records from microphone and plays to speakers
- **WebRTC Client**: Connects to OpenAI Realtime API
- **Voice Trace Client**: Logs events to backend for observability
- **Main Application**: Coordinates all components

## Development

To modify the code:

1. Make changes in `src/` directory
2. Test on Raspberry Pi
3. Check logs for errors

Enable debug logging by modifying log levels in `src/main.py`.

## License

Part of the willAIam project.

