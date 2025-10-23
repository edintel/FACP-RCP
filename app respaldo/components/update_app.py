import os
import subprocess
from datetime import datetime, time, timedelta
import requests
import sys
import logging
import threading

logger = logging.getLogger(__name__)

def get_latest_release() -> str:
    url = 'https://api.github.com/repos/Andres10976/Serial_to_Mqtt_Gateway_for_FACP/releases/latest'
    try:
        response = requests.get(url)
        response.raise_for_status()
        latest_release = response.json()
        latest_tag = latest_release['tag_name']
        return latest_tag
    except requests.RequestException as e:
        logger.error(f"Failed to fetch latest release: {e}")
        return ""

def check_zip_file(latest_tag: str) -> None:
    zip_file = f"{latest_tag}.zip"
    if not os.path.exists(zip_file):
        if sys.platform.startswith('linux'):
            try:
                subprocess.run(['./updateApp.sh'], check=True)
            except subprocess.CalledProcessError as e:
                logger.error(f"Failed to run update script: {e}")
        else:
            logger.info("Updating app...")

def is_update_time() -> bool:
    current_time = datetime.now().time()
    start_time = time(0, 0)
    end_time = (datetime.combine(datetime.today(), start_time) + timedelta(hours=1)).time()
    return start_time <= current_time <= end_time

def update_check_thread(shutdown_flag: threading.Event) -> None:
    while not shutdown_flag.is_set():
        try:
            if is_update_time():
                latest_tag = get_latest_release()
                if latest_tag:
                    check_zip_file(latest_tag)
            if shutdown_flag.wait(60):
                break
        except Exception as e:
            logger.error(f"Error in update check thread: {e}")
            if shutdown_flag.wait(60):
                break