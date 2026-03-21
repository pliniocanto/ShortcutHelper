"""
KeymapPopup — GTK popup window that displays matching keyboard shortcuts.
"""

import math

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib


SOURCE_LABELS = {
    'window_manager':    'WM',
    'media_keys':        'Media',
    'shell':             'Shell',
    'custom_keybindings': 'Custom',
}

MODIFIER_DISPLAY = {
    'ctrl': 'CTRL',
    'control': 'CTRL',
    'super': 'SUPER',
    'alt': 'ALT',
    'shift': 'SHIFT',
}

CORNER_RADIUS = 20
BG_COLOR = (30/255, 30/255, 30/255)

POPUP_CSS = """
#shortcut-popup,
#shortcut-popup box,
#shortcut-popup scrolledwindow,
#shortcut-popup viewport         { background-color: transparent; }
#shortcut-popup label            { color: rgb(255, 255, 255); font-size: 12px;
                                   background-color: transparent; }
#shortcut-popup separator        { background-color: rgba(255, 255, 255, 0.2); }
"""


def _format_shortcut_markup(key):
    """Converts 'Ctrl+Shift+A' -> '<b>CTRL + SHIFT + A</b>'"""
    parts = key.split('+')
    modifiers = []
    final_key = parts[-1]

    for part in parts[:-1]:
        label = MODIFIER_DISPLAY.get(part.lower(), part.upper())
        modifiers.append(label)

    if modifiers:
        return f"<b>{' + '.join(modifiers)} + {final_key.upper()}</b>"
    return f"<b>{final_key.upper()}</b>"


def _make_shortcut_row(key, description, source=None):
    """Creates a single row widget for a shortcut entry."""
    hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=25)

    key_label = Gtk.Label()
    key_label.set_markup(_format_shortcut_markup(key))
    key_label.set_width_chars(25)
    key_label.set_xalign(0)
    hbox.pack_start(key_label, False, False, 0)

    desc_label = Gtk.Label(label=description)
    desc_label.set_xalign(0)
    desc_label.set_ellipsize(3)
    hbox.pack_start(desc_label, True, True, 0)

    if source:
        tag = SOURCE_LABELS.get(source, source)
        src_label = Gtk.Label()
        src_label.set_markup(f"<small><span alpha='60%'>[{tag}]</span></small>")
        src_label.set_xalign(1)
        hbox.pack_start(src_label, False, False, 0)

    return hbox


