#!/usr/bin/env python3
"""
ShortcutHelper - Shows keyboard shortcuts when modifier keys are pressed
"""

import json
import os
import sys
import threading
import time
from pathlib import Path

try:
    from pynput import keyboard
    import gi
    gi.require_version('Gtk', '3.0')
    gi.require_version('Gio', '2.0')
    from gi.repository import Gtk, Gdk, GLib, Gio
except ImportError as e:
    print(f"Error importing dependencies: {e}")
    print("\n📋 Solution:")
    print("1. Run the setup script: ./setup.sh")
    print("   OR")
    print("2. Create a virtual environment and install dependencies:")
    print("   python3 -m venv venv")
    print("   source venv/bin/activate")
    print("   pip install -r requirements.txt")
    print("\n3. Install system dependencies:")
    print("   sudo apt-get install python3-gi python3-gi-cairo gir1.2-gtk-3.0")
    sys.exit(1)


class KeymapPopup:
    def __init__(self, shortcuts, settings, key_aliases=None, configured_shortcuts=None, imported_shortcuts=None):
        self.shortcuts = shortcuts
        self.settings = settings
        self.key_aliases = key_aliases or {}
        self.configured_shortcuts = configured_shortcuts or {}  # User-configured shortcuts
        self.imported_shortcuts = imported_shortcuts or {}  # System-imported shortcuts
        self.window = None
        self.timeout_id = None
        self.ctrl_pressed = False
        self.filtered_shortcuts = shortcuts.copy()  # Filtered shortcuts
        self.scrolled = None
        self.shortcuts_box = None
        self.title_label = None
        self.current_modifiers = {'ctrl': False, 'super': False, 'alt': False, 'shift': False}
        
    def create_window(self):
        """Creates the popup window"""
        self.window = Gtk.Window(type=Gtk.WindowType.POPUP)
        self.window.set_decorated(False)
        self.window.set_resizable(False)
        self.window.set_skip_taskbar_hint(True)
        self.window.set_skip_pager_hint(True)
        self.window.set_keep_above(True)
        self.window.set_accept_focus(False)
        
        # Set minimum width (doubled)
        self.window.set_size_request(600, -1)  # Minimum width of 600px (doubled)
        
        # Configure opacity via CSS (set_opacity is deprecated)
        opacity = self.settings.get('opacity', 0.95)
        # Opacity will be applied via CSS below
        
        # Create main container
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        vbox.set_border_width(15)
        vbox.set_margin_start(10)
        vbox.set_margin_end(10)
        vbox.set_margin_top(10)
        vbox.set_margin_bottom(10)
        
        # Title (will be updated dynamically)
        self.title_label = Gtk.Label()
        self.title_label.set_markup("<b>Available Shortcuts</b>")
        self.title_label.set_margin_bottom(10)
        vbox.pack_start(self.title_label, False, False, 0)
        
        # Separator
        separator = Gtk.Separator()
        vbox.pack_start(separator, False, False, 5)
        
        # Lista de atalhos
        self.scrolled = Gtk.ScrolledWindow()
        self.scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.scrolled.set_min_content_height(300)
        self.scrolled.set_max_content_height(500)
        
        self.shortcuts_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        
        # Preencher com atalhos filtrados
        # List will be updated when filter is applied
        
        self.scrolled.add(self.shortcuts_box)
        vbox.pack_start(self.scrolled, True, True, 0)
        
        self.window.add(vbox)
        
        # Estilizar com CSS
        css_provider = Gtk.CssProvider()
        opacity = self.settings.get('opacity', 0.75)
        css = f"""
        window {{
            background-color: rgba(30, 30, 30, {opacity});
            border-radius: 10px;
        }}
        label {{
            color: rgba(255, 255, 255, {min(opacity + 0.1, 1.0)});
            font-size: 12px;
        }}
        """
        css_provider.load_from_data(css.encode())
        style_context = self.window.get_style_context()
        style_context.add_provider(css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        
        # Position in bottom-right corner
        self.position_window()
        
    def position_window(self):
        """Positions the window in the bottom-right corner"""
        if not self.window:
            return
            
        # Get screen dimensions
        display = Gdk.Display.get_default()
        monitor = display.get_primary_monitor()
        geometry = monitor.get_geometry()
        
        # Calculate window size
        self.window.show_all()
        width, height = self.window.get_size()
        
        # Position in bottom-right corner with margin
        margin = 20
        x = geometry.width - width - margin
        y = geometry.height - height - margin
        
        self.window.move(x, y)
        
    def show(self, use_timeout=True, pressed_keys=None):
        """Mostra o popup
        
        Args:
            use_timeout: Se True, oculta após timeout. Se False, mantém aberto.
            pressed_keys: dict com {'ctrl': bool, 'super': bool, 'alt': bool, 'shift': bool}
        """
        if not self.window:
            self.create_window()
        
        # Apply filter if keys were provided
        if pressed_keys is not None:
            # Use popup aliases (already passed in __init__)
            self.filter_shortcuts(pressed_keys, self.key_aliases)
        
        # Cancel previous timeout if exists
        if self.timeout_id:
            GLib.source_remove(self.timeout_id)
            self.timeout_id = None
        
        self.window.show_all()
        self.window.present()
        
        # Hide after timeout only if use_timeout is True
        if use_timeout:
            timeout_ms = self.settings.get('timeout', 3000)
            self.timeout_id = GLib.timeout_add(timeout_ms, self.hide)
        
    def hide(self):
        """Oculta o popup"""
        if self.window:
            self.window.hide()
        if self.timeout_id:
            GLib.source_remove(self.timeout_id)
            self.timeout_id = None
        return False  # Remove o timeout
    
    def update_title_from_keys(self, pressed_keys):
        """Updates the popup title based on pressed keys"""
        if not self.title_label:
            return
        
        # Build modifier string in order: Ctrl, Super, Alt, Shift
        modifiers_parts = []
        if pressed_keys.get('ctrl', False):
            modifiers_parts.append('CTRL')
        if pressed_keys.get('super', False):
            modifiers_parts.append('SUPER')
        if pressed_keys.get('alt', False):
            modifiers_parts.append('ALT')
        if pressed_keys.get('shift', False):
            modifiers_parts.append('SHIFT')
        
        if modifiers_parts:
            modifiers_text = ' + '.join(modifiers_parts)
            self.title_label.set_markup(f"<b>Available Shortcuts ({modifiers_text} + ...)</b>")
        else:
            self.title_label.set_markup(f"<b>Available Shortcuts</b>")
    
    def filter_shortcuts(self, pressed_keys, key_aliases=None):
        """Filtra atalhos baseado nas teclas pressionadas
        
        Args:
            pressed_keys: dict com {'ctrl': bool, 'super': bool, 'alt': bool, 'shift': bool}
            key_aliases: dict com mapeamentos de aliases (ex: {'Shift+Delete': 'Insert'})
        """
        filtered = {}
        key_aliases = key_aliases or {}
        
        # Build prefix string based on pressed keys
        # Order: Ctrl, Super, Alt, Shift (common display order)
        prefix_parts = []
        if pressed_keys.get('ctrl', False):
            prefix_parts.append('Ctrl')
        if pressed_keys.get('super', False):
            prefix_parts.append('Super')
        if pressed_keys.get('alt', False):
            prefix_parts.append('Alt')
        if pressed_keys.get('shift', False):
            prefix_parts.append('Shift')
        
        # If no keys are pressed, show nothing
        if not prefix_parts:
            self.filtered_shortcuts = {}
            self.update_title_from_keys(pressed_keys)
            self.update_shortcuts_list_from_keys(pressed_keys)
            return
        
        # Build search prefix (e.g., "Ctrl+Shift+Alt+")
        search_prefix = '+'.join(prefix_parts) + '+'
        search_prefix_lower = search_prefix.lower()
        
        # Store current modifiers for title
        self.current_modifiers = {
            'ctrl': pressed_keys.get('ctrl', False),
            'super': pressed_keys.get('super', False),
            'alt': pressed_keys.get('alt', False),
            'shift': pressed_keys.get('shift', False)
        }
        
        for key, description in self.shortcuts.items():
            key_lower = key.lower()
            
            # Check if shortcut starts with the prefix of pressed keys
            if key_lower.startswith(search_prefix_lower):
                filtered[key] = description
        
        # Add mapped aliases
        if key_aliases:
            for alias_key, mapped_key in key_aliases.items():
                alias_lower = alias_key.lower()
                # Check if alias matches the prefix of pressed keys
                if alias_lower.startswith(search_prefix_lower):
                    # If alias matches, get the mapped shortcut
                    if mapped_key in self.shortcuts:
                        # Create a description showing the alias and mapping
                        original_desc = self.shortcuts[mapped_key]
                        filtered[alias_key] = f"{original_desc} (via {mapped_key})"
        
        self.filtered_shortcuts = filtered
        self.update_title_from_keys(pressed_keys)
        self.update_shortcuts_list_from_keys(pressed_keys)
    
    def update_shortcuts_list_from_keys(self, pressed_keys):
        """Updates the shortcuts list in the popup based on pressed keys"""
        if not self.shortcuts_box:
            return
        
        # Clear existing list
        for child in self.shortcuts_box.get_children():
            self.shortcuts_box.remove(child)
        
        # Separate user and imported shortcuts
        user_items = []
        imported_items = []
        
        for key, description in self.filtered_shortcuts.items():
            item = (key, description)
            # Check if it's a configured shortcut (has priority)
            if key in self.configured_shortcuts:
                user_items.append(item)
            else:
                imported_items.append(item)
        
        # Sort each group
        user_items.sort(key=lambda x: x[0].lower())
        imported_items.sort(key=lambda x: x[0].lower())
        
        # Add user shortcuts first
        for key, description in user_items:
            hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=25)
            
            # Key - format based on full shortcut name
            key_label = Gtk.Label()
            key_lower = key.lower()
            
            # Extract all parts of the shortcut
            parts = key.split('+')
            modifiers_parts = []
            final_key = None
            
            # Process each part to identify modifiers and final key
            for part in parts:
                part_lower = part.lower()
                if part_lower in ['ctrl', 'control']:
                    modifiers_parts.append('CTRL')
                elif part_lower == 'super':
                    modifiers_parts.append('SUPER')
                elif part_lower == 'alt':
                    modifiers_parts.append('ALT')
                elif part_lower == 'shift':
                    modifiers_parts.append('SHIFT')
                else:
                    # This is the final key (not a modifier)
                    final_key = part
                    break
            
            # If final key not found, use the last part
            if final_key is None and parts:
                final_key = parts[-1]
            
            if modifiers_parts:
                modifiers_str = ' + '.join(modifiers_parts)
                key_markup = f"<b>{modifiers_str} + {final_key.upper() if final_key else ''}</b>"
            else:
                key_markup = f"<b>{final_key.upper() if final_key else key.upper()}</b>"
            
            key_label.set_markup(key_markup)
            key_label.set_width_chars(25)
            key_label.set_xalign(0)
            hbox.pack_start(key_label, False, False, 0)
            
            # Description
            desc_label = Gtk.Label(label=description)
            desc_label.set_xalign(0)
            desc_label.set_ellipsize(3)
            hbox.pack_start(desc_label, True, True, 0)
            
            self.shortcuts_box.pack_start(hbox, False, False, 0)
        
        # Add separator if there are imported shortcuts
        if imported_items and user_items:
            separator = Gtk.Separator()
            separator.set_margin_top(10)
            separator.set_margin_bottom(10)
            self.shortcuts_box.pack_start(separator, False, False, 0)
        
        # Add imported shortcuts after
        for key, description in imported_items:
            hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=25)
            
            # Key - format based on full shortcut name
            key_label = Gtk.Label()
            key_lower = key.lower()
            
            # Extract all parts of the shortcut
            parts = key.split('+')
            modifiers_parts = []
            final_key = None
            
            # Process each part to identify modifiers and final key
            for part in parts:
                part_lower = part.lower()
                if part_lower in ['ctrl', 'control']:
                    modifiers_parts.append('CTRL')
                elif part_lower == 'super':
                    modifiers_parts.append('SUPER')
                elif part_lower == 'alt':
                    modifiers_parts.append('ALT')
                elif part_lower == 'shift':
                    modifiers_parts.append('SHIFT')
                else:
                    # This is the final key (not a modifier)
                    final_key = part
                    break
            
            # If final key not found, use the last part
            if final_key is None and parts:
                final_key = parts[-1]
            
            if modifiers_parts:
                modifiers_str = ' + '.join(modifiers_parts)
                key_markup = f"<b>{modifiers_str} + {final_key.upper() if final_key else ''}</b>"
            else:
                key_markup = f"<b>{final_key.upper() if final_key else key.upper()}</b>"
            
            key_label.set_markup(key_markup)
            key_label.set_width_chars(25)
            key_label.set_xalign(0)
            hbox.pack_start(key_label, False, False, 0)
            
            # Description
            desc_label = Gtk.Label(label=description)
            desc_label.set_xalign(0)
            desc_label.set_ellipsize(3)
            hbox.pack_start(desc_label, True, True, 0)
            
            self.shortcuts_box.pack_start(hbox, False, False, 0)
        
        # Update display
        self.shortcuts_box.show_all()


