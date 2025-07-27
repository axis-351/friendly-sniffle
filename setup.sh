#!/bin/bash
set -e

# Install system packages
if command -v apt-get >/dev/null 2>&1; then
    sudo apt-get update
    sudo apt-get install -y python3 python3-pip ffmpeg
fi

# Install Python dependencies
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt

echo "Setup complete"
