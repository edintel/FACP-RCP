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

    def handle_silence_rpc(self, params: Dict[str, Any]) -> str:
        """
        Callback para manejar comandos RPC de silencio desde ThingsBoard
        
        Args:
            params: Parámetros del comando RPC
            
        Returns:
            Mensaje de estado
        """
        try:
            self.logger.info(f"Received silence RPC command with params: {params}")
            
            # El comando puede venir como {'activate': True} o directamente True
            activate = params.get('activate', True) if isinstance(params, dict) else True
            
            if activate:
                # Ejecutar en un hilo separado para no bloquear
                threading.Thread(target=self.activate_silence, daemon=True).start()
                return "Comando de silencio aceptado y en ejecución"
            else:
                return "Comando de silencio recibido pero no activado (activate=False)"
                
        except Exception as e:
            error_msg = f"Error handling silence RPC command: {e}"
            self.logger.error(error_msg)
            return error_msg

    def activate_silence(self):
        """Activa el relay de silencio por el tiempo configurado"""
        with self.silence_lock:
            if self.is_silencing:
                self.logger.warning("Silence already in progress, ignoring new request")
                return False

            self.is_silencing = True
            
        self.logger.info(f"Activating silence relay for {self.activation_time} seconds")
        
        # Publicar estado inicial
        self._publish_silence_state(True, "started")
        
        if self.is_raspberry_pi and self.GPIO:
            try:
                # Activar el relay
                active_state = self.GPIO.HIGH if self.active_high else self.GPIO.LOW
                self.GPIO.output(self.silence_pin, active_state)
                self.logger.info(f"Silence relay GPIO {self.silence_pin} activated")
                
                # Esperar el tiempo configurado
                time.sleep(self.activation_time)
                
                # Desactivar el relay
                inactive_state = self.GPIO.LOW if self.active_high else self.GPIO.HIGH
                self.GPIO.output(self.silence_pin, inactive_state)
                self.logger.info(f"Silence relay GPIO {self.silence_pin} deactivated")
                
            except Exception as e:
                self.logger.error(f"Error controlling silence relay: {e}")
                self._publish_silence_state(False, f"error: {e}")
                with self.silence_lock:
                    self.is_silencing = False
                return False
        else:
            self.logger.info(f"[SIMULATION] Silence relay would be active for {self.activation_time} seconds")
            time.sleep(self.activation_time)
        
        with self.silence_lock:
            self.is_silencing = False
        
        # Publicar estado final
        self._publish_silence_state(False, "completed")
        self.logger.info("Silence cycle completed successfully")
        return True

    def _publish_silence_state(self, is_active: bool, status: str = ""):
        """Publica el estado del relay de silencio a ThingsBoard"""
        try:
            telemetry = {
                "silence_relay_active": is_active,
                "silence_status": status,
                "silence_timestamp": time.time()
            }
            self.mqtt_handler.publish_telemetry(telemetry, bypass_queue=False)
            self.logger.debug(f"Silence state published: active={is_active}, status={status}")
        except Exception as e:
            self.logger.error(f"Failed to publish silence state: {e}")

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
