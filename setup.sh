#!/bin/bash
# Setup script for ShortcutHelper

set -e

echo "🚀 Setting up ShortcutHelper..."

# Check if we're in the correct directory
if [ ! -f "shortcut_helper.py" ]; then
    echo "❌ Error: Run this script in the project directory"
    exit 1
fi

# Install system dependencies
echo "📦 Installing system dependencies..."
sudo apt-get update
sudo apt-get install -y python3-pip python3-gi python3-gi-cairo gir1.2-gtk-3.0 python3-venv

# Create virtual environment with access to system libraries
# This is necessary for the 'gi' (PyGObject) module to work
echo "🔧 Creating virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv --system-site-packages venv
    echo "✅ Virtual environment created (with access to system libraries)"
else
    echo "ℹ️  Virtual environment already exists"
    echo "⚠️  If you have problems, remove the 'venv' directory and run setup again"
fi

# Activate virtual environment and install dependencies
echo "📥 Installing Python dependencies..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "✅ Installation complete!"
echo ""
echo "To run the program, use:"
echo "  ./run.sh"
echo ""
echo "Or activate the virtual environment manually:"
echo "  source venv/bin/activate"
echo "  python shortcut_helper.py"
