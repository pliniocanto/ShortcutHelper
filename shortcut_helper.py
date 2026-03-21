#!/usr/bin/env python3
"""
ShortcutHelper — shows keyboard shortcuts when modifier keys are pressed.

Usage:
    python shortcut_helper.py [--import-only] [--no-import-system]
"""

import json
import sys
from pathlib import Path

try:
    from pynput import keyboard  # noqa: F401  (validate dep at startup)
    import gi
    gi.require_version('Gtk', '3.0')
    gi.require_version('Gio', '2.0')
    from gi.repository import Gtk, Gio  # noqa: F401
except ImportError as e:
    print(f"Error importing dependencies: {e}")
    print("\n📋 Solution:")
    print("1. Run the setup script: ./setup.sh")
    print("   OR")
    print("2. Create a virtual environment and install dependencies:")
    print("   python3 -m venv venv && source venv/bin/activate")
    print("   pip install -r requirements.txt")
    print("\n3. Install system packages:")
    print("   sudo apt-get install python3-gi python3-gi-cairo gir1.2-gtk-3.0")
    sys.exit(1)

from helper import KeymapHelper
from importer import SystemKeymapImporter


CONFIG_PATH = Path(__file__).parent / 'config.json'


def _load_config(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error reading config: {e}")
        sys.exit(1)


def _save_config(path, config):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def cmd_import_only():
    """Imports system shortcuts into config.json and exits."""
    config = _load_config(CONFIG_PATH)
    import_sources = config.get('import_sources', {
        'window_manager': True, 'media_keys': True, 'shell': True,
    })
    shortcuts = SystemKeymapImporter.get_system_shortcuts(import_sources)
    config['imported_shortcuts'] = shortcuts
    _save_config(CONFIG_PATH, config)
    print(f"✅ Imported {len(shortcuts)} shortcuts to {CONFIG_PATH}")


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description='ShortcutHelper — shows keyboard shortcuts when modifier keys are pressed'
    )
    parser.add_argument('--import-only', action='store_true',
                        help='Import system shortcuts into config.json and exit')
    parser.add_argument('--no-import-system', action='store_true',
                        help='Skip auto-importing GNOME shortcuts on startup')
    args = parser.parse_args()

    if args.import_only:
        cmd_import_only()
        return

    import_system = not args.no_import_system
    KeymapHelper(CONFIG_PATH, import_system=import_system).start()


if __name__ == '__main__':
    main()
