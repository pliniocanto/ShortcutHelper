"""
SystemKeymapImporter — reads keyboard shortcuts from GNOME GSettings
and converts them to ShortcutHelper's config format.
"""

import re
import warnings

import gi
gi.require_version('Gio', '2.0')
from gi.repository import Gio


# Maps GNOME key names to the display names used in config.json
KEY_NAME_MAP = {
    'return':    'Enter',
    'space':     'Space',
    'backspace': 'Backspace',
    'delete':    'Delete',
    'escape':    'Esc',
    'tab':       'Tab',
    'home':      'Home',
    'end':       'End',
    'page_up':   'PageUp',
    'page_down': 'PageDown',
    'up':        'Up',
    'down':      'Down',
    'left':      'Left',
    'right':     'Right',
    **{f'f{n}': f'F{n}' for n in range(1, 13)},
}

GSETTINGS_SOURCES = {
    'window_manager': 'org.gnome.desktop.wm.keybindings',
    'media_keys':     'org.gnome.settings-daemon.plugins.media-keys',
    'shell':          'org.gnome.shell.keybindings',
}


class SystemKeymapImporter:
    """Imports keyboard shortcuts from GNOME GSettings."""

    @staticmethod
    def get_system_shortcuts(import_sources=None):
        """Returns a dict of {key_combo: description} from enabled GNOME sources.

        import_sources: {'window_manager': bool, 'media_keys': bool, 'shell': bool}
        """
        if import_sources is None:
            import_sources = {k: True for k in GSETTINGS_SOURCES}

        shortcuts = {}
        try:
            for source_name, schema in GSETTINGS_SOURCES.items():
                if not import_sources.get(source_name, True):
                    continue
                try:
                    settings = Gio.Settings.new(schema)
                    shortcuts.update(SystemKeymapImporter._read_settings(settings))
                except Exception:
                    pass
        except Exception as e:
            print(f"⚠️  Warning: Could not read all system shortcuts: {e}")

        return shortcuts

    @staticmethod
    def _read_settings(settings):
        """Reads all keybindings from a GSettings object."""
        shortcuts = {}
        try:
            entries = settings.get_all().items()
        except Exception:
            entries = SystemKeymapImporter._list_keys_fallback(settings)

        for key, value in entries:
            for binding in SystemKeymapImporter._binding_values(value):
                if not SystemKeymapImporter._has_ctrl_or_super(binding):
                    continue
                parsed = SystemKeymapImporter.parse_keybinding(binding)
                if parsed:
                    desc = key.replace('_', ' ').replace('-', ' ').title()
                    shortcuts[parsed] = desc

        return shortcuts

    @staticmethod
    def _list_keys_fallback(settings):
        """Falls back to list_keys() when get_all() is unavailable."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            keys = settings.list_keys()
        for key in keys:
            try:
                yield key, settings.get_value(key)
            except Exception:
                pass

    @staticmethod
    def _has_ctrl_or_super(binding):
        b = binding.lower()
        has_ctrl  = 'control' in b or 'ctrl' in b or 'primary' in b
        has_super = 'super' in b or 'mod4' in b or 'mod5' in b
        return has_ctrl or has_super

    @staticmethod
    def _binding_values(value):
        """Extracts string bindings from a GVariant (string or string array)."""
        try:
            if value is None:
                return []
            t = value.get_type_string()
            if t == 's':
                return [value.get_string()]
            if t == 'as':
                return value.get_strv() or []
        except Exception:
            pass
        return []

    @staticmethod
    def parse_keybinding(binding):
        """Converts a GNOME keybinding string to ShortcutHelper format.

        Examples:
            '<Super><Shift>Left'  -> 'Super+Shift+Left'
            '<Control><Alt>Tab'   -> 'Alt+Tab'   (Ctrl is the base, not shown)
        """
        if not binding or binding in ('', '[]'):
            return None

        modifiers = []
        has_ctrl  = False
        has_super = False

        for match in re.findall(r'<([^>]+)>', binding):
            m = match.lower()
            if m in ('control', 'ctrl', 'primary'):
                has_ctrl = True
            elif m in ('super', 'mod4', 'mod5'):
                has_super = True
            elif m == 'shift':
                modifiers.append('Shift')
            elif m == 'alt':
                modifiers.append('Alt')

        # Extract the bare key (everything after the <Tag> parts)
        remaining = re.sub(r'<[^>]+>', '', binding).replace('+', '').strip()
        if not remaining:
            return None

        key_lower = remaining.lower()
        normalized = KEY_NAME_MAP.get(key_lower,
                                      remaining.upper() if len(remaining) == 1
                                      else remaining.capitalize())

        key_with_mods = '+'.join(modifiers + [normalized])

        if has_super:
            return 'Super+' + key_with_mods
        return key_with_mods
