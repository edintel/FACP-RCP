#!/usr/bin/env python3
"""
Script de prueba SIMPLIFICADO para funciones de Silenciar y Reiniciar Panel
NO requiere cargar config.yml - usa configuración directa

Uso:
    python3 test_simple.py
"""

import sys
import os
import time
import logging
import threading

# Configurar logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURACIÓN MANUAL - EDITAR ESTOS VALORES
# ============================================================================

# GPIO Pins
SILENCE_PIN = 22
RESET_PIN = 25

# Tiempos de activación (segundos)
SILENCE_ACTIVATION_TIME = 5
RESET_ACTIVATION_TIME = 5

# Active High (True si se activa con HIGH, False si se activa con LOW)
SILENCE_ACTIVE_HIGH = True
RESET_ACTIVE_HIGH = True

# ============================================================================


class MockMqttHandler:
    """Mock del MQTT handler para pruebas"""
    def __init__(self):
        self.telemetry_published = []
        self.logger = logging.getLogger("MockMQTT")
        
    def publish_telemetry(self, telemetry, bypass_queue=False):
        self.telemetry_published.append(telemetry)
        self.logger.info(f"📤 MQTT Telemetry: {telemetry}")


class SimpleSilenceController:
    """Controlador de silencio simplificado"""
    def __init__(self, pin, activation_time, active_high, mqtt_handler):
        self.silence_pin = pin
        self.activation_time = activation_time
        self.active_high = active_high
        self.mqtt_handler = mqtt_handler
        self.is_raspberry_pi = self._is_raspberry_pi()
        self.GPIO = None
        self.is_silencing = False
        self.silence_lock = threading.Lock()
        self.logger = logging.getLogger("SilenceController")

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
        
        self._publish_silence_state(True, "started")
        
        if self.is_raspberry_pi and self.GPIO:
            try:
                active_state = self.GPIO.HIGH if self.active_high else self.GPIO.LOW
                self.GPIO.output(self.silence_pin, active_state)
                self.logger.info(f"🔥 Silence relay GPIO {self.silence_pin} activated")
                
                time.sleep(self.activation_time)
                
                inactive_state = self.GPIO.LOW if self.active_high else self.GPIO.HIGH
                self.GPIO.output(self.silence_pin, inactive_state)
                self.logger.info(f"💤 Silence relay GPIO {self.silence_pin} deactivated")
                
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
        
        self._publish_silence_state(False, "completed")
        self.logger.info("Silence cycle completed successfully")
        return True

    def _publish_silence_state(self, is_active, status=""):
        try:
            telemetry = {
                "silence_relay_active": is_active,
                "silence_status": status,
                "silence_timestamp": time.time()
            }
            self.mqtt_handler.publish_telemetry(telemetry, bypass_queue=False)
        except Exception as e:
            self.logger.error(f"Failed to publish silence state: {e}")

    def cleanup(self):
        try:
            if self.is_raspberry_pi and self.GPIO:
                inactive_state = self.GPIO.LOW if self.active_high else self.GPIO.HIGH
                self.GPIO.output(self.silence_pin, inactive_state)
                self.GPIO.cleanup(self.silence_pin)
                self.logger.info("GPIO cleanup completed for SilenceController")
        except Exception as e:
            self.logger.error(f"Error during GPIO cleanup in SilenceController: {e}")


class SimpleResetController:
    """Controlador de reinicio simplificado"""
    def __init__(self, pin, activation_time, active_high, mqtt_handler):
        self.reset_pin = pin
        self.activation_time = activation_time
        self.active_high = active_high
        self.mqtt_handler = mqtt_handler
        self.is_raspberry_pi = self._is_raspberry_pi()
        self.GPIO = None
        self.is_resetting = False
        self.reset_lock = threading.Lock()
        self.logger = logging.getLogger("ResetController")

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

    def activate_reset(self):
        """Activa el relay de reinicio por el tiempo configurado"""
        with self.reset_lock:
            if self.is_resetting:
                self.logger.warning("Reset already in progress, ignoring new request")
                return False
            self.is_resetting = True
            
        self.logger.info(f"Activating reset relay for {self.activation_time} seconds")
        
        self._publish_reset_state(True, "started")
        
        if self.is_raspberry_pi and self.GPIO:
            try:
                active_state = self.GPIO.HIGH if self.active_high else self.GPIO.LOW
                self.GPIO.output(self.reset_pin, active_state)
                self.logger.info(f"🔥 Reset relay GPIO {self.reset_pin} activated")
                
                time.sleep(self.activation_time)
                
                inactive_state = self.GPIO.LOW if self.active_high else self.GPIO.HIGH
                self.GPIO.output(self.reset_pin, inactive_state)
                self.logger.info(f"💤 Reset relay GPIO {self.reset_pin} deactivated")
                
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
        
        self._publish_reset_state(False, "completed")
        self.logger.info("Reset cycle completed successfully")
        return True

    def _publish_reset_state(self, is_active, status=""):
        try:
            telemetry = {
                "reset_relay_active": is_active,
                "reset_status": status,
                "reset_timestamp": time.time()
            }
            self.mqtt_handler.publish_telemetry(telemetry, bypass_queue=False)
        except Exception as e:
            self.logger.error(f"Failed to publish reset state: {e}")

    def cleanup(self):
        try:
            if self.is_raspberry_pi and self.GPIO:
                inactive_state = self.GPIO.LOW if self.active_high else self.GPIO.HIGH
                self.GPIO.output(self.reset_pin, inactive_state)
                self.GPIO.cleanup(self.reset_pin)
                self.logger.info("GPIO cleanup completed for ResetController")
        except Exception as e:
            self.logger.error(f"Error during GPIO cleanup in ResetController: {e}")


