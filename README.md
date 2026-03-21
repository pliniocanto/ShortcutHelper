# ShortcutHelper

A program for Ubuntu that shows a popup near a screen corner whenever you press CTRL, Super, or ALT, listing available keyboard shortcuts and their descriptions.

## ShortcutHelper
<img width="627" height="322" alt="image" src="https://github.com/user-attachments/assets/d3f64aa5-232a-4750-af02-1eca78c398b1" />

## ShortcutHelper Settings
<img width="771" height="655" alt="image" src="https://github.com/user-attachments/assets/1428e097-3983-4c44-8eaf-6fba8f3a7190" />



## Features

- Detects when CTRL, Super, or ALT keys are pressed
- Shows an elegant popup in the bottom-right corner (or another corner—see settings)
- Lists all available shortcuts with the pressed modifiers
- Displays descriptions of what each shortcut does
- **Automatically imports shortcuts from GNOME system**
- Customizable through the configuration file or the built-in **settings dialog**
- **Configurable popup transparency** via `popup_settings.opacity` (semi-transparent background so you can see through the overlay)
- **System tray icon** (keyboard) stays resident while the app runs: open the shortcut list on demand, edit settings, or quit
- Dynamic filtering based on pressed modifier keys (CTRL, Super, ALT, SHIFT)

## Requirements

- Ubuntu 24.04 (or similar)
- Python 3.8+
- Python libraries (see requirements.txt)

## Quick Installation

```bash
./setup.sh
```

This will create a virtual environment and install all dependencies automatically.

For more details, see the `SETUP.md` file.

## Usage

### Running Manually

After installation, run the program with:

```bash
./run.sh
```

Or manually:

```bash
source venv/bin/activate
python shortcut_helper.py
```

The program runs in the background and shows the popup whenever you press CTRL, Super, or ALT.

A **system tray** icon (keyboard) appears while ShortcutHelper is running. Use it to:

- **Show Shortcuts** — open the popup without holding a modifier
- **Edit Config** — open the graphical **ShortcutHelper Settings** window (custom shortcuts, popup options, key aliases, imported shortcuts, and which GNOME sources to import)
- **Quit** — exit the app

On GNOME, the app uses **AppIndicator** when available; otherwise it falls back to GTK’s legacy status icon.

### Running as a System Service (Auto-start on Login)

To install ShortcutHelper as a systemd user service that starts automatically when you log in:

```bash
./install-service.sh
```

This will:
- Create a systemd service file
- Install it to `~/.config/systemd/user/`
- Enable it to start automatically on login
- Start the service immediately

**Useful service commands:**
```bash
# Check service status
systemctl --user status shortcut-helper.service

# View logs
journalctl --user -u shortcut-helper.service -f

# Restart the service
systemctl --user restart shortcut-helper.service

# Stop the service
systemctl --user stop shortcut-helper.service

# Start the service
systemctl --user start shortcut-helper.service
```

**To uninstall the service:**
```bash
./uninstall-service.sh
```

## Configuration

Edit `config.json` directly, or use **Edit Config** from the tray to change most options in a tabbed dialog. The **Popup** settings tab includes **opacity** (about 10%–100%): lower values make the shortcut overlay more transparent.

Relevant keys in `config.json` under `popup_settings`:

| Key        | Meaning |
| ---------- | ------- |
| `timeout`  | How long the popup stays visible (milliseconds) |
| `font_size`| Text size |
| `position` | `bottom-right`, `bottom-left`, `top-right`, or `top-left` |
| `opacity`  | Opacity of the popup’s rounded background (`0.1`–`1.0`) |

### Import System Shortcuts

The program automatically imports shortcuts from the GNOME system on startup. To manually import and save to the configuration file:

```bash
python shortcut_helper.py --import-only
```

To disable automatic import:

```bash
python shortcut_helper.py --no-import-system
```

## Project Structure

- `shortcut_helper.py` - Entry point
- `helper.py` - Keyboard listener, tray, and lifecycle
- `popup.py` - Shortcut popup window (including opacity)
- `config_editor.py` - GTK settings dialog
- `importer.py` - GNOME shortcut import
- `config.json` - Shortcut configuration
- `requirements.txt` - Python dependencies
- `setup.sh` - Automatic installation script
- `run.sh` - Script to run the program
- `install-service.sh` - Install as systemd service (auto-start)
- `uninstall-service.sh` - Uninstall systemd service
- `README.md` - This file
- `SETUP.md` - Detailed installation instructions
- `CUSTOMIZATION.md` - Customization guide