class SystemKeymapImporter:
    """Importa atalhos de teclado do sistema GNOME"""
    
    @staticmethod
    def parse_keybinding(binding):
        """Converte um atalho do GNOME para formato simplificado
        
        Exemplo: 
        '<Control>c' -> 'c'
        '<Control><Shift>c' -> 'Shift+c'
        '<Control><Shift><Alt>Left' -> 'Shift+Alt+Left'
        """
        if not binding or binding == '' or binding == '[]':
            return None
        
        # Extract modifiers and key
        modifiers = []
        key = None
        has_control = False
        has_super = False
        
        # Process <Modifier> tags
        import re
        pattern = r'<([^>]+)>'
        matches = re.findall(pattern, binding)
        
        for match in matches:
            match_lower = match.lower()
            if match_lower in ['control', 'ctrl', 'primary']:
                # Mark that it has Control, but don't add to modifiers
                has_control = True
                continue
            elif match_lower in ['super', 'mod4', 'mod5']:
                # Mark that it has Super
                has_super = True
                continue
            elif match_lower == 'shift':
                modifiers.append('Shift')
            elif match_lower == 'alt':
                modifiers.append('Alt')
            else:
                # Provavelmente é a tecla principal
                key = match
        
        # Se não encontrou a tecla nos matches, tentar extrair do que sobrou
        if not key:
            # Remover todas as tags
            remaining = re.sub(r'<[^>]+>', '', binding)
            remaining = remaining.strip()
            if remaining:
                # Pode ter um + no final
                remaining = remaining.replace('+', '').strip()
                if remaining:
                    key = remaining
        
        if not key:
            return None
        
        # Normalizar nome da tecla
        key_lower = key.lower()
        key_map = {
            'return': 'Enter',
            'space': 'Space',
            'backspace': 'Backspace',
            'delete': 'Delete',
            'escape': 'Esc',
            'tab': 'Tab',
            'home': 'Home',
            'end': 'End',
            'page_up': 'PageUp',
            'page_down': 'PageDown',
            'up': 'Up',
            'down': 'Down',
            'left': 'Left',
            'right': 'Right',
            'f1': 'F1', 'f2': 'F2', 'f3': 'F3', 'f4': 'F4',
            'f5': 'F5', 'f6': 'F6', 'f7': 'F7', 'f8': 'F8',
            'f9': 'F9', 'f10': 'F10', 'f11': 'F11', 'f12': 'F12',
        }
        
        normalized_key = key_map.get(key_lower, key.upper() if len(key) == 1 else key.capitalize())
        
        # Build final key with modifiers and base modifier prefix
        base_prefix = ''
        if has_super:
            base_prefix = 'Super+'
        elif has_control:
            # For CTRL, we don't add prefix (compatibility - assumes CTRL by default)
            base_prefix = ''
        
        # Build final key
        if modifiers:
            key_with_modifiers = '+'.join(modifiers) + '+' + normalized_key
        else:
            key_with_modifiers = normalized_key
        
        # Add base modifier prefix if it's SUPER
        if base_prefix:
            return base_prefix + key_with_modifiers
        else:
            return key_with_modifiers
    
    @staticmethod
    def get_binding_values(value):
        """Obtém os valores de um keybinding, lidando com strings e arrays
        
        Retorna uma lista de bindings (pode ter múltiplos atalhos para a mesma ação)
        """
        try:
            if value is None:
                return []
            type_str = value.get_type_string()
            if type_str == 's':  # String
                return [value.get_string()]
            elif type_str == 'as':  # Array de strings
                arr = value.get_strv()
                return arr if arr else []
            return []
        except Exception:
            return []
    
    @staticmethod
    def get_system_shortcuts(import_sources=None):
        """Obtém atalhos do sistema GNOME que usam CTRL ou SUPER
        
        Args:
            import_sources: dict com flags para habilitar/desabilitar fontes
                {'window_manager': bool, 'media_keys': bool, 'shell': bool}
        """
        shortcuts = {}
        
        # Default values if not specified
        if import_sources is None:
            import_sources = {
                'window_manager': True,
                'media_keys': True,
                'shell': True
            }
        
        try:
            # Atalhos do window manager
            if import_sources.get('window_manager', True):
                wm_settings = Gio.Settings.new('org.gnome.desktop.wm.keybindings')
                # Use get_all() to avoid deprecated list_keys()
                try:
                    all_settings = wm_settings.get_all()
                    for key, value in all_settings.items():
                        bindings = SystemKeymapImporter.get_binding_values(value)
                        for binding in bindings:
                            # Processar atalhos com CTRL ou SUPER
                            binding_lower = binding.lower()
                            has_ctrl = 'control' in binding_lower or 'ctrl' in binding_lower or 'primary' in binding_lower
                            has_super = 'super' in binding_lower or 'mod4' in binding_lower or 'mod5' in binding_lower
                            if not has_ctrl and not has_super:
                                continue  # Pular atalhos sem CTRL ou SUPER
                            parsed_key = SystemKeymapImporter.parse_keybinding(binding)
                            if parsed_key:
                                # Convert action name to readable description
                                desc = key.replace('_', ' ').replace('-', ' ').title()
                                shortcuts[parsed_key] = desc
                except:
                    # Fallback to list_keys() if get_all() doesn't work
                    try:
                        import warnings
                        with warnings.catch_warnings():
                            warnings.simplefilter("ignore")
                            wm_keys = wm_settings.list_keys()
                        for key in wm_keys:
                            try:
                                value = wm_settings.get_value(key)
                                bindings = SystemKeymapImporter.get_binding_values(value)
                                for binding in bindings:
                                    # Process shortcuts with CTRL or SUPER
                                    binding_lower = binding.lower()
                                    has_ctrl = 'control' in binding_lower or 'ctrl' in binding_lower or 'primary' in binding_lower
                                    has_super = 'super' in binding_lower or 'mod4' in binding_lower or 'mod5' in binding_lower
                                    if not has_ctrl and not has_super:
                                        continue
                                    parsed_key = SystemKeymapImporter.parse_keybinding(binding)
                                    if parsed_key:
                                        desc = key.replace('_', ' ').replace('-', ' ').title()
                                        shortcuts[parsed_key] = desc
                            except:
                                pass
                    except:
                        pass
            
            # Media shortcuts
            if import_sources.get('media_keys', True):
                try:
                    media_settings = Gio.Settings.new('org.gnome.settings-daemon.plugins.media-keys')
                    try:
                        all_settings = media_settings.get_all()
                        for key, value in all_settings.items():
                            bindings = SystemKeymapImporter.get_binding_values(value)
                            for binding in bindings:
                                # Process shortcuts with CTRL or SUPER
                                binding_lower = binding.lower()
                                has_ctrl = 'control' in binding_lower or 'ctrl' in binding_lower or 'primary' in binding_lower
                                has_super = 'super' in binding_lower or 'mod4' in binding_lower or 'mod5' in binding_lower
                                if not has_ctrl and not has_super:
                                    continue
                                parsed_key = SystemKeymapImporter.parse_keybinding(binding)
                                if parsed_key:
                                    desc = key.replace('_', ' ').replace('-', ' ').title()
                                    shortcuts[parsed_key] = desc
                    except:
                        import warnings
                        with warnings.catch_warnings():
                            warnings.simplefilter("ignore")
                            media_keys = media_settings.list_keys()
                        for key in media_keys:
                            try:
                                value = media_settings.get_value(key)
                                bindings = SystemKeymapImporter.get_binding_values(value)
                                for binding in bindings:
                                    # Process shortcuts with CTRL or SUPER
                                    binding_lower = binding.lower()
                                    has_ctrl = 'control' in binding_lower or 'ctrl' in binding_lower or 'primary' in binding_lower
                                    has_super = 'super' in binding_lower or 'mod4' in binding_lower or 'mod5' in binding_lower
                                    if not has_ctrl and not has_super:
                                        continue
                                    parsed_key = SystemKeymapImporter.parse_keybinding(binding)
                                    if parsed_key:
                                        desc = key.replace('_', ' ').replace('-', ' ').title()
                                        shortcuts[parsed_key] = desc
                            except:
                                pass
                except:
                    pass  # May not be available
            
            # Atalhos do shell
            if import_sources.get('shell', True):
                try:
                    shell_settings = Gio.Settings.new('org.gnome.shell.keybindings')
                    try:
                        all_settings = shell_settings.get_all()
                        for key, value in all_settings.items():
                            bindings = SystemKeymapImporter.get_binding_values(value)
                            for binding in bindings:
                                # Process shortcuts with CTRL or SUPER
                                binding_lower = binding.lower()
                                has_ctrl = 'control' in binding_lower or 'ctrl' in binding_lower or 'primary' in binding_lower
                                has_super = 'super' in binding_lower or 'mod4' in binding_lower or 'mod5' in binding_lower
                                if not has_ctrl and not has_super:
                                    continue
                                parsed_key = SystemKeymapImporter.parse_keybinding(binding)
                                if parsed_key:
                                    desc = key.replace('_', ' ').replace('-', ' ').title()
                                    shortcuts[parsed_key] = desc
                    except:
                        import warnings
                        with warnings.catch_warnings():
                            warnings.simplefilter("ignore")
                            shell_keys = shell_settings.list_keys()
                        for key in shell_keys:
                            try:
                                value = shell_settings.get_value(key)
                                bindings = SystemKeymapImporter.get_binding_values(value)
                                for binding in bindings:
                                    # Process shortcuts with CTRL or SUPER
                                    binding_lower = binding.lower()
                                    has_ctrl = 'control' in binding_lower or 'ctrl' in binding_lower or 'primary' in binding_lower
                                    has_super = 'super' in binding_lower or 'mod4' in binding_lower or 'mod5' in binding_lower
                                    if not has_ctrl and not has_super:
                                        continue
                                    parsed_key = SystemKeymapImporter.parse_keybinding(binding)
                                    if parsed_key:
                                        desc = key.replace('_', ' ').replace('-', ' ').title()
                                        shortcuts[parsed_key] = desc
                            except:
                                pass
                except:
                    pass  # May not be available
                
        except Exception as e:
            print(f"⚠️  Warning: Could not read all system shortcuts: {e}")
        
        return shortcuts