def print_separator(char="=", length=70):
    print(char * length)


def print_header(text):
    print_separator()
    print(f"  {text}")
    print_separator()


def test_silence():
    """Prueba el controlador de silencio"""
    print_header("🔇 PRUEBA DE CONTROLADOR DE SILENCIO")
    
    mqtt_handler = MockMqttHandler()
    
    logger.info("Creando SilenceController...")
    controller = SimpleSilenceController(
        SILENCE_PIN, 
        SILENCE_ACTIVATION_TIME, 
        SILENCE_ACTIVE_HIGH, 
        mqtt_handler
    )
    
    logger.info(f"📍 Configuración:")
    logger.info(f"   - Pin GPIO: {controller.silence_pin}")
    logger.info(f"   - Tiempo activación: {controller.activation_time}s")
    logger.info(f"   - Active High: {controller.active_high}")
    logger.info(f"   - Es Raspberry Pi: {controller.is_raspberry_pi}")
    logger.info(f"   - GPIO disponible: {controller.GPIO is not None}")
    
    print()
    logger.info("🎯 Activando relay de silencio...")
    
    controller.activate_silence()
    
    logger.info(f"📊 Telemetría publicada: {len(mqtt_handler.telemetry_published)} mensajes")
    for i, tel in enumerate(mqtt_handler.telemetry_published):
        logger.info(f"   Mensaje {i+1}: {tel}")
    
    print()
    logger.info("🧹 Limpiando recursos...")
    controller.cleanup()
    
    print_separator()
    print()
    
    return controller.is_raspberry_pi


def test_reset():
    """Prueba el controlador de reinicio"""
    print_header("🔄 PRUEBA DE CONTROLADOR DE REINICIO")
    
    mqtt_handler = MockMqttHandler()
    
    logger.info("Creando ResetController...")
    controller = SimpleResetController(
        RESET_PIN, 
        RESET_ACTIVATION_TIME, 
        RESET_ACTIVE_HIGH, 
        mqtt_handler
    )
    
    logger.info(f"📍 Configuración:")
    logger.info(f"   - Pin GPIO: {controller.reset_pin}")
    logger.info(f"   - Tiempo activación: {controller.activation_time}s")
    logger.info(f"   - Active High: {controller.active_high}")
    logger.info(f"   - Es Raspberry Pi: {controller.is_raspberry_pi}")
    logger.info(f"   - GPIO disponible: {controller.GPIO is not None}")
    
    print()
    logger.info("🎯 Activando relay de reinicio...")
    
    controller.activate_reset()
    
    logger.info(f"📊 Telemetría publicada: {len(mqtt_handler.telemetry_published)} mensajes")
    for i, tel in enumerate(mqtt_handler.telemetry_published):
        logger.info(f"   Mensaje {i+1}: {tel}")
    
    print()
    logger.info("🧹 Limpiando recursos...")
    controller.cleanup()
    
    print_separator()
    print()
    
    return controller.is_raspberry_pi


