#!/usr/bin/env python3
"""
Script para probar RPC end-to-end
Simula exactamente lo que VigiApp debería enviar

Este script:
1. Se conecta a ThingsBoard como cliente externo
2. Envía comandos RPC al dispositivo
3. Espera respuesta
4. Muestra resultados detallados

Uso:
    python3 test_rpc_endtoend.py
"""

import sys
import os
import time
import json
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

try:
    import requests
except ImportError:
    logger.error("❌ Módulo 'requests' no encontrado")
    logger.error("   Instalar con: pip3 install requests")
    sys.exit(1)


def print_separator(char="=", length=70):
    print(char * length)


def print_header(text):
    print()
    print_separator()
    print(f"  {text}")
    print_separator()
    print()


def load_config():
    """Carga configuración desde config.yml"""
    try:
        import yaml
        config_path = '/home/edintel/Desktop/FACP-RCP/config/config.yml'
        
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        return config
    except Exception as e:
        logger.error(f"Error cargando config.yml: {e}")
        return None


def send_rpc_via_http(tb_host, tb_port, device_token, method, params):
    """
    Envía comando RPC vía HTTP API de ThingsBoard
    Simula lo que haría un cliente externo como VigiApp
    """
    # Construir URL para RPC
    # Nota: Este método usa el device token directamente
    url = f"http://{tb_host}:{tb_port}/api/v1/{device_token}/rpc"
    
    payload = {
        "method": method,
        "params": params
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    logger.info(f"📤 Enviando RPC a: {url}")
    logger.info(f"   Method: {method}")
    logger.info(f"   Params: {params}")
    logger.info(f"   Payload: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        
        logger.info(f"📥 Respuesta recibida:")
        logger.info(f"   Status Code: {response.status_code}")
        
        if response.status_code == 200:
            logger.info(f"   ✅ SUCCESS")
            try:
                result = response.json()
                logger.info(f"   Response: {json.dumps(result, indent=2)}")
                return True, result
            except:
                logger.info(f"   Response: {response.text}")
                return True, response.text
        else:
            logger.error(f"   ❌ ERROR")
            logger.error(f"   Response: {response.text}")
            return False, response.text
            
    except requests.exceptions.Timeout:
        logger.error("❌ Timeout - El dispositivo no respondió")
        logger.error("   Posibles causas:")
        logger.error("   1. El servicio serial-to-mqtt no está corriendo")
        logger.error("   2. El dispositivo no está conectado a ThingsBoard")
        logger.error("   3. Los handlers RPC no están configurados")
        return False, "timeout"
    except requests.exceptions.ConnectionError as e:
        logger.error(f"❌ Error de conexión: {e}")
        logger.error("   Verifica:")
        logger.error("   1. El host y puerto de ThingsBoard son correctos")
        logger.error("   2. ThingsBoard está accesible desde esta red")
        return False, str(e)
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        return False, str(e)


def test_silence_command(config):
    """Prueba comando de silenciar"""
    print_header("🔇 PRUEBA COMANDO SILENCIAR")
    
    tb_config = config['thingsboard']
    
    logger.info("Configuración ThingsBoard:")
    logger.info(f"  Host: {tb_config['host']}")
    logger.info(f"  Port: {tb_config['port']}")
    logger.info(f"  Device Token: {tb_config['device_token'][:8]}...{tb_config['device_token'][-4:]}")
    print()
    
    # Enviar comando
    success, result = send_rpc_via_http(
        tb_host=tb_config['host'],
        tb_port=tb_config['port'],
        device_token=tb_config['device_token'],
        method="silenciar_panel",
        params={"activate": True}
    )
    
    print()
    
    if success:
        logger.info("✅ Comando de silenciar enviado exitosamente")
        logger.info("   El relay debería activarse ahora")
        
        silence_time = config.get('silence_relay', {}).get('activation_time', 5)
        logger.info(f"   Esperando {silence_time} segundos...")
        time.sleep(silence_time + 2)
        
        logger.info("   El relay debería estar inactivo ahora")
    else:
        logger.error("❌ Fallo al enviar comando de silenciar")
    
    print_separator()
    return success


def test_reset_command(config):
    """Prueba comando de reiniciar"""
    print_header("🔄 PRUEBA COMANDO REINICIAR")
    
    tb_config = config['thingsboard']
    
    logger.info("Configuración ThingsBoard:")
    logger.info(f"  Host: {tb_config['host']}")
    logger.info(f"  Port: {tb_config['port']}")
    logger.info(f"  Device Token: {tb_config['device_token'][:8]}...{tb_config['device_token'][-4:]}")
    print()
    
    # Enviar comando
    success, result = send_rpc_via_http(
        tb_host=tb_config['host'],
        tb_port=tb_config['port'],
        device_token=tb_config['device_token'],
        method="reiniciar_panel",
        params={"activate": True}
    )
    
    print()
    
    if success:
        logger.info("✅ Comando de reiniciar enviado exitosamente")
        logger.info("   El relay debería activarse ahora")
        
        reset_time = config.get('reset_relay', {}).get('activation_time', 5)
        logger.info(f"   Esperando {reset_time} segundos...")
        time.sleep(reset_time + 2)
        
        logger.info("   El relay debería estar inactivo ahora")
    else:
        logger.error("❌ Fallo al enviar comando de reiniciar")
    
    print_separator()
    return success


def check_service_running():
    """Verifica si el servicio está corriendo"""
    import subprocess
    
    try:
        result = subprocess.run(
            ['systemctl', 'is-active', 'serial_to_mqtt.service'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        is_active = result.stdout.strip() == 'active'
        
        if is_active:
            logger.info("✅ Servicio serial-to-mqtt está CORRIENDO")
        else:
            logger.warning("⚠️  Servicio serial-to-mqtt NO está corriendo")
            logger.warning("    Inicia el servicio con: sudo systemctl start serial-to-mqtt.service")
        
        return is_active
        
    except Exception as e:
        logger.warning(f"No se pudo verificar estado del servicio: {e}")
        return None


def check_mqtt_connection():
    """Verifica logs de conexión MQTT"""
    import subprocess
    
    try:
        result = subprocess.run(
            ['journalctl', '-u', 'serial-to-mqtt.service', '-n', '100'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        logs = result.stdout
        
        connected = 'Connected to ThingsBoard successfully' in logs
        rpc_configured = 'RPC handlers configured successfully' in logs
        
        if connected:
            logger.info("✅ Dispositivo CONECTADO a ThingsBoard")
        else:
            logger.warning("⚠️  No se encuentra confirmación de conexión a ThingsBoard")
            logger.warning("    Verifica logs: sudo journalctl -u serial-to-mqtt.service -n 50")
        
        if rpc_configured:
            logger.info("✅ Handlers RPC CONFIGURADOS")
        else:
            logger.warning("⚠️  No se encuentra confirmación de configuración RPC")
        
        return connected and rpc_configured
        
    except Exception as e:
        logger.warning(f"No se pudo verificar logs: {e}")
        return None


def main():
    print()
    print_separator("*")
    print("  🧪 PRUEBA END-TO-END - RPC DESDE CLIENTE EXTERNO")
    print("     (Simula exactamente lo que VigiApp debería hacer)")
    print_separator("*")
    
    # Pre-checks
    print_header("🔍 PRE-VERIFICACIONES")
    
    service_ok = check_service_running()
    print()
    connection_ok = check_mqtt_connection()
    print()
    
    if service_ok == False:
        logger.error("❌ El servicio no está corriendo. Inicialo primero:")
        logger.error("   sudo systemctl start serial-to-mqtt.service")
        sys.exit(1)
    
    if connection_ok == False:
        logger.warning("⚠️  Hay problemas de conexión/configuración")
        logger.warning("   Continuando de todos modos...")
        print()
        input("Presiona Enter para continuar o Ctrl+C para cancelar...")
    
    # Cargar configuración
    logger.info("📄 Cargando configuración...")
    config = load_config()
    
    if not config:
        logger.error("❌ No se pudo cargar la configuración")
        sys.exit(1)
    
    logger.info("✅ Configuración cargada")
    print()
    
    # Menú
    print("¿Qué comando deseas probar?")
    print()
    print("  1) SILENCIAR panel")
    print("  2) REINICIAR panel")
    print("  3) AMBOS comandos")
    print()
    
    try:
        choice = input("Opción (1-3) [3]: ").strip() or "3"
    except KeyboardInterrupt:
        print("\n⚠️ Cancelado")
        sys.exit(0)
    
    success_silence = None
    success_reset = None
    
    # Ejecutar pruebas
    if choice in ["1", "3"]:
        success_silence = test_silence_command(config)
        
        if choice == "3":
            print()
            input("Presiona Enter para probar REINICIAR...")
    
    if choice in ["2", "3"]:
        success_reset = test_reset_command(config)
    
    # Resumen
    print()
    print_header("📊 RESUMEN DE RESULTADOS")
    
    if success_silence is not None:
        status = "✅ ÉXITO" if success_silence else "❌ FALLO"
        print(f"  Comando SILENCIAR: {status}")
    
    if success_reset is not None:
        status = "✅ ÉXITO" if success_reset else "❌ FALLO"
        print(f"  Comando REINICIAR: {status}")
    
    print()
    print_separator()
    
    # Diagnóstico
    all_success = (success_silence is None or success_silence) and \
                  (success_reset is None or success_reset)
    
    if all_success:
        print()
        logger.info("🎉 ¡TODAS LAS PRUEBAS EXITOSAS!")
        logger.info("")
        logger.info("Los comandos RPC funcionan correctamente desde un cliente externo.")
        logger.info("Si VigiApp no funciona, el problema está en VigiApp, no en tu código.")
        logger.info("")
        logger.info("Verifica en VigiApp:")
        logger.info("  1. Que envíe exactamente: 'silenciar_panel' y 'reiniciar_panel'")
        logger.info("  2. Que use el device_token correcto")
        logger.info("  3. Que la URL/endpoint sea correcta")
    else:
        print()
        logger.error("❌ ALGUNAS PRUEBAS FALLARON")
        logger.error("")
        logger.error("Posibles causas:")
        logger.error("  1. El servicio no está conectado a ThingsBoard")
        logger.error("  2. Los handlers RPC no están configurados")
        logger.error("  3. Las credenciales en config.yml son incorrectas")
        logger.error("")
        logger.error("Ejecuta para más información:")
        logger.error("  sudo journalctl -u serial-to-mqtt.service -n 100 | grep -i 'rpc\\|connect\\|error'")
    
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ Interrumpido por el usuario")
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ Error inesperado: {e}", exc_info=True)
        sys.exit(1)
