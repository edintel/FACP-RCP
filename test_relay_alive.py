#!/usr/bin/env python3
"""
Script para probar el relay del Test Alive
"""
import yaml
import time
import sys
import argparse

def load_config(config_path='config/config.yml'):
    """Carga la configuración desde el archivo YAML"""
    try:
        with open(config_path, 'r') as file:
            return yaml.safe_load(file)
    except FileNotFoundError:
        print(f"Error: No se encontró el archivo {config_path}")
        sys.exit(1)

def check_raspberry_pi():
    """Verifica si estamos en una Raspberry Pi"""
    try:
        with open('/sys/firmware/devicetree/base/model', 'r') as model:
            return 'Raspberry Pi' in model.read()
    except:
        return False

def test_relay(pin, high_time, low_time, cycles=3):
    """Prueba el relay por un número específico de ciclos"""
    
    is_rpi = check_raspberry_pi()
    
    if not is_rpi:
        print("⚠️  ADVERTENCIA: No se detectó Raspberry Pi")
        print("El script continuará en modo simulación (sin control GPIO real)\n")
        
        for cycle in range(cycles):
            print(f"Ciclo {cycle + 1}/{cycles}:")
            print(f"  🟢 Relay ON (simulado) - Pin {pin} - {high_time}s")
            time.sleep(high_time)
            print(f"  🔴 Relay OFF (simulado) - Pin {pin} - {low_time}s")
            time.sleep(low_time)
        return
    
    # Código real para Raspberry Pi
    try:
        import RPi.GPIO as GPIO
        
        print(f"✅ Raspberry Pi detectada - Iniciando prueba del relay\n")
        print(f"Configuración:")
        print(f"  - Pin GPIO: {pin}")
        print(f"  - Tiempo HIGH: {high_time}s")
        print(f"  - Tiempo LOW: {low_time}s")
        print(f"  - Ciclos: {cycles}\n")
        
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(pin, GPIO.OUT)
        
        for cycle in range(cycles):
            print(f"Ciclo {cycle + 1}/{cycles}:")
            print(f"  🟢 Relay ON - Pin {pin}")
            GPIO.output(pin, GPIO.HIGH)
            time.sleep(high_time)
            
            print(f"  🔴 Relay OFF - Pin {pin}")
            GPIO.output(pin, GPIO.LOW)
            time.sleep(low_time)
        
        print("\n✅ Prueba completada exitosamente")
        GPIO.cleanup(pin)
        
    except ImportError:
        print("❌ Error: No se pudo importar RPi.GPIO")
        print("Instalar con: pip install RPi.GPIO")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error durante la prueba: {e}")
        if 'GPIO' in dir():
            GPIO.cleanup(pin)
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(
        description='Script para probar el relay del Test Alive'
    )
    parser.add_argument(
        '--config', 
        type=str, 
        default='config/config.yml',
        help='Ruta al archivo de configuración (default: config/config.yml)'
    )
    parser.add_argument(
        '--cycles', 
        type=int, 
        default=3,
        help='Número de ciclos a ejecutar (default: 3)'
    )
    parser.add_argument(
        '--pin',
        type=int,
        help='Pin GPIO a usar (sobreescribe el del config)'
    )
    parser.add_argument(
        '--high-time',
        type=int,
        help='Tiempo en HIGH en segundos (sobreescribe el del config)'
    )
    parser.add_argument(
        '--low-time',
        type=int,
        help='Tiempo en LOW en segundos (sobreescribe el del config)'
    )
    
    args = parser.parse_args()
    
    # Cargar configuración
    config = load_config(args.config)
    
    # Usar valores de argumentos o del config
    pin = args.pin if args.pin else config['relay']['pin']
    high_time = args.high_time if args.high_time else config['relay']['high_time']
    low_time = args.low_time if args.low_time else config['relay']['low_time']
    
    print("=" * 50)
    print("  TEST ALIVE - PRUEBA DE RELAY")
    print("=" * 50)
    print()
    
    try:
        test_relay(pin, high_time, low_time, args.cycles)
    except KeyboardInterrupt:
        print("\n\n⚠️  Prueba interrumpida por el usuario")
        if check_raspberry_pi():
            import RPi.GPIO as GPIO
            GPIO.cleanup(pin)
        sys.exit(0)

if __name__ == "__main__":
    main()
