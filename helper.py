"""
KeymapHelper — main controller.

Runs a pynput keyboard listener in a background thread and dispatches
UI updates to the GTK main thread via GLib.idle_add.
"""

import json
import sys

from pynput import keyboard

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib

try:
    gi.require_version('AppIndicator3', '0.1')
    from gi.repository import AppIndicator3
    HAS_APP_INDICATOR = True
except (ValueError, ImportError):
    HAS_APP_INDICATOR = False

from popup import KeymapPopup
from importer import SystemKeymapImporter
from config_editor import open_config_editor


class KeymapHelper:
    def __init__(self, config_path, import_system=None):
        self.config_path = config_path
        self.config = self._load_config()

        if import_system is None:
            import_system = any(self.config.get('import_sources', {}).values())

        if import_system:
            self._import_system_shortcuts()

        self.popup     = None
        self.listener  = None
        self.tray_icon = None
        self.indicator = None

        self.ctrl_pressed  = False
        self.shift_pressed = False
        self.alt_pressed   = False
        self.super_pressed = False

    # ── Config ───────────────────────────────────────────────────────────

    def _load_config(self):
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Configuration file not found: {self.config_path}")
            sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"Error reading configuration: {e}")
            sys.exit(1)

    def save_config(self):
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"⚠️  Warning: Could not save configuration: {e}")

    def _import_system_shortcuts(self):
        try:
            import_sources = self.config.get('import_sources', {})
            hidden = set(self.config.get('hidden_imported_shortcuts', []))
            system, sources = SystemKeymapImporter.get_system_shortcuts(import_sources)
            # Remove shortcuts the user has explicitly hidden
            filtered = {k: v for k, v in system.items() if k not in hidden}
            filtered_sources = {k: v for k, v in sources.items() if k not in hidden}
            old = self.config.get('imported_shortcuts', {})
            self.config['imported_shortcuts'] = filtered
            self.config['imported_shortcuts_sources'] = filtered_sources
            new_count = len([k for k in filtered if k not in old])
            if new_count > 0 or len(filtered) != len(old):
                self.save_config()
                if new_count > 0:
                    print(f"📥 Imported {new_count} new shortcuts from GNOME system")
                else:
                    print(f"📥 Updated {len(filtered)} shortcuts from GNOME system")
        except Exception as e:
            print(f"⚠️  Warning: Could not import system shortcuts: {e}")

    def _get_all_shortcuts(self):
        """Merges imported + configured; configured takes priority."""
        imported   = self.config.get('imported_shortcuts', {})
        configured = self.config.get('configured_shortcuts',
                                     self.config.get('shortcuts', {}))
        return {**imported, **configured}

    # ── Popup ────────────────────────────────────────────────────────────

    def _make_popup(self):
        return KeymapPopup(
            shortcuts            = self._get_all_shortcuts(),
            settings             = self.config.get('popup_settings', {}),
            key_aliases          = self.config.get('key_aliases', {}),
            configured_shortcuts = self.config.get('configured_shortcuts',
                                                   self.config.get('shortcuts', {})),
            imported_shortcuts   = self.config.get('imported_shortcuts', {}),
            imported_sources     = self.config.get('imported_shortcuts_sources', {}),
        )

    def _pressed_keys(self):
        return {
            'ctrl':  self.ctrl_pressed,
            'super': self.super_pressed,
            'alt':   self.alt_pressed,
            'shift': self.shift_pressed,
        }

    def show_popup(self):
        if not self.popup:
            self.popup = self._make_popup()
        self.popup.show(use_timeout=False, pressed_keys=self._pressed_keys())
        return False

    def hide_popup(self):
        if self.popup:
            self.popup.hide()
        return False

    def update_filter(self):
        if self.popup:
            self.popup.filter_shortcuts(
                self._pressed_keys(),
                self.config.get('key_aliases', {}),
            )
        return False

    # ── Config editor ────────────────────────────────────────────────────

    def open_config_editor(self):
        def on_save():
            self.save_config()
            self.popup = None  # force popup reload with new shortcuts

        open_config_editor(self.config, on_save)
        return False

    # ── System tray ──────────────────────────────────────────────────────

    def setup_tray(self):
        menu = Gtk.Menu()

        show_item = Gtk.MenuItem(label="Show Shortcuts")
        show_item.connect("activate", lambda _: GLib.idle_add(self.show_popup))
        menu.append(show_item)

        edit_item = Gtk.MenuItem(label="Edit Config")
        edit_item.connect("activate", lambda _: GLib.idle_add(self.open_config_editor))
        menu.append(edit_item)

        menu.append(Gtk.SeparatorMenuItem())

        quit_item = Gtk.MenuItem(label="Quit")
        quit_item.connect("activate", lambda _: self.stop())
        menu.append(quit_item)

        menu.show_all()

        if HAS_APP_INDICATOR:
            self.indicator = AppIndicator3.Indicator.new(
                "shortcut-helper",
                "input-keyboard",
                AppIndicator3.IndicatorCategory.APPLICATION_STATUS,
            )
            self.indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
            self.indicator.set_title("ShortcutHelper")
            self.indicator.set_menu(menu)
        else:
            self.tray_icon = Gtk.StatusIcon()
            self.tray_icon.set_from_icon_name("input-keyboard")
            self.tray_icon.set_tooltip_text("ShortcutHelper")
            self.tray_icon.connect("popup-menu", self._on_tray_popup, menu)
            self.tray_icon.set_visible(True)

    def _on_tray_popup(self, icon, button, time, menu):
        menu.popup(None, None, Gtk.StatusIcon.position_menu, icon, button, time)

    # ── Keyboard listener ────────────────────────────────────────────────

    def on_press(self, key):
        try:
            if key in (keyboard.Key.ctrl_l, keyboard.Key.ctrl_r):
                if not self.ctrl_pressed:
                    self.ctrl_pressed = True
                    GLib.idle_add(self.show_popup)
            elif hasattr(keyboard.Key, 'cmd') and key in (keyboard.Key.cmd, keyboard.Key.cmd_r):
                if not self.super_pressed:
                    self.super_pressed = True
                    GLib.idle_add(self.show_popup)
            elif key in (keyboard.Key.shift_l, keyboard.Key.shift_r):
                if not self.shift_pressed:
                    self.shift_pressed = True
                    if self.ctrl_pressed or self.super_pressed or self.alt_pressed:
                        if self.popup:
                            GLib.idle_add(self.update_filter, priority=GLib.PRIORITY_HIGH)
                        else:
                            GLib.idle_add(self.show_popup)
            elif key in (keyboard.Key.alt_l, keyboard.Key.alt_r):
                if not self.alt_pressed:
                    self.alt_pressed = True
                    GLib.idle_add(self.show_popup)
        except AttributeError:
            pass

        # vk-code fallback for Linux/X11
        try:
            if hasattr(key, 'vk'):
                vk = key.vk
                if vk in (133, 134):  # Super_L / Super_R
                    if not self.super_pressed:
                        self.super_pressed = True
                        GLib.idle_add(self.show_popup)
                elif vk in (64, 65511):  # Alt_L
                    if not self.alt_pressed:
                        self.alt_pressed = True
                        GLib.idle_add(self.show_popup)
                elif vk == 108:  # Could be Alt_R or 'l' — disambiguate
                    if key == keyboard.Key.alt_r and not self.alt_pressed:
                        self.alt_pressed = True
                        GLib.idle_add(self.show_popup)
        except Exception:
            pass

    def on_release(self, key):
        try:
            if key in (keyboard.Key.ctrl_l, keyboard.Key.ctrl_r):
                self.ctrl_pressed = False
            elif hasattr(keyboard.Key, 'cmd') and key in (keyboard.Key.cmd, keyboard.Key.cmd_r):
                self.super_pressed = False
            elif key in (keyboard.Key.shift_l, keyboard.Key.shift_r):
                self.shift_pressed = False
            elif key in (keyboard.Key.alt_l, keyboard.Key.alt_r):
                self.alt_pressed = False
        except AttributeError:
            pass

        # vk-code fallback
        try:
            if hasattr(key, 'vk'):
                vk = key.vk
                if vk in (133, 134) and self.super_pressed:
                    self.super_pressed = False
                elif vk in (64, 108, 65511) and self.alt_pressed:
                    self.alt_pressed = False
        except Exception:
            pass

        has_modifier = (self.ctrl_pressed or self.super_pressed
                        or self.alt_pressed or self.shift_pressed)
        if has_modifier and self.popup:
            GLib.idle_add(self.update_filter)
        elif not has_modifier:
            GLib.idle_add(self.hide_popup)

    # ── Lifecycle ────────────────────────────────────────────────────────

    def start(self):
        self.popup = self._make_popup()

        self.listener = keyboard.Listener(
            on_press=self.on_press,
            on_release=self.on_release,
        )
        self.listener.start()
        self.setup_tray()

        print("ShortcutHelper started!")
        print("Press CTRL, Super (Windows) or ALT to see shortcuts.")
        print("Press Ctrl+C to exit.")

        try:
            Gtk.main()
        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        if self.listener:
            self.listener.stop()
        Gtk.main_quit()
        print("\nShortcutHelper stopped.")
