#!/bin/bash

# ArpadBot Azure Startup Script
# This script ensures the bot starts correctly on Azure

set -e

echo "Starting ArpadBot..."
echo "Python version:"
python3 --version

echo "Installing dependencies..."
pip install -r requirements.txt

echo "Starting bot on port 8000..."
python3 bot.py
