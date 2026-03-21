"""
SystemKeymapImporter — reads keyboard shortcuts from GNOME GSettings
and converts them to ShortcutHelper's config format.
"""

import re
import warnings

import gi
gi.require_version('Gio', '2.0')
from gi.repository import Gio


# Maps GNOME key names to display names used in config.json
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

# Bindings GNOME uses to mark a shortcut as disabled
DISABLED_BINDINGS = {'', 'disabled', '[]'}

GSETTINGS_SOURCES = {
    'window_manager': 'org.gnome.desktop.wm.keybindings',
    'media_keys':     'org.gnome.settings-daemon.plugins.media-keys',
    'shell':          'org.gnome.shell.keybindings',
}

# Custom keybindings are stored as a list of paths under this schema,
# each pointing to an instance of CUSTOM_KB_ITEM_SCHEMA.
CUSTOM_KB_LIST_SCHEMA = 'org.gnome.settings-daemon.plugins.media-keys'
CUSTOM_KB_ITEM_SCHEMA = 'org.gnome.settings-daemon.plugins.media-keys.custom-keybinding'


class SystemKeymapImporter:
    """Imports keyboard shortcuts from GNOME GSettings."""

    @staticmethod
    def get_system_shortcuts(import_sources=None):
        """Returns (shortcuts, sources) where both are {key_combo: ...} dicts.

        shortcuts: {key_combo: description}
        sources:   {key_combo: source_name}  e.g. 'window_manager', 'custom_keybindings'

        import_sources: {'window_manager': bool, 'media_keys': bool, 'shell': bool}
        Defaults to False for any missing key (opt-in, not opt-out).
        """
        if import_sources is None:
            import_sources = {}

        shortcuts = {}
        sources = {}
        for source_name, schema in GSETTINGS_SOURCES.items():
            if not import_sources.get(source_name, False):
                continue
            try:
                settings = Gio.Settings.new(schema)
                found = SystemKeymapImporter._read_settings(settings)
                shortcuts.update(found)
                sources.update({k: source_name for k in found})
            except Exception as e:
                print(f"⚠️  Warning: Could not read {source_name} shortcuts: {e}")

        if import_sources.get('custom_keybindings', False):
            found = SystemKeymapImporter._read_custom_keybindings()
            shortcuts.update(found)
            sources.update({k: 'custom_keybindings' for k in found})

        return shortcuts, sources

    @staticmethod
    def _read_settings(settings):
        """Reads all enabled keybindings from a GSettings object."""
        shortcuts = {}
        for key, raw_value in SystemKeymapImporter._iter_settings(settings):
            for binding in SystemKeymapImporter._extract_bindings(raw_value):
                if not SystemKeymapImporter._has_ctrl_or_super(binding):
                    continue
                parsed = SystemKeymapImporter.parse_keybinding(binding)
                if parsed:
                    desc = key.replace('_', ' ').replace('-', ' ').title()
                    shortcuts[parsed] = desc
        return shortcuts

    @staticmethod
    def _read_custom_keybindings():
        """Reads user-defined custom keybindings (e.g. Ctrl+Alt+T → Terminal).

        These are stored as a list of GSettings paths under the media-keys
        schema, each path containing a name, command, and binding key.
        """
        shortcuts = {}
        try:
            media = Gio.Settings.new(CUSTOM_KB_LIST_SCHEMA)
            paths = media.get_strv('custom-keybindings')
        except Exception as e:
            print(f"⚠️  Warning: Could not read custom keybinding list: {e}")
            return shortcuts

        for path in paths:
            try:
                kb = Gio.Settings.new_with_path(CUSTOM_KB_ITEM_SCHEMA, path)
                binding = kb.get_string('binding')
                name    = kb.get_string('name')
                if not binding or binding.strip() in DISABLED_BINDINGS:
                    continue
                if not SystemKeymapImporter._has_ctrl_or_super(binding):
                    continue
                parsed = SystemKeymapImporter.parse_keybinding(binding)
                if parsed and name:
                    shortcuts[parsed] = name
            except Exception:
                pass

        return shortcuts

    @staticmethod
    def _iter_settings(settings):
        """Yields (key, raw_value) pairs from a GSettings object.

        Uses get_value() per key (via list_keys()) so raw_value is always
        a GVariant — avoiding the ambiguity of get_all() which may return
        Python-native types depending on the GI version.
        """
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            try:
                keys = settings.list_keys()
            except Exception as e:
                print(f"⚠️  Warning: Could not list settings keys: {e}")
                return

        for key in keys:
            try:
                yield key, settings.get_value(key)
            except Exception:
                pass

    @staticmethod
    def _extract_bindings(gvariant):
        """Extracts binding strings from a GVariant (type 's' or 'as').

        Filters out disabled/empty entries before returning.
        """
        try:
            t = gvariant.get_type_string()
            if t == 's':
                bindings = [gvariant.get_string()]
            elif t == 'as':
                bindings = gvariant.get_strv() or []
            else:
                return []
        except Exception:
            return []

        return [b for b in bindings if b.strip() not in DISABLED_BINDINGS]

    @staticmethod
    def _has_ctrl_or_super(binding):
        """Returns True if the binding contains Ctrl or Super."""
        b = binding.lower()
        has_ctrl  = 'control' in b or 'ctrl' in b or 'primary' in b
        has_super = 'super' in b or 'mod4' in b or 'mod5' in b
        return has_ctrl or has_super

    @staticmethod
    def parse_keybinding(binding):
        """Converts a GNOME keybinding string to ShortcutHelper format.

        Examples:
            '<Super><Shift>Left'     -> 'Super+Shift+Left'
            '<Control><Shift>C'      -> 'Ctrl+Shift+C'
            '<Super><Control>Up'     -> 'Super+Ctrl+Up'
        """
        if not binding or binding.strip() in DISABLED_BINDINGS:
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

        # Everything after the <Tag> parts is the bare key
        remaining = re.sub(r'<[^>]+>', '', binding).replace('+', '').strip()
        if not remaining:
            return None

        # Skip XF86 hardware function keys — not useful to display
        if remaining.lower().startswith('xf86'):
            return None

        key_lower = remaining.lower()
        normalized = KEY_NAME_MAP.get(
            key_lower,
            remaining.upper() if len(remaining) == 1 else remaining.capitalize()
        )

        # Build ordered prefix: Super > Ctrl > other modifiers > key
        prefix = []
        if has_super:
            prefix.append('Super')
        if has_ctrl:
            prefix.append('Ctrl')

        return '+'.join(prefix + modifiers + [normalized])
