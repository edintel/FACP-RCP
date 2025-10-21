import os
from config.loader import load_and_validate_config, load_event_severity_levels
from logging_setup import setup_logging
from app.core import Application

def main():
    # Get the directory of the current script
    current_dir = os.path.dirname(os.path.abspath(__file__))

    # Setup logging
    config_path = os.path.join(current_dir, "config", "logging_config.yml")
    setup_logging(config_path)

    # Load configurations
    config = load_and_validate_config(os.path.join(current_dir, "config", "config.yml"))
    event_severity_levels = load_event_severity_levels(os.path.join(current_dir, "config", "eventSeverityLevels.yml"))

    # Initialize and run the application
    app = Application(config, event_severity_levels)
    app.start()

if __name__ == "__main__":
    main()