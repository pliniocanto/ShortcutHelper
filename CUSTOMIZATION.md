# Customization

## Import System Shortcuts

The program can automatically import keyboard shortcuts configured in the GNOME system. This includes:

- Window manager shortcuts (move windows, workspaces, etc.)
- Media and system shortcuts
- GNOME shell shortcuts

**Automatic import**: By default, the program imports system shortcuts on startup and merges them with shortcuts from the configuration file. Manually defined shortcuts in the file have priority.

**Manual import**: To import and save system shortcuts to the configuration file:

```bash
python shortcut_helper.py --import-only
```

**Disable import**: To use only shortcuts from the configuration file:

```bash
python shortcut_helper.py --no-import-system
```

## Add/Modify Shortcuts

Edit the `config.json` file to customize the displayed shortcuts.

### Example structure:

```json
{
  "configured_shortcuts": {
    "Ctrl+c": "Copy",
    "Super+1": "Open Files",
    "Alt+Tab": "Switch between windows"
  }
}
```

### Special keys:

For special keys, use the following names:
- `Tab` - Tab
- `Shift+Tab` - Shift+Tab
- `Home` - Home
- `End` - End
- `PageUp` - Page Up
- `PageDown` - Page Down
- `Left`, `Right`, `Up`, `Down` - Directional arrows
- `=` - Equals sign
- `-` - Hyphen
- `0-9` - Numbers

## Configure the Popup

In the `config.json` file, you can adjust popup settings:

```json
{
  "popup_settings": {
    "position": "bottom-right",  // Position (currently only bottom-right)
    "timeout": 10000,             // Time in ms before hiding (10000 = 10 seconds)
    "opacity": 0.55,              // Opacity (0.0 to 1.0)
    "font_size": 12               // Font size
  }
}
```

## Key Aliases

You can map custom key combinations to existing shortcut descriptions. For example, if `Ctrl+Shift+Delete` sends `Ctrl+Insert`:

```json
{
  "key_aliases": {
    "Shift+Delete": "Insert"
  }
}
```

## Import Sources

Control which system shortcut sources are imported:

```json
{
  "import_sources": {
    "window_manager": false,  // Window manager shortcuts
    "media_keys": false,      // Media key shortcuts
    "shell": false            // GNOME shell shortcuts
  }
}
```

## Tips

- The popup appears automatically when you press CTRL, Super, or ALT
- It stays open while modifier keys are pressed
- The popup is positioned in the bottom-right corner with a 20px margin
- User-configured shortcuts are displayed first, followed by imported shortcuts
