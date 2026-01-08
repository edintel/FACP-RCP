#!/usr/bin/env python3
"""
Monitor ALTERNATIVO de tráfico RPC usando paho-mqtt
Más fácil de instalar que tb-mqtt-client

Instalación:
    pip3 install paho-mqtt --user

Uso:
    1. Detener el servicio: sudo systemctl stop serial_to_mqtt.service
    2. Ejecutar este script: python3 monitor_simple.py
    3. Presionar botones en VigiApp
    4. Ver qué llega (o no llega)
"""

import paho.mqtt.client as mqtt
import json
import time
import sys

# CONFIGURACIÓN - Editar con tus valores
DEVICE_TOKEN = "KcJ5skGQMcAJcoN70ZhJ"  # Tu device token
TB_HOST = "mqtt.thingsboard.cloud"
TB_PORT = 1883

# Contador de mensajes recibidos
message_count = 0

def on_connect(client, userdata, flags, rc):
    """Callback cuando se conecta al broker"""
    if rc == 0:
        print("\n" + "="*70)
        print("  ✅ CONECTADO A THINGSBOARD")
        print("="*70)
        print()
        print(f"Host: {TB_HOST}")
        print(f"Port: {TB_PORT}")
        print(f"Device Token: {DEVICE_TOKEN[:8]}...{DEVICE_TOKEN[-4:]}")
        print()
        print("="*70)
        print("  🎧 ESCUCHANDO COMANDOS RPC...")
        print("="*70)
        print()
        print("Presiona los botones en VigiApp:")
        print("  - Botón SILENCIAR")
        print("  - Botón REINICIAR")
        print()
        print("Los comandos aparecerán aquí en tiempo real.")
        print("Presiona Ctrl+C para salir")
        print("="*70)
        print()
        
        # Suscribirse a comandos RPC del servidor
        client.subscribe("v1/devices/me/rpc/request/+")
        print("✅ Suscrito a: v1/devices/me/rpc/request/+")
        print()
        
    else:
        print(f"❌ Error de conexión. Código: {rc}")
        sys.exit(1)


def on_message(client, userdata, msg):
    """Callback cuando llega un mensaje"""
    global message_count
    message_count += 1
    
    # Extraer request ID del topic
    topic_parts = msg.topic.split('/')
    request_id = topic_parts[-1] if len(topic_parts) > 0 else "unknown"
    
    # Parsear el payload
    try:
        payload = json.loads(msg.payload.decode('utf-8'))
    except:
        payload = msg.payload.decode('utf-8')
    
    # Mostrar comando recibido
    print("\n" + "="*70)
    print(f"🎯 COMANDO RPC #{message_count} RECIBIDO!")
    print("="*70)
    print(f"Topic: {msg.topic}")
    print(f"Request ID: {request_id}")
    print()
    
    if isinstance(payload, dict):
        method = payload.get('method', 'NO_METHOD')
        params = payload.get('params', {})
        
        print(f"📋 Método: {method}")
        print(f"📦 Parámetros: {json.dumps(params, indent=2)}")
        print()
        
        # Verificar si el método es correcto
        if method == 'silenciar_panel':
            print("✅ Método 'silenciar_panel' detectado correctamente")
            print("   Este comando FUNCIONARÍA con el servicio real")
        elif method == 'reiniciar_panel':
            print("✅ Método 'reiniciar_panel' detectado correctamente")
            print("   Este comando FUNCIONARÍA con el servicio real")
        else:
            print(f"⚠️  ADVERTENCIA: Método '{method}' NO reconocido")
            print("    Métodos esperados:")
            print("      - 'silenciar_panel'")
            print("      - 'reiniciar_panel'")
            print()
            print("    VigiApp debe cambiar el nombre del método")
    else:
        print(f"Payload: {payload}")
    
    print("="*70)
    print()
    
    # Enviar respuesta al dispositivo
    response_topic = f"v1/devices/me/rpc/response/{request_id}"
    response_payload = {
        "success": True,
        "message": f"Comando recibido en monitor",
        "timestamp": time.time()
    }
    
    client.publish(response_topic, json.dumps(response_payload))
    print(f"✅ Respuesta enviada a: {response_topic}")
    print()


def on_disconnect(client, userdata, rc):
    """Callback cuando se desconecta"""
    if rc != 0:
        print(f"\n⚠️  Desconexión inesperada. Código: {rc}")


def main():
    print("\n" + "="*70)
    print("  🔍 MONITOR SIMPLE DE COMANDOS RPC")
    print("="*70)
    print()
    print("Este monitor mostrará todos los comandos que VigiApp")
    print("envíe al dispositivo vía MQTT.")
    print()
    
    # Crear cliente MQTT
    client = mqtt.Client(client_id=f"monitor_{int(time.time())}")
    
    # Configurar callbacks
    client.on_connect = on_connect
    client.on_message = on_message
    client.on_disconnect = on_disconnect
    
    # Configurar autenticación con device token
    client.username_pw_set(DEVICE_TOKEN)
    
    try:
        # Conectar
        print(f"📡 Conectando a {TB_HOST}:{TB_PORT}...")
        client.connect(TB_HOST, TB_PORT, 60)
        
        # Loop para mantener la conexión
        client.loop_forever()
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrumpido por el usuario")
    except Exception as e:
        print(f"\n❌ Error: {e}")
    finally:
        print("\n🧹 Desconectando...")
        client.disconnect()
        
        # Diagnóstico final
        print()
        print("="*70)
        print("  📊 DIAGNÓSTICO")
        print("="*70)
        print()
        print(f"Total de comandos recibidos: {message_count}")
        print()
        
        if message_count == 0:
            print("❌ NO SE RECIBIERON COMANDOS")
            print()
            print("Posibles causas:")
            print("  1. VigiApp NO está enviando comandos vía MQTT")
            print("  2. VigiApp intenta usar HTTP REST en lugar de MQTT")
            print("  3. VigiApp usa un device token diferente")
            print("  4. VigiApp no está conectado a ThingsBoard")
            print()
            print("Solución:")
            print("  - Verificar que VigiApp use cliente MQTT")
            print("  - Verificar que use el device token correcto")
            print("  - Ver documentación en DIAGNOSTICO_FINAL_VIGIAPP.md")
        else:
            print("✅ SE RECIBIERON COMANDOS")
            print()
            print("Si los métodos eran correctos ('silenciar_panel' y 'reiniciar_panel'):")
            print("  ✅ VigiApp funciona correctamente")
            print("  ✅ Reinicia el servicio:")
            print("     sudo systemctl start serial_to_mqtt.service")
            print()
            print("Si los métodos tenían nombres incorrectos:")
            print("  ⚠️  Corrige los nombres en VigiApp")
            print("  ⚠️  Deben ser exactamente: 'silenciar_panel' y 'reiniciar_panel'")
        
        print()
        print("="*70)
        print()


if __name__ == "__main__":
    # Verificar que paho-mqtt esté instalado
    try:
        import paho.mqtt.client as mqtt
    except ImportError:
        print("\n❌ ERROR: paho-mqtt no está instalado")
        print()
        print("Instalar con:")
        print("  pip3 install paho-mqtt --user")
        print()
        print("O ejecutar:")
        print("  bash install_all_deps.sh")
        print()
        sys.exit(1)
    
    main()