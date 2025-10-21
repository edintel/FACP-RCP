import logging
from config.loader import ConfigSchema
from classes.mqtt_sender import MqttHandler
from classes.specific_serial_handler import Edwards_iO1000, Edwards_EST3x, Notifier_NFS, Simplex
from app_utils.queue_operations import SafeQueue
from components.update_app import update_check_thread
from components.relay_controller import RelayController
from components.silence_controller import SilenceController  # NUEVO
from components.queue_manager import QueueManager
from components.thread_manager import ThreadManager
from classes.relay_monitor import RelayMonitor
from classes.serial_port_handler import SerialPortHandler

class Application:
    def __init__(self, config: ConfigSchema, event_severity_levels: dict):
        self.config = config
        self.event_severity_levels = event_severity_levels
        self.queue = SafeQueue()
        self.mqtt_handler = MqttHandler(self.config, self.queue)
        self.id_modelo_panel: int = self.config.id_modelo_panel
        self.serial_handler: SerialPortHandler = None

        self.queue_manager = QueueManager(self.queue, "queue_backup.pkl")
        self.relay_controller = RelayController(config.relay)
        self.silence_controller = SilenceController(config.silence_relay, self.mqtt_handler)  # NUEVO
        self.relay_monitor = RelayMonitor(config, self.mqtt_handler)
        self.thread_manager = ThreadManager()

        self.logger = logging.getLogger(__name__)

    def _create_serial_handler(self):
        severity_list = self.event_severity_levels.get(self.id_modelo_panel, {})
        
        handlers = {
            10001: Edwards_iO1000,
            10002: Edwards_EST3x,
            10003: Notifier_NFS,
            10004: Simplex
        }
        
        handler_class = handlers.get(self.id_modelo_panel)
        if not handler_class:
            raise ValueError(f"Unsupported panel model: {self.id_modelo_panel}")
        
        return handler_class(self.config, severity_list, self.queue)

    def start(self):
        self.logger.info("Starting application...")
        self.queue_manager.load_queue()
        self.mqtt_handler.start()
        
        # Suscribirse al atributo de silencio en ThingsBoard
        self._setup_silence_subscription()
        
        self.serial_handler = self._create_serial_handler()
        
        threads = [
            self.queue_manager.save_queue_periodically,
            self.relay_monitor.monitor_relays,
            self.relay_controller.relay_control,
            self.serial_handler.listening_to_serial
        ]

        self.thread_manager.start_threads(threads)

        try:
            self.thread_manager.monitor_threads()
        except KeyboardInterrupt:
            self.logger.info("Program terminated by user")
        finally:
            self.shutdown()

    def _setup_silence_subscription(self):
        """Configura la suscripción al atributo de silencio en ThingsBoard"""
        try:
            # Suscribirse a cambios en el atributo 'silence_panel'
            self.mqtt_handler.subscribe_to_attribute(
                'silence_panel', 
                self.silence_relay_controller.handle_attribute_update
            )
            self.logger.info("Subscribed to 'silence_panel' attribute in ThingsBoard")
            
            # Opcionalmente, solicitar el valor actual del atributo
            self.mqtt_handler.request_attributes(
                client_attribute_names=[],
                shared_attribute_names=['silence_panel'],
                callback=self.silence_relay_controller.handle_attribute_update
            )
        except Exception as e:
            self.logger.error(f"Error setting up silence subscription: {e}")

    def shutdown(self):
        self.logger.info("Initiating graceful shutdown...")
        self.thread_manager.stop_all_threads()
        self.queue_manager.save_queue()
        self.relay_controller.cleanup()
        self.silence_relay_controller.cleanup()  # NUEVO
        self.relay_monitor.cleanup()
        self.mqtt_handler.stop()
        self.logger.info("Graceful shutdown completed")
