#!/usr/bin/env python3
"""
Script de prueba para el relay de silencio del panel
Permite probar la funcionalidad sin necesidad de ThingsBoard
"""

import sys
import time
import logging
from pathlib import Path

# Agregar el directorio del proyecto al path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from config.loader import load_and_validate_config
from components.silence_controller import SilenceController
from logging_setup import setup_logging

def main():
    print("=" * 60)
    print("PRUEBA DEL RELAY DE SILENCIO DEL PANEL")
    print("=" * 60)
    print()

    # Configurar logging
    setup_logging("config/logging_config.yml")
    logger = logging.getLogger(__name__)

    try:
        # Cargar configuración
        print("📝 Cargando configuración...")
        config = load_and_validate_config("config/config.yml")
        
        # Mostrar configuración del relay de silencio
        print(f"✓ Configuración cargada:")
        print(f"  - GPIO Pin: {config.silence_relay.pin}")
        print(f"  - Tiempo de activación: {config.silence_relay.activation_time}s")
        print(f"  - Activo en: {'HIGH' if config.silence_relay.active_high else 'LOW'}")
        print()

        # Crear un mock simple del MQTT handler para las pruebas
        class MockMQTTHandler:
            def publish_telemetry(self, data, bypass_queue=False):
                print(f"📤 Telemetría: {data}")
            
            def publish_attributes(self, data):
                print(f"📋 Atributos: {data}")

        # Inicializar el controlador de silencio
        print("🔧 Inicializando SilenceController...")
        mqtt_handler = MockMQTTHandler()
        silence_controller = SilenceController(config.silence_relay, mqtt_handler)
        
        if silence_controller.is_raspberry_pi:
            print("✓ Ejecutando en Raspberry Pi - GPIO disponible")
        else:
            print("⚠ No se detectó Raspberry Pi - Modo simulación")
        print()

        # Menú de opciones
        while True:
            print("-" * 60)
            print("OPCIONES:")
            print("1. Activar relay de silencio (una vez)")
            print("2. Probar secuencia (3 activaciones)")
            print("3. Activar relay manualmente (sin tiempo)")
            print("4. Desactivar relay manualmente")
            print("5. Ver estado actual")
            print("0. Salir")
            print("-" * 60)
            
            try:
                opcion = input("Seleccione una opción: ").strip()
                print()
                
                if opcion == "0":
                    print("👋 Saliendo...")
                    break
                    
                elif opcion == "1":
                    print("🔄 Activando relay de silencio...")
                    print(f"⏱️  El relay estará activo por {config.silence_relay.activation_time} segundos")
                    silence_controller.activate_silence()
                    print("✓ Activación completada")
                    
                elif opcion == "2":
                    print("🔄 Iniciando secuencia de prueba (3 activaciones)...")
                    for i in range(1, 4):
                        print(f"\n--- Activación {i}/3 ---")
                        silence_controller.activate_silence()
                        if i < 3:
                            print("⏸️  Esperando 2 segundos antes de la siguiente activación...")
                            time.sleep(2)
                    print("\n✓ Secuencia completada")
                    
                elif opcion == "3":
                    if not silence_controller.is_raspberry_pi:
                        print("❌ Esta opción requiere Raspberry Pi")
                        continue
                    
                    print("⚡ Activando relay manualmente...")
                    active_state = silence_controller.GPIO.HIGH if config.silence_relay.active_high else silence_controller.GPIO.LOW
                    silence_controller.GPIO.output(config.silence_relay.pin, active_state)
                    print(f"✓ Relay GPIO {config.silence_relay.pin} activado")
                    print("⚠️  ATENCIÓN: El relay permanecerá activo hasta que lo desactive manualmente")
                    
                elif opcion == "4":
                    if not silence_controller.is_raspberry_pi:
                        print("❌ Esta opción requiere Raspberry Pi")
                        continue
                    
                    print("⚡ Desactivando relay manualmente...")
                    inactive_state = silence_controller.GPIO.LOW if config.silence_relay.active_high else silence_controller.GPIO.HIGH
                    silence_controller.GPIO.output(config.silence_relay.pin, inactive_state)
                    print(f"✓ Relay GPIO {config.silence_relay.pin} desactivado")
                    
                elif opcion == "5":
                    print("📊 Estado actual:")
                    print(f"  - Raspberry Pi detectada: {'Sí' if silence_controller.is_raspberry_pi else 'No'}")
                    print(f"  - Silencio en progreso: {'Sí' if silence_controller.is_silencing else 'No'}")
                    
                    if silence_controller.is_raspberry_pi:
                        current_state = silence_controller.GPIO.input(config.silence_relay.pin)
                        state_name = "HIGH" if current_state == silence_controller.GPIO.HIGH else "LOW"
                        is_active = current_state == (silence_controller.GPIO.HIGH if config.silence_relay.active_high else silence_controller.GPIO.LOW)
                        print(f"  - Estado GPIO {config.silence_relay.pin}: {state_name} ({'Activo' if is_active else 'Inactivo'})")
                    
                else:
                    print("❌ Opción no válida")
                    
            except KeyboardInterrupt:
                print("\n\n⚠️  Interrupción detectada")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
                logger.exception("Error durante la prueba")
        
        # Cleanup
        print("\n🧹 Limpiando recursos...")
        silence_controller.cleanup()
        print("✓ Limpieza completada")
        
    except FileNotFoundError as e:
        print(f"❌ Error: Archivo no encontrado - {e}")
        print("   Asegúrese de ejecutar el script desde el directorio del proyecto")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        logger.exception("Error fatal")
        sys.exit(1)
    
    print("\n✓ Prueba finalizada")
    print("=" * 60)

if __name__ == "__main__":
    main()
