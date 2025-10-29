#!/bin/bash

VENV_PATH="/home/edintel/Desktop/app/.venv"
PYTHON_SCRIPT="/home/edintel/Desktop/app/main.py"
PROJECT_PATH="/home/edintel/Desktop/app"

"$VENV_PATH/bin/pip" install -r "$PROJECT_PATH/requirements.txt"
"$VENV_PATH/bin/python3" "$PYTHON_SCRIPT"
