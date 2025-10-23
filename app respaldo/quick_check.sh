#!/bin/bash

echo "================================================================================"
echo "🔍 VERIFICACIÓN RÁPIDA DEL SISTEMA - Serial to MQTT Gateway"
echo "================================================================================"
echo ""

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 1. Verificar que el servicio esté corriendo
echo "1️⃣  Verificando estado del servicio..."
if systemctl is-active --quiet serial-to-mqtt.service; then
    echo -e "   ${GREEN}✅ Servicio ACTIVO${NC}"
else
    echo -e "   ${RED}❌ Servicio NO está activo${NC}"
    echo "      Iniciar con: sudo systemctl start serial-to-mqtt.service"
fi
echo ""

# 2. Verificar logs recientes
echo "2️⃣  Últimos mensajes del servicio (últimos 20)..."
echo "   -------------------------------------------------------------------"
journalctl -u serial-to-mqtt.service -n 20 --no-pager | tail -10
echo "   -------------------------------------------------------------------"
echo ""

# 3. Verificar conexión MQTT
echo "3️⃣  Verificando conexión MQTT a ThingsBoard..."
if journalctl -u serial-to-mqtt.service -n 100 --no-pager | grep -q "Connected to ThingsBoard successfully"; then
    echo -e "   ${GREEN}✅ MQTT conectado exitosamente${NC}"
else
    echo -e "   ${YELLOW}⚠️  No se encontró confirmación de conexión MQTT${NC}"
    echo "      Verifica las credenciales en config/config.yml"
fi
echo ""

# 4. Verificar eventos recibidos
echo "4️⃣  Verificando eventos del serial..."
SERIAL_EVENTS=$(journalctl -u serial-to-mqtt.service -n 100 --no-pager | grep -c "Serial data received\|data received" || echo "0")
echo "   Datos recibidos del serial: $SERIAL_EVENTS mensajes"

QUEUED_EVENTS=$(journalctl -u serial-to-mqtt.service -n 100 --no-pager | grep -c "Event queued" || echo "0")
echo "   Eventos añadidos a la cola: $QUEUED_EVENTS eventos"

SENT_EVENTS=$(journalctl -u serial-to-mqtt.service -n 100 --no-pager | grep -c "Telemetry sent successfully" || echo "0")
echo "   Telemetría enviada: $SENT_EVENTS mensajes"
echo ""

# 5. Verificar errores
echo "5️⃣  Buscando errores recientes..."
ERROR_COUNT=$(journalctl -u serial-to-mqtt.service -n 100 --no-pager | grep -c "ERROR\|Error\|error" || echo "0")
if [ "$ERROR_COUNT" -gt 0 ]; then
    echo -e "   ${YELLOW}⚠️  Se encontraron $ERROR_COUNT errores${NC}"
    echo "   Últimos errores:"
    journalctl -u serial-to-mqtt.service -n 100 --no-pager | grep "ERROR\|Error\|error" | tail -3
else
    echo -e "   ${GREEN}✅ No se encontraron errores recientes${NC}"
fi
echo ""

# 6. Verificar archivo de configuración
echo "6️⃣  Verificando configuración..."
if [ -f "/home/edintel/Desktop/app/config/config.yml" ]; then
    echo -e "   ${GREEN}✅ Archivo config.yml encontrado${NC}"
    
    # Verificar que el evento esté en eventSeverityLevels.yml
    if grep -q "ACTIVA SLENC.REMOTO SILENCIO PANEL" "/home/edintel/Desktop/app/config/eventSeverityLevels.yml" 2>/dev/null; then
        echo -e "   ${GREEN}✅ Evento de silencio configurado en eventSeverityLevels.yml${NC}"
    else
        echo -e "   ${RED}❌ Evento de silencio NO encontrado en eventSeverityLevels.yml${NC}"
        echo "      Agregar: 'ACTIVA SLENC.REMOTO SILENCIO PANEL: 2'"
    fi
else
    echo -e "   ${RED}❌ Archivo config.yml NO encontrado${NC}"
fi
echo ""

# 7. Verificar puerto serial
echo "7️⃣  Verificando puerto serial..."
if [ -e "/dev/serial-adapter" ]; then
    echo -e "   ${GREEN}✅ Puerto /dev/serial-adapter existe${NC}"
