import threading
import logging
import time
from config.schema import SilenceRelayConfig
from typing import Dict, Any

class SilenceController:
    def __init__(self, silence_config: SilenceRelayConfig, mqtt_handler):
        self.silence_pin = silence_config.pin
        self.activation_time = silence_config.activation_time
        self.active_high = silence_config.active_high
        self.mqtt_handler = mqtt_handler
        self.is_raspberry_pi = self._is_raspberry_pi()
        self.GPIO = None
        self.is_silencing = False
        self.silence_lock = threading.Lock()
        self.logger = logging.getLogger(__name__)

        if self.is_raspberry_pi:
            self._setup_gpio()
        else:
            self.logger.warning("Not running on Raspberry Pi. Silence control will be simulated.")

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
            GPIO.setup(self.silence_pin, GPIO.OUT)
            # Set initial state to inactive
            initial_state = GPIO.LOW if self.active_high else GPIO.HIGH
            GPIO.output(self.silence_pin, initial_state)
            self.GPIO = GPIO
            self.logger.info(f"Silence relay GPIO {self.silence_pin} configured successfully")
        except ImportError:
            self.logger.warning("RPi.GPIO module not found. Silence control will be disabled.")
            self.is_raspberry_pi = False
        except Exception as e:
            self.logger.error(f"Error setting up GPIO for silence relay: {e}")
            self.is_raspberry_pi = False

    def activate_silence(self):
        """Activa el relay de silencio por el tiempo configurado"""
        with self.silence_lock:
            if self.is_silencing:
                self.logger.warning("Silence already in progress, ignoring new request")
                return False

            self.is_silencing = True
            
        self.logger.info(f"Activating silence relay for {self.activation_time} seconds")
        
        # Publicar estado inicial
        self._publish_silence_state(True)
        
        if self.is_raspberry_pi and self.GPIO:
            try:
                # Activar el relay
                active_state = self.GPIO.HIGH if self.active_high else self.GPIO.LOW
                self.GPIO.output(self.silence_pin, active_state)
                self.logger.debug(f"Silence relay GPIO {self.silence_pin} set to {'HIGH' if self.active_high else 'LOW'}")
                
                # Esperar el tiempo configurado
                time.sleep(self.activation_time)
                
                # Desactivar el relay
                inactive_state = self.GPIO.LOW if self.active_high else self.GPIO.HIGH
                self.GPIO.output(self.silence_pin, inactive_state)
                self.logger.debug(f"Silence relay GPIO {self.silence_pin} set to {'LOW' if self.active_high else 'HIGH'}")
                
            except Exception as e:
                self.logger.error(f"Error controlling silence relay: {e}")
        else:
            self.logger.info(f"[SIMULATION] Silence relay would be active for {self.activation_time} seconds")
            time.sleep(self.activation_time)
        
        with self.silence_lock:
            self.is_silencing = False
        
        # Publicar estado final
        self._publish_silence_state(False)
        self.logger.info("Silence relay deactivated")
        return True

    def _publish_silence_state(self, is_active: bool):
        """Publica el estado del relay de silencio a ThingsBoard"""
        try:
            telemetry = {
                "silence_relay_active": is_active,
                "silence_relay_timestamp": time.time()
            }
            self.mqtt_handler.publish_telemetry(telemetry, bypass_queue=False)
            self.logger.debug(f"Silence state published: {is_active}")
        except Exception as e:
            self.logger.error(f"Failed to publish silence state: {e}")

    def handle_silence_command(self, data: Dict[str, Any]):
        """Callback para manejar comandos de silencio desde ThingsBoard"""
        try:
            self.logger.info(f"Received silence command: {data}")
            
            # Verificar si el comando es para activar el silencio
            if isinstance(data, dict):
                command = data.get('silence_panel', False)
            else:
                command = data
            
            if command:
                # Ejecutar en un hilo separado para no bloquear
                threading.Thread(target=self.activate_silence, daemon=True).start()
                self.logger.info("Silence command accepted and started")
            else:
                self.logger.debug("Silence command received but value is False")
                
        except Exception as e:
            self.logger.error(f"Error handling silence command: {e}")

    def cleanup(self):
        """Limpia los recursos GPIO"""
        try:
            if self.is_raspberry_pi and self.GPIO:
                # Asegurar que el relay esté en estado inactivo
                inactive_state = self.GPIO.LOW if self.active_high else self.GPIO.HIGH
                self.GPIO.output(self.silence_pin, inactive_state)
                self.GPIO.cleanup(self.silence_pin)
                self.logger.info("GPIO cleanup completed for SilenceController")
        except Exception as e:
            self.logger.error(f"Error during GPIO cleanup in SilenceController: {e}")
