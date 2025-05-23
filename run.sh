#!/bin/bash

# Check if .venv exists
if [ ! -d ".venv" ]; then
    echo "Virtual environment .venv not found."
    echo "Please run the following commands to create it:"
    echo "  uv venv"
    echo "  uv sync"
    exit 1
fi

# Activate virtual environment
source .venv/bin/activate

# Run the main application
python api_server.py

# Deactivate virtual environment (optional, runs when script exits)
# deactivate
