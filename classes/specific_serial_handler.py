from datetime import datetime
from classes.serial_port_handler import SerialPortHandler
from app_utils.queue_operations import SafeQueue
import re
import time
import serial
from typing import Dict, Any
import threading

class Specific_Serial_Handler_Template(SerialPortHandler):
    def __init__(self, config: Dict[str, Any], eventSeverityLevels: Dict[str, int], queue: SafeQueue):
        super().__init__(config, eventSeverityLevels, queue)
        self.report_delimiter = "Set the delimiter"
        self.max_report_delimiter_count = 4

    def parse_string_event(self, event: str) -> Dict[str, Any] | None:
        # Implement the parsing logic here
        pass

class Edwards_iO1000(SerialPortHandler):
    def __init__(self, config: Dict[str, Any], eventSeverityLevels: Dict[str, int], queue: SafeQueue):
        super().__init__(config, eventSeverityLevels, queue)
        self.report_delimiter = "-----------------"
        self.max_report_delimiter_count = 4
        self.serial_config = {
            "baudrate": 9600,
            "bytesize": 8,
            "parity": "none",
            "stopbits": 1,
            "xonxoff": False,
            "timeout": 1
        }

    def process_incoming_data(self, shutdown_flag: threading.Event) -> None:
        """
        Override para Edwards iO1000: procesa cada línea como un evento individual
        sin esperar líneas vacías, ya que el panel no las envía.
        """
        buffer = ""

        if self.ser is None:
            raise ValueError("Serial port is not initialized")

        try:
            while not shutdown_flag.is_set():
                if self.ser.in_waiting > 0:
                    raw_data = self.ser.readline()
                    incoming_line = raw_data.decode('latin-1').strip()
                    
                    # Log de datos recibidos
                    if incoming_line:
                        self.logger.debug(f"📡 Serial data received: {repr(incoming_line)}")
                        
                        # Para Edwards iO1000, cada línea es un evento completo
                        # No esperamos líneas vacías
                        self.logger.debug(f"🎯 Processing as complete event...")
                        self.publish_parsed_event(incoming_line)
                else:
                    time.sleep(0.1)
        except (serial.SerialException, serial.SerialTimeoutException, OSError) as e:
            raise serial.SerialException(str(e))
        except (TypeError, UnicodeDecodeError) as e:
            self.logger.error(f"Error decoding data: {e}")
            raise TypeError(str(e))
        except Exception as e:
            raise Exception(f"Unexpected failure occurred: {str(e)}")

    def parse_string_event(self, event: str) -> Dict[str, Any] | None:
        """
        Parser híbrido que soporta dos formatos de Edwards iO1000:
        1. Con pipe: 'EVENTO|FECHA HORA DETALLES'
        2. Con espacios múltiples: 'EVENTO                FECHA HORA DETALLES'
        """
        try:
            lines = list(filter(None, event.strip().split('\n')))
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
                parts = re.split(r'\s{2,}', line.strip())
                
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
                description += "\n" + "\n".join(lines[1:])

            return {
                "event": ID_Event,
                "description": description,
                "severity": self.eventSeverityLevels.get(ID_Event, self.default_event_severity_not_recognized),
                "SBC_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
                "FACP_date": FACP_date
            }

        except Exception as e:
            self.logger.exception(f"An error occurred while parsing the event: {event}")
            return None
class Edwards_EST3x(SerialPortHandler):
    def __init__(self, config: Dict[str, Any], eventSeverityLevels: Dict[str, int], queue: SafeQueue):
        super().__init__(config, eventSeverityLevels, queue)
        self.report_delimiter = "-----------------"
        self.max_report_delimiter_count = 2
        self.end_report_delimiter = "**"
        self.serial_config = {
            "baudrate": 9600,
            "bytesize": 8,
            "parity": "none",
            "stopbits": 1,
            "xonxoff": False,
            "timeout": 1
        }


    def parse_string_event(self, event: str) -> Dict[str, Any] | None:
        try:
            lines = list(filter(None, event.strip().split('\n')))
            if not lines:
                self.logger.error(f"Invalid event received: {event}")
                return None

            primary_data = lines[0][1:].split('-') if lines[0][0] == "-" else lines[0].split('::')
            if len(primary_data) < 2:
                self.logger.error(f"Invalid event received: {event}")
                return None

            ID_Event = primary_data[0].strip()
            time_date_metadata = primary_data[1].strip().split()
            FACP_date = f"{time_date_metadata[0]} {time_date_metadata[1]}"

            description = " | ".join(time_date_metadata[2:])
            if len(lines) > 1:
                description += "\n" + "\n".join(lines[1:])

            return {
                "event": ID_Event,
                "description": description,
                "severity": self.eventSeverityLevels.get(ID_Event, self.default_event_severity_not_recognized),
                "SBC_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
                "FACP_date": FACP_date
            }

        except Exception as e:
            self.logger.exception(f"An error occurred while parsing the event: {event}")
            return None

    def check_last_line(self, string: str) -> bool:
        last_newline = string.rfind('\n', 0, string.rfind('\n'))
        last_line = string[last_newline+1:]
        return self.end_report_delimiter in last_line
    
    def handle_empty_line(self, buffer: str, report_count: int) -> bool:
        if report_count == 0 and buffer.strip() and self.check_last_line(buffer):
            self.logger.debug("Empty report parsed. Skipping.")
            return True
        if report_count == self.max_report_delimiter_count and buffer.strip() and self.check_last_line(buffer):
            self.logger.debug("Report parsed.")
            self.publish_parsed_report(buffer)
            return True
        elif report_count == 0 and buffer.strip():
            self.publish_parsed_event(buffer)
            return True
        else:
            return False

