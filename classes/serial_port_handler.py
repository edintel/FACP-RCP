import serial
from app_utils.queue_operations import SafeQueue
from typing import Tuple, Dict, Any
from classes.enums import PublishType
import time
import logging
import threading
from config.schema import ConfigSchema
import re

class SerialPortHandler:
    def __init__(self, config: ConfigSchema, eventSeverityLevels: Dict[str, int], queue: SafeQueue):
        self.config = config
        self.queue = queue
        self.eventSeverityLevels = eventSeverityLevels
        self.ser: serial.Serial | None = None
        self.logger = logging.getLogger(__name__)
        self.report_delimiter = ""
        self.max_report_delimiter_count = -1
        self.default_event_severity_not_recognized = 0
        self.parity_dic = {'none': serial.PARITY_NONE, 
            'even': serial.PARITY_EVEN,
            'odd': serial.PARITY_ODD
        }
        self.attempt = 0
        self.max_reconnect_delay = 60
        self.base_delay = 1
        self.serial_config = {}
        
        # Pattern para detectar líneas con timestamp (fin de mensaje)
        # Formato: HH:MMA DDMMYY XXX (ejemplo: 08:57A 102925 Mie)
        self.timestamp_pattern = re.compile(r'\d{1,2}:\d{2}[AP]\s+\d{6}\s+\w+\s*$')

    def init_serial_port(self) -> None:
        self.ser = serial.Serial(
            port=self.config.serial.puerto,
            baudrate=self.serial_config.get('baudrate'),
            bytesize=self.serial_config.get('bytesize'),
            parity=self.parity_dic[self.serial_config.get('parity')],
            stopbits=self.serial_config.get('stopbits'),
            xonxoff=self.serial_config.get('xonxoff'),
            timeout=self.serial_config.get('timeout')
        )

    def open_serial_port(self) -> None:
        try:
            if self.ser is None:
                self.init_serial_port()
            if not self.ser.is_open:
                self.ser.open()
                self.queue.is_serial_connected = True
            self.logger.debug("Serial connected")
                
        except serial.SerialException as e:
            raise serial.SerialException(f"An error occurred while opening the specified port: {e}")
        
    def publish_parsed_report(self, buffer: str) -> None:
        self.logger.warning("Publish reports is currently not supported. Dismissing report.")

    def publish_parsed_event(self, buffer: str) -> None:
        """Publica un evento parseado a la cola para envío MQTT"""
        # Limpiar el buffer de espacios extra pero mantener la estructura
        buffer = buffer.strip()
        
        if not buffer:
            self.logger.debug("Empty buffer, skipping.")
            return
            
        self.logger.debug(f"📥 Raw event buffer received:\n{repr(buffer)}")
        
        parsed_data = self.parse_string_event(buffer)
        
        if parsed_data is not None:
            # Log detallado del evento parseado
            self.logger.info(f'✅ Event queued successfully:')
            self.logger.info(f'   - Event ID: {parsed_data.get("event")}')
            self.logger.info(f'   - Severity: {parsed_data.get("severity")}')
            self.logger.info(f'   - Description: {parsed_data.get("description")}')
            self.logger.info(f'   - FACP Date: {parsed_data.get("FACP_date")}')
            
            # Advertencia si el evento no tiene severidad asignada
            if parsed_data.get("severity") == 0:
                self.logger.warning(f'⚠️  EVENT NOT IN SEVERITY LIST: "{parsed_data.get("event")}"')
                self.logger.warning(f'    This event will be sent but consider adding it to eventSeverityLevels.yml')
            
            # Poner en la cola
            self.queue.put((PublishType.TELEMETRY, parsed_data))
            self.logger.debug(f'   - Queue size after adding: {self.queue.qsize()}')
        else:
            self.logger.warning(f"❌ Failed to parse event. Buffer was:\n{repr(buffer)}")
            self.logger.debug("The parsed event information is empty, skipping MQTT publish.")

    def parse_string_event(self, event: str) -> Dict[str, Any] | None:
        self.logger.error("The 'parse_string_event' function must be implemented in the specific handler!")
        return None

    def is_complete_message(self, line: str) -> bool:
        """
        Determina si una línea contiene un mensaje completo.
        Un mensaje completo típicamente contiene un timestamp al final.
        Formato esperado: ... HH:MMA DDMMYY XXX
        Ejemplo: REARME DEL SISTEMA    Sys.Initialization    SISTEMA NORMAL   08:57A 102925 Mie
        """
        if not line.strip():
            return False
        
        # Verificar si la línea contiene un timestamp
        if self.timestamp_pattern.search(line):
            return True
        
        # Si no hay timestamp, podría ser un mensaje de reporte
        # o un mensaje parcial que necesita acumularse
        return False

    def attempt_reconnection(self, shutdown_flag: threading.Event) -> None:
        while not shutdown_flag.is_set():
            try:
                self.open_serial_port()
                if self.ser and self.ser.is_open:
                    self.queue.is_serial_connected = True
                    self.attempt = 1
                    break
            except Exception as e:
                self.queue.is_serial_connected = False
                delay = min(self.base_delay * (2 ** self.attempt), self.max_reconnect_delay)
                self.logger.error(f"Error found trying to open serial: {e}. Retrying in {delay} seconds.")
                time.sleep(delay)
                self.attempt += 1
            if shutdown_flag.wait(delay):
                    break

    def close_serial_port(self) -> None:
        if self.ser:
            try:
                if self.ser.is_open:
                    self.ser.close()
                self.logger.info("Serial port closed")
            except Exception as e:
                self.logger.error(f"Error closing serial port: {e}")
        self.ser = None
        self.queue.is_serial_connected = False

    def process_incoming_data(self, shutdown_flag: threading.Event) -> None:
        buffer = ""
        report_count = 0
        last_activity_time = time.time()
        message_timeout = 2.0  # Segundos de timeout para considerar mensaje completo

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
                        last_activity_time = time.time()
                    
                    # Procesar la línea recibida
                    if incoming_line:
                        # Verificar si es un delimitador de reporte
                        if self.report_delimiter and self.report_delimiter in incoming_line:
                            report_count += 1
                            buffer += incoming_line + "\n"
                            self.logger.debug(f"Report delimiter detected. Count: {report_count}")
                        
                        # Verificar si la línea contiene un mensaje completo
                        elif self.is_complete_message(incoming_line):
                            # Si hay buffer acumulado, agregarlo primero
                            if buffer:
                                buffer += incoming_line
                                self.logger.debug(f"🎯 Complete multi-line message detected")
                                if report_count > 0:
                                    self.publish_parsed_report(buffer)
                                else:
                                    self.publish_parsed_event(buffer)
                                buffer = ""
                                report_count = 0
                            else:
                                # Mensaje completo en una sola línea
                                self.logger.debug(f"🎯 Complete single-line message detected")
                                self.publish_parsed_event(incoming_line)
                        else:
                            # Línea parcial, acumular en buffer
                            buffer += incoming_line + "\n"
                            self.logger.debug(f"Partial line accumulated. Buffer size: {len(buffer)} chars")
                    
                    # Línea vacía puede indicar fin de mensaje multi-línea
                    elif buffer:
                        self.logger.debug(f"Empty line received with buffer content")
                        # Verificar si es fin de reporte
                        if report_count == self.max_report_delimiter_count and report_count > 0:
                            self.logger.debug(f"Publishing report (delimiter count matched)")
                            self.publish_parsed_report(buffer)
                        elif buffer.strip():
                            self.logger.debug(f"Publishing accumulated buffer as event")
                            self.publish_parsed_event(buffer)
                        buffer = ""
                        report_count = 0
                
                # Timeout check: Si hay buffer y pasó tiempo sin actividad
                elif buffer and (time.time() - last_activity_time) > message_timeout:
                    self.logger.debug(f"⏱️ Message timeout - publishing accumulated buffer")
                    if report_count > 0:
                        self.publish_parsed_report(buffer)
                    else:
                        self.publish_parsed_event(buffer)
                    buffer = ""
                    report_count = 0
                    last_activity_time = time.time()
                else:
                    time.sleep(0.1)
                    
        except (serial.SerialException, serial.SerialTimeoutException, OSError) as e:
            # Antes de lanzar la excepción, procesar buffer si hay contenido
            if buffer.strip():
                self.logger.warning("Serial error occurred, processing remaining buffer...")
                if report_count > 0:
                    self.publish_parsed_report(buffer)
                else:
                    self.publish_parsed_event(buffer)
            raise serial.SerialException(str(e))
        except (TypeError, UnicodeDecodeError) as e:
            if buffer.strip():
                self.logger.warning("Decode error occurred, processing remaining buffer...")
                if report_count > 0:
                    self.publish_parsed_report(buffer)
                else:
                    self.publish_parsed_event(buffer)
            raise TypeError(str(e))
        except Exception as e:
            raise Exception(f"Unexpected failure occurred: {str(e)}")

    def handle_data_line(self, incoming_line: str, buffer: str, report_count: int) -> Tuple[str, int]:
        """DEPRECATED: Esta función ya no se usa con la nueva lógica"""
        if self.report_delimiter in incoming_line:
            report_count += 1
        buffer += incoming_line + "\n"
        return buffer, report_count

    def handle_empty_line(self, buffer: str, report_count: int) -> bool:
        """DEPRECATED: Esta función ya no se usa con la nueva lógica"""
        if report_count == self.max_report_delimiter_count and buffer.strip():
            self.publish_parsed_report(buffer)
            return True
        elif report_count == 0 and buffer.strip():
            self.logger.debug(f"🎯 Detected complete event, publishing...")
            self.publish_parsed_event(buffer)
            return True
        else:
            return False

    def listening_to_serial(self, shutdown_flag: threading.Event) -> None:
        max_delay = 60  
        delay = 1 
        while not shutdown_flag.is_set():
            try:
                self.open_serial_port()
                self.logger.info("🎧 Started listening to serial port...")
                self.process_incoming_data(shutdown_flag)
            except (serial.SerialException, serial.SerialTimeoutException) as e:
                self.logger.error(f"Lost serial connection. Retrying in 5 seconds. Error: {e} ")
                self.close_serial_port()
                self.attempt_reconnection(shutdown_flag)
            except (TypeError, UnicodeDecodeError) as e:
                self.logger.error(f"Error occurred, strange character found. Resetting the serial: {e}")
                if self.ser:
                    self.ser.reset_input_buffer()
            except Exception as e:
                self.close_serial_port()
                self.logger.error(f"An unexpected error has occurred: {str(e)}")
                delay = min(delay * 2, max_delay) 
                if shutdown_flag.wait(delay):
                    break
            else:
                delay = 1 
        self.close_serial_port()
