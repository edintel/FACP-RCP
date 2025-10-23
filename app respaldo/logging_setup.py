import logging
import logging.config
import yaml
import os

def setup_logging(config_path: str) -> None:
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        logging.config.dictConfig(config)
        print(f"Logging configuration loaded from {config_path}")
    else:
        logging.basicConfig(level=logging.DEBUG,
                            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                            handlers=[
                                logging.StreamHandler(),
                                logging.FileHandler("app.log")
                            ])
        print(f"Logging configuration file not found at {config_path}. Using basic configuration.")
    
    logging.getLogger().setLevel(logging.DEBUG)