class Notifier_NFS(SerialPortHandler):
    def __init__(self, config: Dict[str, Any], eventSeverityLevels: Dict[str, int], queue: SafeQueue):
        super().__init__(config, eventSeverityLevels, queue)
        self.report_delimiter = "************"
        self.max_report_delimiter_count = 2
        self.serial_config = {
            "baudrate": 9600,
            "bytesize": 7,
            "parity": "even",
            "stopbits": 1,
            "xonxoff": True,
            "timeout": 1
        }

    def parse_string_event(self, event: str) -> Dict[str, Any] | None:
        try:
            lines = list(filter(None, event.strip().split('\n')))
            if not lines:
                self.logger.error(f"Invalid event received: {event}")
                return None

            primary_data = re.split(r'\s{3,}', lines[0])
            if len(primary_data) < 2:
                self.logger.error(f"Invalid event received: {event}")
                return None

            ID_Event = primary_data[0].strip()
            description = ' / '.join(primary_data[1:]).strip()

            if len(lines) > 1:
                description += "\n" + "\n".join(lines[1:])

            severity = 3 if ":" in ID_Event else self.eventSeverityLevels.get(ID_Event, self.default_event_severity_not_recognized)

            return {
                "event": ID_Event,
                "description": description,
                "severity": severity,
                "SBC_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
                "FACP_date": ""  # Notifier_NFS320 doesn't provide a panel date
            }

        except Exception as e:
            self.logger.exception(f"An error occurred while parsing the event: {event}")
            return None
    
    def process_incoming_data(self, shutdown_flag: threading.Event) -> None:
        buffer = ""
        report_count = 0
        add_blank_line = False
        try:
            while not shutdown_flag.is_set():
                if self.ser and (self.ser.in_waiting > 0 or add_blank_line):
                    if add_blank_line:
                        add_blank_line = False  
                        if_eof = self.handle_empty_line(buffer, report_count)
                        if if_eof:
                            buffer = ""
                            report_count = 0
                    else:
                        raw_data = self.ser.readline()
                        incoming_line = raw_data.decode('latin-1').strip()
                        buffer, report_count = self.handle_data_line(incoming_line, buffer, report_count)
                        add_blank_line = True 
                else:
                    time.sleep(0.1)
        except (serial.SerialException, serial.SerialTimeoutException) as e:
            raise serial.SerialException(str(e))
        except (TypeError, UnicodeDecodeError) as e:
            if buffer:
                if report_count > 0:
                    self.publish_parsed_report(buffer)
                else:
                    self.publish_parsed_event(buffer)
            raise TypeError(str(e))
        except Exception as e:
            raise Exception(f"Unexpected failure occurred: {str(e)}")
        
class Simplex(SerialPortHandler):
    def __init__(self, config: Dict[str, Any], eventSeverityLevels: Dict[str, int], queue: SafeQueue):
        super().__init__(config, eventSeverityLevels, queue)
        self.report_delimiter = "************"
        self.max_report_delimiter_count = 2
        self.serial_config = {
            "baudrate": 9600,
            "bytesize": 7,
            "parity": "even",
            "stopbits": 1,
            "timeout": 1
        }

    def parse_string_event(self, event: str) -> Dict[str, Any] | None:
            """
            Parser híbrido que soporta dos formatos de Edwards iO1000:
            1. Con pipe: 'EVENTO|FECHA HORA DETALLES'
            2. Con espacios múltiples: 'EVENTO                FECHA HORA DETALLES'
            """
            try:
                lines = list(filter(None, event.strip().split('\n')))
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
                    parts = re.split(r'\s{2,}', line.strip())
                    
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
                    description += "\n" + "\n".join(lines[1:])

                return {
                    "event": ID_Event,
                    "description": description,
                    "severity": self.eventSeverityLevels.get(ID_Event, self.default_event_severity_not_recognized),
                    "SBC_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
                    "FACP_date": FACP_date
                }

            except Exception as e:
                self.logger.exception(f"An error occurred while parsing the event: {event}")
                return None
                
    def process_incoming_data(self, shutdown_flag: threading.Event) -> None:
        if self.ser is None:
            raise ValueError("Serial port is not initialized")

        try:
            while not shutdown_flag.is_set():
                if self.ser.in_waiting > 0:
                    raw_data = self.ser.readline()
                    data = raw_data.decode('latin-1')
                    
                    # Skip empty or null bytes
                    if data.strip() == '' or data == '\x00':
                        continue

                    # Split into individual events (split on timestamp pattern)
                    timestamp_pattern = r'(?=\s*\d{1,2}:\d{2}:\d{2} [ap]m\s+[A-Z]{3} \d{2}-[A-Z]{3}-\d{2})'
                    events = re.split(timestamp_pattern, data)
                    
                    # Process each event
                    for event in events:
                        if event.strip():  # Skip empty events
                            # Clean up the event
                            event = event.strip()
                            if event.endswith('\r\r'):
                                event = event[:-1]  # Remove one \r to leave only one
                            # Convert \r to \n between timestamp and message
                            event_parts = event.split('\r', 1)
                            if len(event_parts) == 2:
                                cleaned_event = f"{event_parts[0].strip()}\n{event_parts[1].strip()}"
                                self.publish_parsed_event(cleaned_event)
                else:
                    time.sleep(0.1)
                    
        except (serial.SerialException, serial.SerialTimeoutException, OSError) as e:
            raise serial.SerialException(str(e))
        except (TypeError, UnicodeDecodeError) as e:
            raise TypeError(str(e))
        except Exception as e:
            raise Exception(f"Unexpected failure occurred: {str(e)}")