class KeymapHelper:
    def __init__(self, config_path, import_system=None):
        self.config_path = config_path
        self.config = self.load_config()
        
        # Determine if system shortcuts should be imported
        # If import_system is None, check if any source is enabled
        if import_system is None:
            import_sources = self.config.get('import_sources', {
                'window_manager': True,
                'media_keys': True,
                'shell': True
            })
            # Import if at least one source is enabled
            import_system = any(import_sources.values())
        
        # Import system shortcuts if requested
        if import_system:
            self.import_system_shortcuts()
        
        self.popup = None
        self.listener = None
        self.ctrl_pressed = False
        self.shift_pressed = False
        self.alt_pressed = False
        self.super_pressed = False
        
    def load_config(self):
        """Loads configuration from JSON file"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Configuration file not found: {self.config_path}")
            sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"Error reading configuration: {e}")
            sys.exit(1)
    
    def import_system_shortcuts(self):
        """Imports system shortcuts and saves to configuration file"""
        try:
            # Get import source configuration
            import_sources = self.config.get('import_sources', {
                'window_manager': True,
                'media_keys': True,
                'shell': True
            })
            system_shortcuts = SystemKeymapImporter.get_system_shortcuts(import_sources)
            
            # Save imported shortcuts separately
            old_imported = self.config.get('imported_shortcuts', {})
            
            # Update imported shortcuts in config
            self.config['imported_shortcuts'] = system_shortcuts
            
            # Count new imported shortcuts
            new_count = len([k for k in system_shortcuts.keys() if k not in old_imported])
            
            if new_count > 0 or len(system_shortcuts) != len(old_imported):
                # Save to file
                self.save_config()
                if new_count > 0:
                    print(f"📥 Imported {new_count} new shortcuts from GNOME system")
                else:
                    print(f"📥 Updated {len(system_shortcuts)} shortcuts from GNOME system")
        except Exception as e:
            print(f"⚠️  Warning: Could not import system shortcuts: {e}")
    
    def save_config(self):
        """Saves configuration to JSON file"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"⚠️  Warning: Could not save configuration: {e}")
    
    def get_all_shortcuts(self):
        """Retorna todos os atalhos (importados + configurados), com prioridade para os configurados"""
        imported = self.config.get('imported_shortcuts', {})
        configured = self.config.get('configured_shortcuts', self.config.get('shortcuts', {}))  # Compatibility with old name
        # Configured shortcuts override imported ones (maintains customizations)
        return {**imported, **configured}
    
    def on_press(self, key):
        """Callback when a key is pressed"""
        try:
            # Check if it's CTRL
            if key == keyboard.Key.ctrl_l or key == keyboard.Key.ctrl_r:
                if not self.ctrl_pressed:
                    self.ctrl_pressed = True
                    # Show popup in GTK main thread (no timeout)
                    GLib.idle_add(self.show_popup)
            # Check if it's Super/Windows (cmd in pynput)
            elif hasattr(keyboard.Key, 'cmd') and (key == keyboard.Key.cmd or key == keyboard.Key.cmd_r):
                if not self.super_pressed:
                    self.super_pressed = True
                    # Show popup in GTK main thread (no timeout)
                    GLib.idle_add(self.show_popup)
            # Note: The Fn key doesn't send direct events on most keyboards,
            # so we can't detect it. It only modifies other keys.
            # Check if it's SHIFT
            elif key == keyboard.Key.shift_l or key == keyboard.Key.shift_r:
                if not self.shift_pressed:
                    self.shift_pressed = True
                    # If any modifier key is pressed, show/update popup
                    if self.ctrl_pressed or self.super_pressed or self.alt_pressed:
                        if self.popup:
                            GLib.idle_add(self.update_filter, priority=GLib.PRIORITY_HIGH)
                        else:
                            GLib.idle_add(self.show_popup)
            # Check if it's ALT
            elif key == keyboard.Key.alt_l or key == keyboard.Key.alt_r:
                if not self.alt_pressed:
                    self.alt_pressed = True
                    # Show popup in GTK main thread (no timeout)
                    GLib.idle_add(self.show_popup)
        except AttributeError:
            pass
        
        # Try to detect Super using key code (fallback for Linux)
        try:
            # On Linux/X11, Super usually has code 133 (left) or 134 (right)
            if hasattr(key, 'vk') and (key.vk == 133 or key.vk == 134):
                if not self.super_pressed:
                    self.super_pressed = True
                    GLib.idle_add(self.show_popup)
        except:
            pass
    
    def on_release(self, key):
        """Callback when a key is released"""
        try:
            if key == keyboard.Key.ctrl_l or key == keyboard.Key.ctrl_r:
                self.ctrl_pressed = False
                if not self.super_pressed and not self.alt_pressed:
                    GLib.idle_add(self.hide_popup)
                elif self.popup:
                    GLib.idle_add(self.update_filter)
            elif hasattr(keyboard.Key, 'cmd') and (key == keyboard.Key.cmd or key == keyboard.Key.cmd_r):
                self.super_pressed = False
                if not self.ctrl_pressed and not self.alt_pressed:
                    GLib.idle_add(self.hide_popup)
                elif self.popup:
                    GLib.idle_add(self.update_filter)
            elif key == keyboard.Key.shift_l or key == keyboard.Key.shift_r:
                self.shift_pressed = False
                if (self.ctrl_pressed or self.super_pressed or self.alt_pressed) and self.popup:
                    GLib.idle_add(self.update_filter)
            elif key == keyboard.Key.alt_l or key == keyboard.Key.alt_r:
                self.alt_pressed = False
                if not self.ctrl_pressed and not self.super_pressed:
                    GLib.idle_add(self.hide_popup)
                elif self.popup:
                    GLib.idle_add(self.update_filter)
        except AttributeError:
            pass
        
        # Try to detect Super using key code (fallback for Linux)
        try:
            # On Linux/X11, Super usually has code 133 (left) or 134 (right)
            if hasattr(key, 'vk') and (key.vk == 133 or key.vk == 134):
                self.super_pressed = False
                if not self.ctrl_pressed and not self.alt_pressed:
                    GLib.idle_add(self.hide_popup)
                elif self.popup:
                    GLib.idle_add(self.update_filter)
        except:
            pass
    
    def update_filter(self):
        """Updates the popup filter based on pressed keys"""
        if self.popup:
            pressed_keys = {
                'ctrl': self.ctrl_pressed,
                'super': self.super_pressed,
                'alt': self.alt_pressed,
                'shift': self.shift_pressed
            }
            key_aliases = self.config.get('key_aliases', {})
            self.popup.filter_shortcuts(pressed_keys, key_aliases)
        return False  # Remove from idle_add
    
    def show_popup(self):
        """Mostra o popup (chamado no thread principal do GTK)"""
        if not self.popup:
            # Get all shortcuts (imported + user)
            shortcuts = self.get_all_shortcuts()
            settings = self.config.get('popup_settings', {})
            key_aliases = self.config.get('key_aliases', {})
            configured_shortcuts = self.config.get('configured_shortcuts', self.config.get('shortcuts', {}))  # Compatibility
            imported_shortcuts = self.config.get('imported_shortcuts', {})
            self.popup = KeymapPopup(shortcuts, settings, key_aliases, configured_shortcuts, imported_shortcuts)
        
        # Get pressed keys
        pressed_keys = {
            'ctrl': self.ctrl_pressed,
            'super': self.super_pressed,
            'alt': self.alt_pressed,
            'shift': self.shift_pressed
        }
        key_aliases = self.config.get('key_aliases', {})
        
        # Show without timeout (stays open while any modifier key is pressed)
        # Aliases are already in popup (passed in __init__)
        self.popup.show(use_timeout=False, pressed_keys=pressed_keys)
        return False  # Remove do idle_add
    
    def hide_popup(self):
        """Oculta o popup (chamado no thread principal do GTK)"""
        if self.popup:
            self.popup.hide()
        return False  # Remove do idle_add
    
    def start(self):
        """Starts key monitoring"""
        # Get all shortcuts (imported + user)
        shortcuts = self.get_all_shortcuts()
        settings = self.config.get('popup_settings', {})
        key_aliases = self.config.get('key_aliases', {})
        configured_shortcuts = self.config.get('configured_shortcuts', self.config.get('shortcuts', {}))  # Compatibility
        imported_shortcuts = self.config.get('imported_shortcuts', {})
        self.popup = KeymapPopup(shortcuts, settings, key_aliases, configured_shortcuts, imported_shortcuts)
        
        # Create keyboard listener
        self.listener = keyboard.Listener(
            on_press=self.on_press,
            on_release=self.on_release
        )
        self.listener.start()
        
        print("ShortcutHelper started!")
        print("Press CTRL, Super (Windows) or ALT to see shortcuts.")
        print("Press Ctrl+C to exit.")
        
        # Start GTK loop
        try:
            Gtk.main()
        except KeyboardInterrupt:
            self.stop()
    
    def stop(self):
        """Stops monitoring"""
        if self.listener:
            self.listener.stop()
        Gtk.main_quit()
        print("\nShortcutHelper stopped.")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='ShortcutHelper - Shows keyboard shortcuts when modifier keys are pressed')
    parser.add_argument('--no-import-system', action='store_true',
                        help='Não importar atalhos do sistema automaticamente')
    parser.add_argument('--import-only', action='store_true',
                        help='Apenas importar atalhos do sistema e salvar no arquivo de configuração')
    
    args = parser.parse_args()
    
    # Configuration file path
    script_dir = Path(__file__).parent
    config_path = script_dir / 'config.json'
    
    # If only importing, do that and exit
    if args.import_only:
        try:
            config = {}
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            
            # Get import source configuration
            import_sources = config.get('import_sources', {
                'window_manager': True,
                'media_keys': True,
                'shell': True
            })
            system_shortcuts = SystemKeymapImporter.get_system_shortcuts(import_sources)
            
            # Save imported shortcuts separately
            config['imported_shortcuts'] = system_shortcuts
            
            # Save
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            print(f"✅ Imported {len(system_shortcuts)} shortcuts from system to {config_path}")
            print(f"   Shortcuts saved in 'imported_shortcuts' (separated from user shortcuts)")
            return
        except Exception as e:
            print(f"❌ Error importing: {e}")
            sys.exit(1)
    
    # Create and start the helper
    import_system = not args.no_import_system
    helper = KeymapHelper(config_path, import_system=import_system)
    helper.start()


if __name__ == '__main__':
    main()
