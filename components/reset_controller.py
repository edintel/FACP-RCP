import threading
import logging
import time
from config.schema import ResetRelayConfig
from typing import Dict, Any

class ResetController:
    def __init__(self, reset_config: ResetRelayConfig, mqtt_handler):
        self.reset_pin = reset_config.pin
        self.activation_time = reset_config.activation_time
        self.active_high = reset_config.active_high
        self.mqtt_handler = mqtt_handler
        self.is_raspberry_pi = self._is_raspberry_pi()
        self.GPIO = None
        self.is_resetting = False
        self.reset_lock = threading.Lock()
        self.logger = logging.getLogger(__name__)

        if self.is_raspberry_pi:
            self._setup_gpio()
        else:
            self.logger.warning("Not running on Raspberry Pi. Reset control will be simulated.")

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
            GPIO.setup(self.reset_pin, GPIO.OUT)
            # Set initial state to inactive
            initial_state = GPIO.LOW if self.active_high else GPIO.HIGH
            GPIO.output(self.reset_pin, initial_state)
            self.GPIO = GPIO
            self.logger.info(f"Reset relay GPIO {self.reset_pin} configured successfully")
        except ImportError:
            self.logger.warning("RPi.GPIO module not found. Reset control will be disabled.")
            self.is_raspberry_pi = False
        except Exception as e:
            self.logger.error(f"Error setting up GPIO for reset relay: {e}")
            self.is_raspberry_pi = False

    def handle_reset_rpc(self, params: Dict[str, Any]) -> str:
        """
        Callback para manejar comandos RPC de reinicio desde ThingsBoard
        
        Args:
            params: Parámetros del comando RPC
            
        Returns:
            Mensaje de estado
        """
        try:
            self.logger.info(f"Received reset RPC command with params: {params}")
            
            # El comando puede venir como {'activate': True} o directamente True
            activate = params.get('activate', True) if isinstance(params, dict) else True
            
            if activate:
                # Ejecutar en un hilo separado para no bloquear
                threading.Thread(target=self.activate_reset, daemon=True).start()
                return "Comando de reinicio aceptado y en ejecución"
            else:
                return "Comando de reinicio recibido pero no activado (activate=False)"
                
        except Exception as e:
            error_msg = f"Error handling reset RPC command: {e}"
            self.logger.error(error_msg)
            return error_msg

    def activate_reset(self):
        """Activa el relay de reinicio por el tiempo configurado"""
        with self.reset_lock:
            if self.is_resetting:
                self.logger.warning("Reset already in progress, ignoring new request")
                return False

            self.is_resetting = True
            
        self.logger.info(f"Activating reset relay for {self.activation_time} seconds")
        
        # Publicar estado inicial
        self._publish_reset_state(True, "started")
        
        if self.is_raspberry_pi and self.GPIO:
            try:
                # Activar el relay
                active_state = self.GPIO.HIGH if self.active_high else self.GPIO.LOW
                self.GPIO.output(self.reset_pin, active_state)
                self.logger.info(f"Reset relay GPIO {self.reset_pin} activated")
                
                # Esperar el tiempo configurado
                time.sleep(self.activation_time)
                
                # Desactivar el relay
                inactive_state = self.GPIO.LOW if self.active_high else self.GPIO.HIGH
                self.GPIO.output(self.reset_pin, inactive_state)
                self.logger.info(f"Reset relay GPIO {self.reset_pin} deactivated")
                
            except Exception as e:
                self.logger.error(f"Error controlling reset relay: {e}")
                self._publish_reset_state(False, f"error: {e}")
                with self.reset_lock:
                    self.is_resetting = False
                return False
        else:
            self.logger.info(f"[SIMULATION] Reset relay would be active for {self.activation_time} seconds")
            time.sleep(self.activation_time)
        
        with self.reset_lock:
            self.is_resetting = False
        
        # Publicar estado final
        self._publish_reset_state(False, "completed")
        self.logger.info("Reset cycle completed successfully")
        return True

    def _publish_reset_state(self, is_active: bool, status: str = ""):
        """Publica el estado del relay de reinicio a ThingsBoard"""
        try:
            telemetry = {
                "reset_relay_active": is_active,
                "reset_status": status,
                "reset_timestamp": time.time()
            }
            self.mqtt_handler.publish_telemetry(telemetry, bypass_queue=False)
            self.logger.debug(f"Reset state published: active={is_active}, status={status}")
        except Exception as e:
            self.logger.error(f"Failed to publish reset state: {e}")

    def cleanup(self):
        """Limpia los recursos GPIO"""
        try:
            if self.is_raspberry_pi and self.GPIO:
                # Asegurar que el relay esté en estado inactivo
                inactive_state = self.GPIO.LOW if self.active_high else self.GPIO.HIGH
                self.GPIO.output(self.reset_pin, inactive_state)
                self.GPIO.cleanup(self.reset_pin)
                self.logger.info("GPIO cleanup completed for ResetController")
        except Exception as e:
            self.logger.error(f"Error during GPIO cleanup in ResetController: {e}")