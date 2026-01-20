# ShortcutHelper

A program for Ubuntu that shows a popup in the bottom-right corner of the screen whenever you press CTRL, Super, or ALT, listing available keyboard shortcuts and their descriptions.

<img width="645" height="327" alt="image" src="https://github.com/user-attachments/assets/9f078761-216f-4a98-b525-c3a3ed885da8" />


## Features

- Detects when CTRL, Super, or ALT keys are pressed
- Shows an elegant popup in the bottom-right corner
- Lists all available shortcuts with the pressed modifiers
- Displays descriptions of what each shortcut does
- **Automatically imports shortcuts from GNOME system**
- Customizable through configuration file
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

After installation, run the program with:

```bash
./run.sh
```

Or manually:

```bash
source venv/bin/activate
python shortcut_helper.py
```

The program will run in the background and show the popup whenever you press CTRL, Super, or ALT.

## Configuration

Edit the `config.json` file to customize the shortcuts and descriptions displayed.

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

- `shortcut_helper.py` - Main program
- `config.json` - Shortcut configuration
- `requirements.txt` - Python dependencies
- `setup.sh` - Automatic installation script
- `run.sh` - Script to run the program
- `README.md` - This file
- `SETUP.md` - Detailed installation instructions
- `CUSTOMIZATION.md` - Customization guide
