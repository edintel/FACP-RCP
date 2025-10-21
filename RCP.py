import paho.mqtt.client as mqtt
import json

BROKER = 'mqtt.thingsboard.cloud'
PORT = 1883
ACCESS_TOKEN = 'WJPwjxsesAFbxoJKhw3x'

def on_connect(client, userdata, flags, rc):
    print(f"Conectado al broker: {rc}")
    # Suscribirse a comandos RPC del servidor
    client.subscribe('v1/devices/me/rpc/request/+')

def on_message(client, userdata, msg):
    print(f"Comando recibido en topic: {msg.topic}")
    data = json.loads(msg.payload.decode())
    print(f"Datos: {data}")
    
    # Extraer el ID de la petición del topic
    request_id = msg.topic.split('/')[-1]
    
    # Procesar el comando
    if data.get('method') == 'encender_led':
        print("Encendiendo LED...")
        # Aquí tu código para encender el LED
        respuesta = {"resultado": "LED encendido"}
    elif data.get('method') == 'apagar_led':
        print("Apagando LED...")
        respuesta = {"resultado": "LED apagado"}
    elif data.get('method') == 'obtener_temperatura':
        respuesta = {"temperatura": 25.5}
    else:
        respuesta = {"error": "Comando no reconocido"}
    
    # Enviar respuesta al servidor
    response_topic = f'v1/devices/me/rpc/response/{request_id}'
    client.publish(response_topic, json.dumps(respuesta))

client = mqtt.Client()
client.username_pw_set(ACCESS_TOKEN)
client.on_connect = on_connect
client.on_message = on_message

client.connect(BROKER, PORT, 60)
client.loop_forever()