elif [ -e "/dev/ttyUSB0" ]; then
    echo -e "   ${YELLOW}⚠️  Puerto /dev/serial-adapter no existe, pero /dev/ttyUSB0 sí${NC}"
    echo "      Verifica el puerto en config.yml"
else
    echo -e "   ${RED}❌ No se encontró ningún puerto serial${NC}"
    echo "      Puertos disponibles:"
    ls -la /dev/tty* 2>/dev/null | grep -E "USB|ACM" | head -5
fi
echo ""

# 8. Resumen y diagnóstico
echo "================================================================================"
echo "📊 RESUMEN Y DIAGNÓSTICO"
echo "================================================================================"
echo ""

# Determinar el problema principal
if [ "$SERIAL_EVENTS" -eq 0 ]; then
    echo -e "${RED}🔴 PROBLEMA: No se reciben datos del serial${NC}"
    echo "   Posibles causas:"
    echo "   - Puerto serial incorrecto o desconectado"
    echo "   - Panel no está enviando datos"
    echo "   - Permisos del puerto serial"
    echo ""
    echo "   Acciones:"
    echo "   1. Verificar conexión física"
    echo "   2. Verificar puerto: ls -la /dev/tty*"
    echo "   3. Dar permisos: sudo chmod 666 /dev/ttyUSB0"
    
elif [ "$QUEUED_EVENTS" -eq 0 ] && [ "$SERIAL_EVENTS" -gt 0 ]; then
    echo -e "${RED}🔴 PROBLEMA: Se reciben datos pero no se procesan eventos${NC}"
    echo "   Posibles causas:"
    echo "   - El evento no está en eventSeverityLevels.yml"
    echo "   - Error en el parser del evento"
    echo ""
    echo "   Acciones:"
    echo "   1. Verificar que el evento esté en eventSeverityLevels.yml"
    echo "   2. Ver logs detallados: journalctl -u serial-to-mqtt.service -f"
    
elif [ "$SENT_EVENTS" -eq 0 ] && [ "$QUEUED_EVENTS" -gt 0 ]; then
    echo -e "${YELLOW}🟡 PROBLEMA: Eventos en cola pero no se envían${NC}"
    echo "   Posibles causas:"
    echo "   - MQTT no está conectado"
    echo "   - process_queue() no está corriendo"
    echo "   - Credenciales incorrectas"
    echo ""
    echo "   Acciones:"
    echo "   1. Verificar conexión: grep 'Connected to ThingsBoard' app.log"
    echo "   2. Verificar credenciales en config.yml"
    echo "   3. Probar conectividad: ping mqtt.thingsboard.cloud"
    
elif [ "$SENT_EVENTS" -gt 0 ]; then
    echo -e "${GREEN}🟢 SISTEMA FUNCIONANDO CORRECTAMENTE${NC}"
    echo "   - Datos del serial: ✅"
    echo "   - Eventos procesados: ✅"
    echo "   - Telemetría enviada: ✅"
    echo ""
    echo "   Si aún no ves los datos en ThingsBoard:"
    echo "   1. Verifica que estés en el dispositivo correcto"
    echo "   2. Ve a 'Latest telemetry' en ThingsBoard"
    echo "   3. Busca las claves: event, description, severity"
    echo "   4. Verifica el device_token en config.yml"
else
    echo -e "${YELLOW}🟡 ESTADO INDETERMINADO${NC}"
    echo "   Revisar logs completos:"
    echo "   journalctl -u serial-to-mqtt.service -n 200 --no-pager > /tmp/full.log"
fi

echo ""
echo "================================================================================"
echo "💡 COMANDOS ÚTILES"
echo "================================================================================"
echo ""
echo "  Ver logs en tiempo real:"
echo "    journalctl -u serial-to-mqtt.service -f"
echo ""
echo "  Reiniciar servicio:"
echo "    sudo systemctl restart serial-to-mqtt.service"
echo ""
echo "  Ver últimos 100 logs:"
echo "    journalctl -u serial-to-mqtt.service -n 100 --no-pager"
echo ""
echo "  Analizar logs en detalle:"
echo "    python3 analyze_logs.py"
echo ""
echo "================================================================================"
