#!/bin/bash
# Script to run ShortcutHelper

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found!"
    echo "Run first: ./setup.sh"
    exit 1
fi

# Activate virtual environment and run (pass through e.g. --help, --import-only)
source venv/bin/activate
python shortcut_helper.py "$@"
