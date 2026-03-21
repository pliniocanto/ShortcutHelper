# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ShortcutHelper is a GTK3 Python application that monitors keyboard modifier keys (Ctrl, Super, Alt, Shift) and displays a context-aware popup of matching keyboard shortcuts. It integrates with GNOME's GSettings to auto-import system shortcuts.

## Running the Application

```bash
# One-time setup (installs system deps, creates venv)
./setup.sh

# Run the application
./run.sh

# Or directly with options
source venv/bin/activate
python shortcut_helper.py [--import-only] [--no-import-system]
```

**`--import-only`**: Imports system shortcuts into config.json and exits.
**`--no-import-system`**: Skips auto-importing GNOME shortcuts on startup.

## Service Management

```bash
./install-service.sh                                          # Install systemd user service
./uninstall-service.sh                                        # Remove service
systemctl --user status shortcut-helper.service
journalctl --user -u shortcut-helper.service -f              # Live logs
```

## Architecture

Single file: `shortcut_helper.py` (~1000 lines), three main classes:

**`KeymapPopup`** — GTK window (bottom-right, always-on-top, dark theme). Renders shortcut lists filtered by currently-held modifiers. Separates user-configured from imported shortcuts visually. Handles modifier-combo matching in `update_filter()`.

**`SystemKeymapImporter`** — Reads GNOME keybindings from GSettings (`org.gnome.desktop.wm.keybindings`, `org.gnome.settings-daemon.plugins.media-keys`, `org.gnome.shell.keybindings`). Converts GNOME format (`<Control><Shift>c`) to config format (`Ctrl+Shift+C`). Controlled by `import_sources` in config.json.

**`KeymapHelper`** — Main controller. Runs a `pynput` keyboard listener in a background thread; uses `GLib.idle_add` to safely dispatch UI updates to the GTK main thread. Tracks modifier state and calls `show_popup()` / `hide_popup()` / `update_filter()` on `KeymapPopup`.

**Threading model**: pynput listener thread → `GLib.idle_add` → GTK main thread. Never call GTK methods directly from the pynput callbacks.

**Key detection quirks**: Uses pynput `Key` objects as primary detection; falls back to virtual key codes (vk) for X11 compatibility. vk 133/134 = Super, 64/65511 = Alt_L/R, 108 requires special disambiguation (Alt_R vs 'l').

## Configuration (config.json)

Four sections:
- `configured_shortcuts` — user-defined shortcuts (higher display priority)
- `imported_shortcuts` — auto-populated from GNOME (populated by `--import-only` or startup)
- `popup_settings` — `position`, `timeout` (ms), `font_size`
- `import_sources` — booleans: `window_manager`, `media_keys`, `shell`
- `key_aliases` — maps one key combo to another's description

## Dependencies

- **Runtime**: `pynput` (pip), PyGObject/GTK3 (system packages — must use `--system-site-packages` venv)
- **System packages**: `python3-gi`, `python3-gi-cairo`, `gir1.2-gtk-3.0`
- No test suite exists in this project.