class KeymapPopup:
    def __init__(self, shortcuts, settings, key_aliases=None,
                 configured_shortcuts=None, imported_shortcuts=None,
                 imported_sources=None):
        self.shortcuts = shortcuts
        self.settings = settings
        self.key_aliases = key_aliases or {}
        self.configured_shortcuts = configured_shortcuts or {}
        self.imported_shortcuts = imported_shortcuts or {}
        self.imported_sources = imported_sources or {}

        self.window = None
        self.timeout_id = None
        self.filtered_shortcuts = shortcuts.copy()
        self.scrolled = None
        self.shortcuts_box = None
        self.title_label = None
        self.current_modifiers = {'ctrl': False, 'super': False, 'alt': False, 'shift': False}

    # ── Window lifecycle ────────────────────────────────────────────────

    def create_window(self):
        self.window = Gtk.Window(type=Gtk.WindowType.POPUP)
        self.window.set_decorated(False)
        self.window.set_resizable(False)
        self.window.set_skip_taskbar_hint(True)
        self.window.set_skip_pager_hint(True)
        self.window.set_keep_above(True)
        self.window.set_accept_focus(False)
        self.window.set_size_request(600, -1)

        # Enable RGBA visual so the transparent background is composited
        screen = self.window.get_screen()
        rgba_visual = screen.get_rgba_visual()
        if rgba_visual:
            self.window.set_visual(rgba_visual)
        self.window.set_name("shortcut-popup")
        self.window.set_app_paintable(True)
        self.window.connect('draw', self._on_draw)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        vbox.set_border_width(15)
        vbox.set_margin_start(10)
        vbox.set_margin_end(10)
        vbox.set_margin_top(10)
        vbox.set_margin_bottom(10)

        self.title_label = Gtk.Label()
        self.title_label.set_markup("<b>Available Shortcuts</b>")
        self.title_label.set_margin_bottom(10)
        vbox.pack_start(self.title_label, False, False, 0)

        vbox.pack_start(Gtk.Separator(), False, False, 5)

        self.scrolled = Gtk.ScrolledWindow()
        self.scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.scrolled.set_min_content_height(200)
        self.scrolled.set_max_content_height(500)

        self.shortcuts_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.scrolled.add(self.shortcuts_box)
        vbox.pack_start(self.scrolled, True, True, 0)

        self.window.add(vbox)
        self._apply_css()
        self._position_window()

    def _on_draw(self, widget, cr):
        """Paints the rounded-rectangle background with configurable opacity."""
        w = widget.get_allocated_width()
        h = widget.get_allocated_height()
        r = CORNER_RADIUS
        opacity = self.settings.get('opacity', 0.8)

        # Clear entire surface to transparent
        cr.save()
        cr.set_operator(0)  # cairo.OPERATOR_CLEAR
        cr.paint()
        cr.restore()

        # Draw filled rounded rectangle
        cr.new_sub_path()
        cr.arc(r,     r,     r, math.pi,           3 * math.pi / 2)
        cr.arc(w - r, r,     r, 3 * math.pi / 2,  0)
        cr.arc(w - r, h - r, r, 0,                 math.pi / 2)
        cr.arc(r,     h - r, r, math.pi / 2,       math.pi)
        cr.close_path()

        cr.set_source_rgba(*BG_COLOR, opacity)
        cr.fill()
        return False

    def _apply_css(self):
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(POPUP_CSS.encode())
        Gtk.StyleContext.add_provider_for_screen(
            self.window.get_screen(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

    def _position_window(self):
        display = Gdk.Display.get_default()
        geometry = display.get_primary_monitor().get_geometry()
        self.window.show_all()
        width, height = self.window.get_size()
        margin = 20
        self.window.move(geometry.width - width - margin,
                         geometry.height - height - margin)

    def show(self, use_timeout=True, pressed_keys=None):
        if not self.window:
            self.create_window()

        if pressed_keys is not None:
            self.filter_shortcuts(pressed_keys, self.key_aliases)

        if self.timeout_id:
            GLib.source_remove(self.timeout_id)
            self.timeout_id = None

        self.window.show_all()
        self.window.present()
        self.window.queue_draw()

        if use_timeout:
            timeout_ms = self.settings.get('timeout', 3000)
            self.timeout_id = GLib.timeout_add(timeout_ms, self.hide)

    def hide(self):
        if self.window:
            self.window.hide()
        if self.timeout_id:
            GLib.source_remove(self.timeout_id)
            self.timeout_id = None
        return False

    # ── Filtering & rendering ────────────────────────────────────────────

    def filter_shortcuts(self, pressed_keys, key_aliases=None):
        key_aliases = key_aliases or {}

        prefix_parts = [
            name for name, flag in [
                ('Ctrl', pressed_keys.get('ctrl')),
                ('Super', pressed_keys.get('super')),
                ('Alt', pressed_keys.get('alt')),
                ('Shift', pressed_keys.get('shift')),
            ] if flag
        ]

        if not prefix_parts:
            self.filtered_shortcuts = {}
            self._update_title(pressed_keys)
            self._render_shortcuts()
            return

        self.current_modifiers = dict(pressed_keys)
        required = set(p.lower() for p in prefix_parts)

        filtered = {}
        for key, desc in self.shortcuts.items():
            key_modifiers = set(p.lower() for p in key.split('+')[:-1])
            if required.issubset(key_modifiers):
                filtered[key] = desc

        for alias_key, mapped_key in key_aliases.items():
            alias_modifiers = set(p.lower() for p in alias_key.split('+')[:-1])
            if required.issubset(alias_modifiers) and mapped_key in self.shortcuts:
                filtered[alias_key] = f"{self.shortcuts[mapped_key]} (via {mapped_key})"

        self.filtered_shortcuts = filtered
        self._update_title(pressed_keys)
        self._render_shortcuts()

    def _update_title(self, pressed_keys):
        if not self.title_label:
            return
        parts = [
            label for key, label in [
                ('ctrl', 'CTRL'), ('super', 'SUPER'), ('alt', 'ALT'), ('shift', 'SHIFT')
            ] if pressed_keys.get(key)
        ]
        if parts:
            self.title_label.set_markup(f"<b>Available Shortcuts ({' + '.join(parts)} + ...)</b>")
        else:
            self.title_label.set_markup("<b>Available Shortcuts</b>")

    def _render_shortcuts(self):
        if not self.shortcuts_box:
            return

        for child in self.shortcuts_box.get_children():
            self.shortcuts_box.remove(child)

        user_items = sorted(
            [(k, v) for k, v in self.filtered_shortcuts.items() if k in self.configured_shortcuts],
            key=lambda x: x[0].lower(),
        )
        imported_items = sorted(
            [(k, v) for k, v in self.filtered_shortcuts.items() if k not in self.configured_shortcuts],
            key=lambda x: x[0].lower(),
        )

        for key, desc in user_items:
            self.shortcuts_box.pack_start(_make_shortcut_row(key, desc), False, False, 0)

        if user_items and imported_items:
            sep = Gtk.Separator()
            sep.set_margin_top(10)
            sep.set_margin_bottom(10)
            self.shortcuts_box.pack_start(sep, False, False, 0)

        for key, desc in imported_items:
            source = self.imported_sources.get(key)
            self.shortcuts_box.pack_start(_make_shortcut_row(key, desc, source), False, False, 0)

        self.shortcuts_box.show_all()
