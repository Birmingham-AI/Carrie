"""
GPIO Button Handler for push-to-talk functionality.

Monitors a GPIO pin for button press/release events with debouncing.
"""

import logging
import time
import platform
from typing import Callable, Optional
import RPi.GPIO as GPIO
from .config import config

logger = logging.getLogger(__name__)


class ButtonHandler:
    """Handles GPIO button input with debouncing for push-to-talk."""

    # Debounce time in seconds (50ms)
    DEBOUNCE_TIME = 0.05

    def __init__(
        self,
        on_press: Optional[Callable[[], None]] = None,
        on_release: Optional[Callable[[], None]] = None,
    ):
        """
        Initialize button handler.

        Args:
            on_press: Callback function called when button is pressed
            on_release: Callback function called when button is released
        """
        self.gpio_pin = config.BUTTON_GPIO_PIN
        self.on_press = on_press
        self.on_release = on_release

        self.is_pressed = False
        self.last_state = GPIO.HIGH  # Button rests at HIGH with pull-up resistor
        self.last_state_change_time = 0.0

        # Check if we're on Raspberry Pi hardware
        machine = platform.machine()
        if machine not in ['armv7l', 'aarch64', 'armv6l']:
            raise RuntimeError(
                f"GPIO is only available on Raspberry Pi hardware. "
                f"Detected platform: {machine}. "
                f"This application must run on a Raspberry Pi."
            )

        try:
            # Suppress warnings about channels already in use
            GPIO.setwarnings(False)
            
            # Set GPIO mode (BCM pin numbering)
            GPIO.setmode(GPIO.BCM)
            
            # Clean up any existing event detection on this pin
            try:
                GPIO.remove_event_detect(self.gpio_pin)
            except (RuntimeError, ValueError):
                # Pin may not have event detection set up, which is fine
                pass
            
            # Setup GPIO pin as input with pull-up resistor
            GPIO.setup(self.gpio_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

            # Add event detection for both rising and falling edges
            GPIO.add_event_detect(
                self.gpio_pin,
                GPIO.BOTH,
                callback=self._edge_callback,
                bouncetime=int(self.DEBOUNCE_TIME * 1000),  # Convert to milliseconds
            )

            logger.info(f"Button handler initialized on GPIO {self.gpio_pin}")

        except RuntimeError as e:
            error_msg = str(e)
            if "channel" in error_msg.lower() or "already" in error_msg.lower():
                raise RuntimeError(
                    f"GPIO pin {self.gpio_pin} is already in use. "
                    f"This may happen if a previous instance didn't clean up properly. "
                    f"Try running: sudo python3 -c 'import RPi.GPIO as GPIO; GPIO.setmode(GPIO.BCM); GPIO.cleanup()'"
                ) from e
            raise RuntimeError(f"Failed to initialize GPIO pin {self.gpio_pin}: {e}") from e
        except Exception as e:
            raise RuntimeError(f"Failed to add edge detection on GPIO {self.gpio_pin}: {e}") from e

    def _edge_callback(self, channel: int) -> None:
        """
        Callback for GPIO edge detection.

        Args:
            channel: GPIO channel that triggered the event
        """
        current_time = time.time()

        # Additional software debouncing
        if current_time - self.last_state_change_time < self.DEBOUNCE_TIME:
            return

        # Read current state
        current_state = GPIO.input(self.gpio_pin)
        self.last_state_change_time = current_time

        # Button is active LOW (pressed = LOW, released = HIGH with pull-up)
        if current_state == GPIO.LOW and self.last_state == GPIO.HIGH:
            # Button pressed (falling edge)
            if not self.is_pressed:
                self.is_pressed = True
                logger.info("Button pressed")
                if self.on_press:
                    try:
                        self.on_press()
                    except Exception as e:
                        logger.error(f"Error in on_press callback: {e}")

        elif current_state == GPIO.HIGH and self.last_state == GPIO.LOW:
            # Button released (rising edge)
            if self.is_pressed:
                self.is_pressed = False
                logger.info("Button released")
                if self.on_release:
                    try:
                        self.on_release()
                    except Exception as e:
                        logger.error(f"Error in on_release callback: {e}")

        self.last_state = current_state

    def is_button_pressed(self) -> bool:
        """Check current button state (with debouncing)."""
        current_state = GPIO.input(self.gpio_pin)
        return current_state == GPIO.LOW  # Active LOW

    def cleanup(self) -> None:
        """Clean up GPIO resources."""
        try:
            GPIO.remove_event_detect(self.gpio_pin)
            GPIO.cleanup(self.gpio_pin)
            logger.info("Button handler cleaned up")
        except Exception as e:
            logger.error(f"Error cleaning up button handler: {e}")