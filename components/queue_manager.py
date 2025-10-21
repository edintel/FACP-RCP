import threading
import logging
from app_utils.file_operations import save_to_file, load_from_file
from app_utils.queue_operations import SafeQueue
import pickle

class QueueManager:
    def __init__(self, queue: SafeQueue, queue_file_path: str):
        self.queue = queue
        self.queue_file_path = queue_file_path
        self.logger = logging.getLogger(__name__)

    def save_queue_periodically(self, shutdown_flag: threading.Event):
        while not shutdown_flag.is_set():
            self.save_queue()
            if shutdown_flag.wait(30):
                break

    def save_queue(self):
        try:
            with self.queue.mutex:
                queue_contents = list(self.queue.queue)
            save_to_file(queue_contents, self.queue_file_path)
            #self.logger.debug(f"Queue saved to {self.queue_file_path}")
        except Exception as e:
            self.logger.error(f"Error saving queue: {e}")

    def load_queue(self) -> None:
        try:
            items = load_from_file(self.queue_file_path)
            if not isinstance(items, list):
                raise TypeError("Loaded data is not a list")
            
            for item in items:
                self.queue.put(item)
            
            self.logger.info(f"Queue loaded from {self.queue_file_path}, {len(items)} items added")
        except FileNotFoundError:
            self.logger.warning(f"File {self.queue_file_path} not found. Starting with an empty queue.")
        except EOFError:
            self.logger.debug("Queue file is empty. Starting with an empty queue.")
        except (pickle.UnpicklingError, AttributeError, TypeError) as e:
            self.logger.error(f"Error unpickling queue data: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error loading queue: {e}")