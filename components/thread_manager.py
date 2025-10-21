import logging
import time
import threading
from typing import List, Union, Callable, Dict

class ThreadManager:
    def __init__(self):
        self.threads: Dict[str, threading.Thread] = {}
        self.shutdown_flags: Dict[str, threading.Event] = {}
        self.logger: logging.Logger = logging.getLogger(__name__)

    def start_threads(self, thread_configs: List[Union[threading.Thread, Callable]]):
        for config in thread_configs:
            self.start_thread(config)

    def start_thread(self, thread_config: Union[threading.Thread, Callable]):
        if isinstance(thread_config, threading.Thread):
            thread = thread_config
            thread_name = thread.name
        else:
            thread_name = thread_config.__name__
            shutdown_flag = threading.Event()
            thread = threading.Thread(target=thread_config, args=(shutdown_flag,), name=thread_name)
            self.shutdown_flags[thread_name] = shutdown_flag

        if thread_name in self.threads:
            self.restart_thread(thread_name, thread)
        else:
            thread.daemon = True
            thread.start()
            self.threads[thread_name] = thread
            self.logger.info(f"Started thread: {thread_name}")

    def restart_thread(self, thread_name: str, new_thread: threading.Thread):
        self.stop_thread(thread_name)
        
        new_shutdown_flag = threading.Event()
        self.shutdown_flags[thread_name] = new_shutdown_flag
        new_thread = threading.Thread(target=new_thread._target, args=(new_shutdown_flag,), name=thread_name)
        
        new_thread.daemon = True
        new_thread.start()
        self.threads[thread_name] = new_thread
        self.logger.info(f"Restarted thread: {thread_name}")

    def stop_thread(self, thread_name: str):
        if thread_name in self.threads:
            thread = self.threads[thread_name]
            if thread.is_alive():
                self.logger.info(f"Stopping thread: {thread_name}")
                self.shutdown_flags[thread_name].set()
                thread.join(timeout=5)
                if thread.is_alive():
                    self.logger.warning(f"Thread {thread_name} did not stop gracefully.")
            del self.threads[thread_name]
            del self.shutdown_flags[thread_name]

    def stop_all_threads(self):
        for thread_name in list(self.threads.keys()):
            self.stop_thread(thread_name)

    def monitor_threads(self):
        while True:
            for thread_name, thread in list(self.threads.items()):
                if not thread.is_alive():
                    self.logger.error(f"Thread {thread_name} has died. Attempting to restart.")
                    self.restart_thread(thread_name, thread)
            time.sleep(5)