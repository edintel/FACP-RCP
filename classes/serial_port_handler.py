import serial
from app_utils.queue_operations import SafeQueue
from typing import Tuple, Dict, Any
from classes.enums import PublishType
import time
import logging
import threading
from config.schema import ConfigSchema

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
        parsed_data = self.parse_string_event(buffer)
        if parsed_data is not None:
            self.logger.info(f'Event queued: {parsed_data}')
            self.queue.put((PublishType.TELEMETRY, parsed_data))
        else:
            self.logger.debug("The parsed event information is empty, skipping MQTT publish.")

    def parse_string_event(self, event: str) -> Dict[str, Any] | None:
        self.logger.error("The 'parse_string_event' function must be implemented in the specific handler!")
        return None

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

        if self.ser is None:
            raise ValueError("Serial port is not initialized")

        try:
            while not shutdown_flag.is_set():
                if self.ser.in_waiting > 0:
                    raw_data = self.ser.readline()
                    incoming_line = raw_data.decode('latin-1').strip()
                    if not incoming_line:
                        if_eof = self.handle_empty_line(buffer, report_count)
                        if if_eof:
                            buffer = ""
                            report_count = 0
                    else:
                        buffer, report_count = self.handle_data_line(incoming_line, buffer, report_count)
                else:
                    time.sleep(0.1)
        except (serial.SerialException, serial.SerialTimeoutException, OSError) as e:
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

    def handle_data_line(self, incoming_line: str, buffer: str, report_count: int) -> Tuple[str, int]:
        if self.report_delimiter in incoming_line:
            report_count += 1
        buffer += incoming_line + "\n"
        return buffer, report_count

    def handle_empty_line(self, buffer: str, report_count: int) -> bool:
        if report_count == self.max_report_delimiter_count and buffer.strip():
            self.publish_parsed_report(buffer)
            return True
        elif report_count == 0 and buffer.strip():
            self.publish_parsed_event(buffer)
            return True
        else:
            return False

    def parse_string_event(self, event: str) -> Dict | None:
        self.logger.error("The 'parse_string_event' function must be implemented!")
        return None

    def listening_to_serial(self, shutdown_flag: threading.Event) -> None:
        max_delay = 60  
        delay = 1 
        while not shutdown_flag.is_set():
            try:
                self.open_serial_port()
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