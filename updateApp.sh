#!/bin/bash

# Set the path to your virtual environment
VENV_PATH="/home/edintel/Desktop/app/.venv"

# Set the path of the project
PROJECT_PATH="/home/edintel/Desktop/app"

# Change directory to the project path
cd "$PROJECT_PATH"

# Get the latest release information from the GitHub repository
latest_release=$(curl -s https://api.github.com/repos/Andres10976/Serial_to_Mqtt_Gateway_for_FACP/releases/latest)

# Extract the tag name of the latest release
latest_tag=$(echo "$latest_release" | grep '"tag_name":' | sed -E 's/.*"([^"]+)".*/\1/')

# Remove the "v" prefix from the tag name
folder_name=$(echo "$latest_tag" | sed 's/^v//')

# Check if the latest release is already downloaded
if [ ! -f "$latest_tag.zip" ]; then
  # Remove the previous .zip file if it exists
  rm -f *.zip
  
  # Download the source code ZIP file of the latest release
  wget "https://github.com/Andres10976/Serial_to_Mqtt_Gateway_for_FACP/archive/$latest_tag.zip" -O "$latest_tag.zip"
  
  # Unzip the source code
  unzip "$latest_tag.zip"
  
  # Synchronize the files from the unzipped folder to the existing directories
  rsync -av "Serial_to_Mqtt_Gateway_for_FACP-$folder_name/app/" app/
  rsync -av "Serial_to_Mqtt_Gateway_for_FACP-$folder_name/classes/" classes/
  rsync -av "Serial_to_Mqtt_Gateway_for_FACP-$folder_name/components/" components/
  rsync -av "Serial_to_Mqtt_Gateway_for_FACP-$folder_name/config/" config/
  rsync -av "Serial_to_Mqtt_Gateway_for_FACP-$folder_name/utils/" utils/
  rsync -av "Serial_to_Mqtt_Gateway_for_FACP-$folder_name/." .
  
  # Remove the unzipped folder
  rm -rf "Serial_to_Mqtt_Gateway_for_FACP-$folder_name"

  # Add permissions to this user
  sudo chown -R edintel:edintel ./
  sudo chmod -R 755 ./
  
  # Activate the virtual environment
  source "$VENV_PATH/bin/activate"

  # Update packages if something new appeared
  pip install -r requirements.txt
  
  # Deactivate the virtual environment
  deactivate
fi

# Restart the serial_to_mqtt service
sudo systemctl restart serial-to-mqtt.service