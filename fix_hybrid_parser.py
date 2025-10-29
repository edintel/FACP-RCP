#!/usr/bin/env python3
"""
PARCHE FINAL: Parser híbrido para Edwards iO1000

Soporta AMBOS formatos:
1. Con pipe: 'EVENTO|FECHA HORA DETALLES'
2. Con espacios: 'EVENTO                           FECHA HORA DETALLES'
"""

import os
import shutil
import re
from datetime import datetime

def apply_hybrid_parser():
    """Aplica parser que soporta ambos formatos"""
    
    file_path = "/home/edintel/Desktop/app/classes/specific_serial_handler.py"
    
    # Hacer backup
    backup_path = f"{file_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    print("=" * 80)
    print("🔧 APLICANDO PARSER HÍBRIDO PARA EDWARDS iO1000")
    print("=" * 80)
    print()
    
    if not os.path.exists(file_path):
        print(f"❌ No se encontró el archivo: {file_path}")
        return False
    
    print(f"📦 Creando backup: {backup_path}")
    shutil.copy2(file_path, backup_path)
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Buscar la clase Edwards_iO1000
    if 'class Edwards_iO1000(SerialPortHandler):' not in content:
        print("❌ No se encontró la clase Edwards_iO1000")
        return False
    
    # Nuevo parser híbrido
    new_parser = '''    def parse_string_event(self, event: str) -> Dict[str, Any] | None:
        """
        Parser híbrido que soporta dos formatos de Edwards iO1000:
        1. Con pipe: 'EVENTO|FECHA HORA DETALLES'
        2. Con espacios múltiples: 'EVENTO                FECHA HORA DETALLES'
        """
        try:
            lines = list(filter(None, event.strip().split('\\n')))
            if not lines:
                self.logger.error(f"Invalid event received: {event}")
                return None

            line = lines[0]
            
            # Intentar primero con pipe '|' (formato original)
            if '|' in line:
                primary_data = line.split('|')
                if len(primary_data) >= 2:
                    ID_Event = primary_data[0].strip()
                    time_date_metadata = primary_data[1].strip().split()
                else:
                    self.logger.error(f"Invalid pipe format: {event}")
                    return None
            else:
                # Si no tiene pipe, usar espacios múltiples (2 o más)
                parts = re.split(r'\\s{2,}', line.strip())
                
                if len(parts) >= 2:
                    ID_Event = parts[0].strip()
                    time_date_metadata = parts[1].strip().split()
                else:
                    self.logger.error(f"Invalid space format: {event}")
                    return None
            
            # Validar que tenemos al menos fecha y hora
            if len(time_date_metadata) < 2:
                self.logger.error(f"Invalid date/time format: {event}")
                return None
            
            FACP_date = f"{time_date_metadata[0]} {time_date_metadata[1]}"
            
            # Descripción es el resto de los metadatos
            description = " | ".join(time_date_metadata[2:]) if len(time_date_metadata) > 2 else ""
            
            # Agregar líneas adicionales si existen
            if len(lines) > 1:
                description += "\\n" + "\\n".join(lines[1:])

            return {
                "event": ID_Event,
                "description": description,
                "severity": self.eventSeverityLevels.get(ID_Event, self.default_event_severity_not_recognized),
                "SBC_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
                "FACP_date": FACP_date
            }

        except Exception as e:
            self.logger.exception(f"An error occurred while parsing the event: {event}")
            return None'''
    
    # Buscar y reemplazar el método parse_string_event en Edwards_iO1000
    # Patrón para encontrar el método completo
    pattern = r'(class Edwards_iO1000\(SerialPortHandler\):.*?)(    def parse_string_event\(self, event: str\).*?(?=\n    def |\nclass |\Z))'
    
    def replace_parser(match):
        class_start = match.group(1)
        # Reemplazar todo el método parse_string_event
        return class_start + new_parser
    
    new_content = re.sub(pattern, replace_parser, content, flags=re.DOTALL)
    
    if new_content != content:
        with open(file_path, 'w') as f:
            f.write(new_content)
        
        print("✅ Parser híbrido aplicado exitosamente")
        print()
        print("📋 Cambios realizados:")
        print("   - Parser ahora soporta AMBOS formatos:")
        print("     1. Con pipe (|): 'EVENTO|FECHA HORA DETALLES'")
        print("     2. Con espacios: 'EVENTO          FECHA HORA DETALLES'")
        print("   - Detecta automáticamente el formato")
        print()
        print("✅ Formatos soportados:")
        print("   ✓ 'HUMO ACT|12:30P 102325 Detalles'")
        print("   ✓ 'ACTIVA SLENC.REMOTO SILENCIO PANEL    07:58A 102325 1M002'")
        print()
        print("🔄 SIGUIENTE PASO:")
        print("   sudo systemctl restart serial-to-mqtt.service")
        print()
        print(f"💾 Backup guardado en: {backup_path}")
        
        return True
    else:
        print("❌ No se pudo aplicar el parche automáticamente")
        print()
        print("Por favor, aplica el parche manualmente siguiendo:")
        print("  MANUAL_HYBRID_PARSER.md")
        
        return False

if __name__ == "__main__":
    print()
    success = apply_hybrid_parser()
    print()
    print("=" * 80)
    
    if success:
        print("✅ PARCHE APLICADO")
        print()
        print("Ahora ejecuta:")
        print("  1. sudo systemctl restart serial-to-mqtt.service")
        print("  2. journalctl -u serial-to-mqtt.service -f")
        print("  3. Activa un evento en el panel")
        print("  4. Deberías ver '✅ Event queued successfully'")
        print()
        print("El parser ahora acepta eventos con '|' o con espacios múltiples.")
    else:
        print("❌ APLICACIÓN MANUAL REQUERIDA")
        print()
        print("Ver: MANUAL_HYBRID_PARSER.md para instrucciones")
    
    print("=" * 80)
    print()