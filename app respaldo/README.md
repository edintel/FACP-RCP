# FACP serial reader to Thingsboard

A robust Python-based gateway service that connects Fire Alarm Control Panels (FACP) to ThingsBoard IoT platform via MQTT, enabling real-time monitoring and event tracking.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Technical Architecture](#technical-architecture)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [API Documentation](#api-documentation)
- [Testing](#testing)
- [Deployment](#deployment)
- [Performance Considerations](#performance-considerations)
- [Security](#security)
- [Known Limitations](#known-limitations)
- [Contributing](#contributing)
- [Troubleshooting](#troubleshooting)
- [License](#license)

## Overview

This gateway service establishes a bridge between Fire Alarm Control Panels and ThingsBoard IoT platform. It reads serial data from various FACP models, processes the events and alarms, and forwards them to ThingsBoard via MQTT. The system supports multiple FACP models including Edwards iO1000, Edwards EST3x, Notifier NFS, and Simplex panels.

### Key Benefits

- Real-time monitoring of fire alarm systems
- Centralized event management
- Support for multiple FACP models
- Reliable message queuing system
- Hardware relay monitoring
- Automatic updates

## Features

- **Multi-Panel Support**: Compatible with various FACP models
- **Event Processing**: Parses and categorizes events by severity levels
- **MQTT Integration**: Secure communication with ThingsBoard
- **Queue Management**: Persistent queue system for reliable message delivery
- **Relay Monitoring**: Hardware-level monitoring of alarm and trouble signals
- **Auto-Updates**: Automatic system updates from GitHub releases
- **Systemd Integration**: Runs as a system service
- **Logging**: Comprehensive logging with rotation

## Technical Architecture

### Core Components

1. **Serial Handler (`classes/serial_port_handler.py`)**

   - Base class for serial communication
   - Implements connection management and data processing
   - Model-specific implementations for different FACP types

2. **MQTT Handler (`classes/mqtt_sender.py`)**

   - Manages MQTT connection to ThingsBoard
   - Implements rate limiting and message queuing
   - Handles telemetry and attribute updates

3. **Queue Manager (`components/queue_manager.py`)**

   - Persistent message queue implementation
   - Periodic queue backup
   - Message recovery after system restart

4. **Relay Controller (`components/relay_controller.py`)**
   - GPIO-based relay control for Raspberry Pi
   - Configurable timing for relay states
   - Hardware-level monitoring

### Design Patterns

- **Factory Pattern**: Used in FACP handler creation
- **Observer Pattern**: For event monitoring and processing
- **Strategy Pattern**: In serial data parsing
- **Singleton Pattern**: For shared resources management

### Technology Stack

- Python 3.x
- PySerial for serial communication
- Paho-MQTT for MQTT protocol
- Pydantic for configuration validation
- RPi.GPIO for hardware interfacing
- YAML for configuration management

## Prerequisites

- Python 3.7 or higher
- Raspberry Pi (for hardware relay features)
- Serial port adapter
- Internet connection for ThingsBoard communication
- Required Python packages (see `requirements.txt`)

## Installation

1. Clone the repository:

```bash
git clone https://github.com/yourusername/Serial_to_Mqtt_Gateway_for_FACP.git
cd Serial_to_Mqtt_Gateway_for_FACP
```

2. Create and activate virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate  # Linux
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Configure the application:

```bash
cp config/config_example.yml config/config.yml
# Edit config.yml with your settings
```

5. Install as a service:

```bash
sudo cp serial-to-mqtt.service /etc/systemd/system/
sudo chmod 644 /etc/systemd/system/serial-to-mqtt.service
sudo systemctl daemon-reload
sudo systemctl enable serial-to-mqtt.service
```

## Configuration

### Main Configuration (`config.yml`)

```yaml
id_modelo_panel: 10001 # FACP model ID
thingsboard:
  device_token: YOUR_DEVICE_TOKEN
  host: YOUR_THINGSBOARD_HOST
  port: YOUR_THINGSBOARD_PORT
serial:
  puerto: /dev/serial-adapter
relay:
  pin: 8
  high_time: 1
  low_time: 60
relay_monitor:
  alarm_pin: 13
  trouble_pin: 27
  publish_interval: 15
  alarm_active_high: true
  trouble_active_high: false
```

### Event Severity Levels (`eventSeverityLevels.yml`)

Configure event severity mappings for each FACP model. Severity levels:

- 3: Severe
- 2: Warning
- 1: Notification

## Usage

### Starting the Service

```bash
# Start the service
sudo systemctl start serial-to-mqtt.service

# Check status
sudo systemctl status serial-to-mqtt.service

# View logs
journalctl -u serial-to-mqtt.service
```

### Development Mode

```bash
# Run directly with Python
python main.py
```

## API Documentation

### MQTT Topics

The gateway publishes to ThingsBoard using the following structure:

- **Telemetry**: `v1/devices/me/telemetry`

  - Event data
  - Relay states
  - System status

- **Attributes**: `v1/devices/me/attributes`
  - Configuration updates
  - Device status

### Message Format

```json
{
  "event": "ALARM_TYPE",
  "description": "Event description",
  "severity": 3,
  "SBC_date": "2025-02-23 20:29:47.685",
  "FACP_date": "2025-02-23 20:29:47"
}
```

### Virtual Serial Port Testing

```bash
# Create virtual serial port
sudo socat PTY,link=/tmp/virtual-serial,rawer,echo=0 PTY,echo=0 &

# Network-accessible virtual port
sudo socat PTY,link=/tmp/virtual-serial,rawer TCP-LISTEN:12345,reuseaddr
```

## Deployment

1. Compile the application:

```bash
pyinstaller main.py
```

2. Copy configuration files:

```bash
cp config/*.yml dist/main/
```

3. Deploy to target system:

```bash
# Copy compiled application
cp -r dist/main/* /path/to/deployment/

# Set up service
sudo cp serial-to-mqtt.service /etc/systemd/system/
sudo systemctl enable serial-to-mqtt.service
```

## Performance Considerations

- **Rate Limiting**: MQTT messages are rate-limited to:

  - 100 messages/second
  - 3000 messages/minute
  - 7000 messages/hour

- **Queue Management**:

  - Persistent queue for reliability
  - Periodic queue backups
  - Memory-efficient processing

- **Resource Usage**:
  - Lightweight thread management
  - Efficient serial buffer handling
  - Optimized GPIO operations

## Security

- Secure MQTT communication
- Device token authentication
- Rate limiting protection
- Error handling and logging
- Input validation
- Configuration validation

## Known Limitations

- Single FACP connection per instance
- Raspberry Pi dependency for relay features
- Specific FACP model support
- Rate limiting constraints

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit changes
4. Push to the branch
5. Create a Pull Request

## Troubleshooting

### Common Issues

1. **Serial Connection Failures**

   - Check physical connections
   - Verify port permissions
   - Confirm baud rate settings

2. **MQTT Connection Issues**

   - Verify ThingsBoard credentials
   - Check network connectivity
   - Review firewall settings

3. **Service Startup Failures**
   - Check service logs
   - Verify configuration files
   - Confirm file permissions

### Debug Mode

Enable debug logging in `logging_config.yml`:

```yaml
root:
  level: DEBUG
  handlers: [file_handler, console_handler]
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.
