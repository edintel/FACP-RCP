import threading
import logging
from config.schema import RelayConfig

class RelayController:
    def __init__(self, relay_config: RelayConfig):
        self.relay_pin = relay_config.pin
        self.relay_high_time = relay_config.high_time
        self.relay_low_time = relay_config.low_time
        self.is_raspberry_pi = self._is_raspberry_pi()
        self.GPIO = None

        if self.is_raspberry_pi:
            self._setup_gpio()

    def _is_raspberry_pi(self):
        try:
            with open('/sys/firmware/devicetree/base/model', 'r') as model:
                return 'Raspberry Pi' in model.read()
        except:
            return False

    def _setup_gpio(self):
        try:
            import RPi.GPIO as GPIO
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(self.relay_pin, GPIO.OUT)
            self.GPIO = GPIO
        except ImportError:
            logging.warning("RPi.GPIO module not found. Relay control will be disabled.")
            self.is_raspberry_pi = False

    def relay_control(self, shutdown_flag: threading.Event):
        if not self.is_raspberry_pi:
            logging.info("Relay control is disabled as this is not a Raspberry Pi.")
            return

        while not shutdown_flag.is_set():
            self.GPIO.output(self.relay_pin, self.GPIO.HIGH)
            if shutdown_flag.wait(self.relay_high_time):
                break
            self.GPIO.output(self.relay_pin, self.GPIO.LOW)
            if shutdown_flag.wait(self.relay_low_time):
                break

    def cleanup(self):
        if self.is_raspberry_pi and self.GPIO:
            self.GPIO.cleanup(self.relay_pin)