def test_manual_gpio(gpio_pin, active_high, duration=2):
    """Prueba manual de GPIO"""
    print_header(f"🔌 PRUEBA MANUAL DE GPIO {gpio_pin}")
    
    try:
        with open('/sys/firmware/devicetree/base/model', 'r') as f:
            model = f.read()
            if 'Raspberry Pi' not in model:
                logger.warning("No es una Raspberry Pi, saltando prueba GPIO")
                return False
    except:
        logger.warning("No se pudo verificar modelo de dispositivo")
        return False
    
    try:
        import RPi.GPIO as GPIO
        
        logger.info(f"Configurando GPIO {gpio_pin}...")
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(gpio_pin, GPIO.OUT)
        
        initial_state = GPIO.LOW if active_high else GPIO.HIGH
        GPIO.output(gpio_pin, initial_state)
        logger.info(f"✓ GPIO {gpio_pin} configurado, estado inicial: {'LOW' if initial_state == GPIO.LOW else 'HIGH'}")
        
        time.sleep(1)
        
        active_state = GPIO.HIGH if active_high else GPIO.LOW
        logger.info(f"🔥 Activando relay (estado: {'HIGH' if active_state == GPIO.HIGH else 'LOW'})...")
        GPIO.output(gpio_pin, active_state)
        logger.info(f"   → ¿Se activa el relay físicamente? Observa durante {duration} segundos")
        
        time.sleep(duration)
        
        logger.info(f"💤 Desactivando relay...")
        GPIO.output(gpio_pin, initial_state)
        logger.info(f"   → El relay debería estar inactivo ahora")
        
        time.sleep(1)
        
        GPIO.cleanup(gpio_pin)
        logger.info("✓ GPIO limpiado")
        
        print_separator()
        print()
        return True
        
    except ImportError:
        logger.error("RPi.GPIO no disponible")
        return False
    except Exception as e:
        logger.error(f"Error en prueba GPIO: {e}")
        return False


def main():
    print("\n")
    print_separator("*")
    print("  🧪 SCRIPT DE PRUEBA SIMPLIFICADO")
    print("     SILENCIAR Y REINICIAR PANEL")
    print_separator("*")
    print()
    
    logger.info("📍 Configuración actual:")
    logger.info(f"   Silence Pin: GPIO {SILENCE_PIN}")
    logger.info(f"   Silence Time: {SILENCE_ACTIVATION_TIME}s")
    logger.info(f"   Silence Active High: {SILENCE_ACTIVE_HIGH}")
    logger.info(f"   Reset Pin: GPIO {RESET_PIN}")
    logger.info(f"   Reset Time: {RESET_ACTIVATION_TIME}s")
    logger.info(f"   Reset Active High: {RESET_ACTIVE_HIGH}")
    print()
    
    print("Selecciona qué pruebas ejecutar:")
    print()
    print("  1) Probar solo SILENCIAR")
    print("  2) Probar solo REINICIAR")
    print("  3) Probar AMBOS (silenciar y reiniciar)")
    print("  4) Prueba manual GPIO (sin controladores)")
    print("  5) TODAS las pruebas")
    print()
    
    try:
        choice = input("Opción (1-5) [3]: ").strip() or "3"
    except KeyboardInterrupt:
        print("\n\n⚠️ Cancelado por el usuario")
        sys.exit(0)
    
    print()
    
    is_raspberry_pi = False
    
    if choice in ["1", "3", "5"]:
        is_raspberry_pi = test_silence()
        
    if choice in ["2", "3", "5"]:
        is_raspberry_pi = test_reset()
    
    if choice in ["4", "5"]:
        if is_raspberry_pi or choice == "4":
            logger.info("Probando GPIO de SILENCIO...")
            test_manual_gpio(SILENCE_PIN, SILENCE_ACTIVE_HIGH, duration=3)
            
            time.sleep(2)
            
            logger.info("Probando GPIO de REINICIO...")
            test_manual_gpio(RESET_PIN, RESET_ACTIVE_HIGH, duration=3)
    
    print_separator("*")
    print("  ✅ PRUEBAS COMPLETADAS")
    print_separator("*")
    print()
    
    if not is_raspberry_pi:
        logger.warning("⚠️  No se detectó Raspberry Pi - Ejecutado en modo simulación")
    else:
        logger.info("✓ Ejecutado en Raspberry Pi")
        logger.info("✓ Los relays deberían haberse activado")
        logger.info("")
        logger.info("Si los relays NO se activaron físicamente:")
        logger.info("  1. Verifica las conexiones de hardware")
        logger.info("  2. Verifica que los pines GPIO sean correctos")
        logger.info("  3. Verifica que active_high esté configurado correctamente")
    
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ Interrumpido por el usuario")
        try:
            import RPi.GPIO as GPIO
            GPIO.cleanup()
        except:
            pass
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ Error inesperado: {e}", exc_info=True)
        sys.exit(1)
