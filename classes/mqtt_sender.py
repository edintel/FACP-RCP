from tb_device_mqtt import TBDeviceMqttClient
from app_utils.queue_operations import SafeQueue
import logging
from typing import Dict, Any, Callable
import threading
import time
from classes.enums import PublishType
from config.schema import ConfigSchema
import queue
from collections import deque

class APILimitsManager:
    def __init__(self):
        self.second_limit = 100
        self.minute_limit = 3000
        self.hour_limit = 7000
        self.second_window = deque()
        self.minute_window = deque()
        self.hour_window = deque()

    def can_send(self) -> bool:
        current_time = time.time()
        self._update_windows(current_time)
        
        if (len(self.second_window) < self.second_limit and
            len(self.minute_window) < self.minute_limit and
            len(self.hour_window) < self.hour_limit):
            self._add_request(current_time)
            return True
        return False

    def _update_windows(self, current_time: float):
        self._clean_window(self.second_window, current_time - 1)
        self._clean_window(self.minute_window, current_time - 60)
        self._clean_window(self.hour_window, current_time - 3600)

    def _clean_window(self, window: deque, oldest_allowed: float):
        while window and window[0] < oldest_allowed:
            window.popleft()

    def _add_request(self, current_time: float):
        self.second_window.append(current_time)
        self.minute_window.append(current_time)
        self.hour_window.append(current_time)

class MqttHandler:
    def __init__(self, config: ConfigSchema, queue: SafeQueue):
        self.config = config
        self.queue = queue
        self.logger = logging.getLogger(__name__)
        self.reconnect_interval = 5
        self.device_token = config.thingsboard.device_token
        self.tb_host = config.thingsboard.host
        self.tb_port = config.thingsboard.port
        self.client: TBDeviceMqttClient = TBDeviceMqttClient(host=self.tb_host, username=self.device_token, port=self.tb_port)
        self.client.connect()
        self.api_limits_manager = APILimitsManager()
        logging.getLogger('tb_connection').setLevel(logging.WARNING)

    def connect(self):
        try:
            self.client.connect()

        except Exception as e:
            self.logger.error(f"Failed to connect to ThingsBoard: {e}")

    def publish_telemetry(self, telemetry: Dict[str, Any], bypass_queue: bool = False):
        if not self.client.is_connected:
            if bypass_queue:
                self.logger.warning("Not connected to ThingsBoard. Dropping telemetry.")
                return
            else:
                self.logger.warning("Not connected to ThingsBoard. Queueing telemetry.")
                self.queue.put((PublishType.TELEMETRY, telemetry))
                return

        if not self.api_limits_manager.can_send():
            if bypass_queue:
                self.logger.warning("API rate limit reached. Dropping telemetry.")
                return
            else:
                self.logger.warning("API rate limit reached. Queueing telemetry.")
                self.queue.put((PublishType.TELEMETRY, telemetry))
                return

        try:
            self.client.send_telemetry(telemetry)
            self.logger.debug(f"Telemetry sent successfully: {telemetry}")
        except Exception as e:
            self.logger.error(f"Failed to publish telemetry: {e}")
            if not bypass_queue:
                self.queue.put((PublishType.TELEMETRY, telemetry))

    def publish_attributes(self, attributes: Dict[str, Any]):
        if not self.client.is_connected:
            self.logger.warning("Not connected to ThingsBoard. Queueing attributes.")
            self.queue.put((PublishType.ATTRIBUTE, attributes))
            return

        if not self.api_limits_manager.can_send():
            self.logger.warning("API rate limit reached. Queueing attributes.")
            self.queue.put((PublishType.ATTRIBUTE, attributes))
            return

        try:
            self.client.send_attributes(attributes)
            self.logger.debug(f"Attributes sent successfully: {attributes}")
        except Exception as e:
            self.logger.error(f"Failed to publish attributes: {e}")
            self.queue.put((PublishType.ATTRIBUTE, attributes))

    def subscribe_to_attribute(self, attribute_name: str, callback: Callable):
        self.client.subscribe_to_attribute(attribute_name, callback)
        self.logger.info(f"Subscribed to attribute: {attribute_name}")

    def request_attributes(self, client_attribute_names: list, shared_attribute_names: list, callback: Callable):
        self.client.request_attributes(client_attribute_names, shared_attribute_names, callback=callback)

    def process_queue(self):
        while not self.shutdown_flag.is_set():
            if self.client.is_connected:
                try:
                    message_type, message = self.queue.get(block=False)
                    if self.api_limits_manager.can_send():
                        if message_type == PublishType.TELEMETRY:
                            self.publish_telemetry(message)
                        elif message_type == PublishType.ATTRIBUTE:
                            self.publish_attributes(message)
                        else:
                            self.logger.error(f'PublishType {message_type} is not supported')
                    else:
                        self.logger.warning("API rate limit reached. Re-queueing message.")
                        self.queue.put((message_type, message))
                    time.sleep(0.1) 
                except queue.Empty:
                    time.sleep(1)
            else:
                self.logger.warning("Not connected to ThingsBoard. Attempting to reconnect...")
                self.connect()
                time.sleep(self.reconnect_interval)

    def start(self):
        self.connect()
        self.shutdown_flag = threading.Event()
        time.sleep(2)
        threading.Thread(target=self.process_queue, daemon=True).start()
        self.logger.info("MQTT Handler started")

    def stop(self):
        self.shutdown_flag.set()
        if self.client:
            self.client.disconnect()
        self.logger.info("MQTT Handler stopped")