#!/usr/bin/env python3
"""
PARCHE: Activar logging detallado en serial_port_handler.py

Este script modifica el archivo serial_port_handler.py para activar
todos los logs DEBUG que están comentados.
"""

import os
import shutil
from datetime import datetime

def apply_debug_logging_patch():
    """Aplica el parche de logging al serial_port_handler.py"""
    
    file_path = "/home/edintel/Desktop/app/classes/serial_port_handler.py"
    
    # Hacer backup
    backup_path = f"{file_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    print("=" * 80)
    print("🔧 APLICANDO PARCHE DE LOGGING DEBUG")
    print("=" * 80)
    print()
    
    # Verificar que existe
    if not os.path.exists(file_path):
        print(f"❌ No se encontró el archivo: {file_path}")
        return False
    
    # Hacer backup
    print(f"📦 Creando backup: {backup_path}")
    shutil.copy2(file_path, backup_path)
    
    # Leer el archivo
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Aplicar cambios
    modifications = 0
    
    # 1. Activar log en process_incoming_data cuando se recibe data
    if 'incoming_line = raw_data.decode' in content:
        # Agregar logging después del decode
        old = """                    raw_data = self.ser.readline()
                    incoming_line = raw_data.decode('latin-1').strip()
                    if not incoming_line:"""
        
        new = """                    raw_data = self.ser.readline()
                    incoming_line = raw_data.decode('latin-1').strip()
                    
                    # DEBUG: Log de datos recibidos
                    if incoming_line:
                        self.logger.debug(f"📡 Serial data received: {repr(incoming_line)}")
                    
                    if not incoming_line:"""
        
        if old in content:
            content = content.replace(old, new)
            modifications += 1
            print("✅ Agregado logging en process_incoming_data")
    
    # 2. Activar log en handle_empty_line cuando se detecta evento
    if 'elif report_count == 0 and buffer.strip():' in content:
        old = """        elif report_count == 0 and buffer.strip():
            self.publish_parsed_event(buffer)
            return True"""
        
        new = """        elif report_count == 0 and buffer.strip():
            self.logger.debug(f"🎯 Detected complete event, publishing...")
            self.logger.debug(f"📥 Buffer content: {repr(buffer)}")
            self.publish_parsed_event(buffer)
            return True"""
        
        if old in content:
            content = content.replace(old, new)
            modifications += 1
            print("✅ Agregado logging en handle_empty_line")
    
    # 3. Mejorar log en publish_parsed_event
    if 'def publish_parsed_event(self, buffer: str)' in content:
        old = """    def publish_parsed_event(self, buffer: str) -> None:
        parsed_data = self.parse_string_event(buffer)
        if parsed_data is not None:
            self.logger.info(f'Event queued: {parsed_data}')
            self.queue.put((PublishType.TELEMETRY, parsed_data))
        else:
            self.logger.debug("The parsed event information is empty, skipping MQTT publish.")"""
        
        new = """    def publish_parsed_event(self, buffer: str) -> None:
        self.logger.debug(f"📥 Raw buffer received for parsing: {repr(buffer[:100])}...")
        parsed_data = self.parse_string_event(buffer)
        if parsed_data is not None:
            self.logger.info(f'✅ Event queued successfully: {parsed_data["event"]} (severity: {parsed_data["severity"]})')
            self.logger.debug(f'   Full event data: {parsed_data}')
            self.queue.put((PublishType.TELEMETRY, parsed_data))
            self.logger.debug(f'   Queue size after adding: {self.queue.qsize()}')
        else:
            self.logger.warning(f"❌ Failed to parse event. Buffer was: {repr(buffer[:200])}")
            self.logger.debug("The parsed event information is empty, skipping MQTT publish.")"""
        
        if old in content:
            content = content.replace(old, new)
            modifications += 1
            print("✅ Mejorado logging en publish_parsed_event")
    
    # 4. Activar log de inicio en listening_to_serial
    if 'def listening_to_serial' in content:
        old = """            try:
                self.open_serial_port()
                self.process_incoming_data(shutdown_flag)"""
        
        new = """            try:
                self.open_serial_port()
                self.logger.info("🎧 Started listening to serial port...")
                self.process_incoming_data(shutdown_flag)"""
        
        if old in content:
            content = content.replace(old, new)
            modifications += 1
            print("✅ Agregado logging en listening_to_serial")
    
    # Escribir el archivo modificado
    if modifications > 0:
        with open(file_path, 'w') as f:
            f.write(content)
        
        print()
        print(f"✅ Parche aplicado exitosamente ({modifications} modificaciones)")
        print()
        print("📋 Cambios realizados:")
        print("   - Logging detallado de datos recibidos del serial")
        print("   - Logging de buffers antes de parsear")
        print("   - Logging mejorado de eventos parseados")
        print("   - Logging de tamaño de cola")
        print()
        print("🔄 SIGUIENTE PASO:")
        print("   sudo systemctl restart serial-to-mqtt.service")
        print()
        print("📊 Para ver los logs:")
        print("   journalctl -u serial-to-mqtt.service -f")
        print()
        print(f"💾 Backup guardado en: {backup_path}")
        
        return True
    else:
        print("⚠️  No se encontraron las secciones esperadas para modificar")
        print("   El archivo puede haber sido modificado previamente")
        return False

if __name__ == "__main__":
    print()
    success = apply_debug_logging_patch()
    print()
    print("=" * 80)
    
    if success:
        print("✅ PARCHE APLICADO")
        print()
        print("Ahora ejecuta:")
        print("  1. sudo systemctl restart serial-to-mqtt.service")
        print("  2. journalctl -u serial-to-mqtt.service -f")
        print("  3. Activa un evento en el panel")
        print("  4. Observa los logs detallados")
    else:
        print("❌ NO SE PUDO APLICAR EL PARCHE")
        print()
        print("Alternativa manual:")
        print("  1. Edita: /home/edintel/Desktop/app/classes/serial_port_handler.py")
        print("  2. Busca las líneas con 'self.logger.debug'")
        print("  3. Descoméntalas o agrégalas")
    
    print("=" * 80)
    print()
