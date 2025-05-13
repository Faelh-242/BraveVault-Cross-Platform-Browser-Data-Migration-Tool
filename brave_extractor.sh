#!/bin/bash

echo "BraveVault - Brave Browser Data Migration Tool"
echo "-------------------------------"
echo

# Make the script executable
if [ ! -x "$0" ]; then
    chmod +x "$0"
fi

# Get the script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Create a virtual environment if it doesn't exist
if [ ! -d "$SCRIPT_DIR/venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$SCRIPT_DIR/venv"
    source "$SCRIPT_DIR/venv/bin/activate"
    echo "Installing dependencies..."
    pip install -r "$SCRIPT_DIR/requirements.txt"
else
    source "$SCRIPT_DIR/venv/bin/activate"
fi

echo
if [ "$1" = "gui" ]; then
    echo "Starting BraveVault GUI..."
    python "$SCRIPT_DIR/brave_extractor_gui.py"
else
    echo "Running BraveVault CLI..."
    echo
    python "$SCRIPT_DIR/brave_extractor.py" "$@"
fi

echo 