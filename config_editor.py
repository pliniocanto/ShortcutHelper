"""
config_editor — tabbed settings window for ShortcutHelper.

Uses the same undecorated RGBA + Cairo approach as KeymapPopup so the
rounded corners are drawn correctly on all compositors.
"""

import math

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk


POSITIONS    = ["bottom-right", "bottom-left", "top-right", "top-left"]
CORNER_RADIUS = 12
BG_COLOR      = (30/255, 30/255, 30/255)

SOURCE_DISPLAY = {
    'window_manager':     'WM',
    'media_keys':         'Media',
    'shell':              'Shell',
    'custom_keybindings': 'Custom',
}

# All large containers are transparent so Cairo's rounded rect shows through.
# Individual widgets (buttons, spinbuttons, etc.) keep their theme styling.
EDITOR_CSS = """
#config-editor,
#config-editor box,
#config-editor notebook,
#config-editor notebook > stack,
#config-editor scrolledwindow,
#config-editor viewport,
#config-editor grid {
    background-color: transparent;
}
#config-editor label {
    color: rgb(220, 220, 220);
    background-color: transparent;
}
#config-editor separator {
    background-color: rgba(255, 255, 255, 0.15);
    min-height: 1px;
}
#config-editor notebook header {
    background-color: rgba(255, 255, 255, 0.06);
    border-bottom: 1px solid rgba(255, 255, 255, 0.12);
}
#config-editor notebook tab {
    color: rgba(220, 220, 220, 0.65);
    padding: 4px 10px;
}
#config-editor notebook tab:checked {
    color: rgb(255, 255, 255);
}
#config-editor treeview {
    background-color: transparent;
    color: rgb(220, 220, 220);
}
#config-editor treeview:selected,
#config-editor treeview row:selected {
    background-color: #2a5298;
    color: white;
}
#config-editor treeview header button {
    background-color: rgba(255, 255, 255, 0.06);
    color: rgb(180, 180, 180);
    border: none;
}
#config-editor eventbox,
#config-editor .title-bar {
    background-color: transparent;
}
#config-editor button.suggested-action {
    background-color: #2a5298;
    color: white;
}
#config-editor button.suggested-action:hover {
    background-color: #3463b8;
}
#config-editor button.suggested-action:active {
    background-color: #1e3d70;
}
"""


# ── Window drawing ────────────────────────────────────────────────────────────

def _on_draw(widget, cr):
    """Paints the rounded-rectangle background (same as KeymapPopup)."""
    w = widget.get_allocated_width()
    h = widget.get_allocated_height()
    r = CORNER_RADIUS

    cr.save()
    cr.set_operator(0)   # OPERATOR_CLEAR — wipe to transparent
    cr.paint()
    cr.restore()

    cr.new_sub_path()
    cr.arc(r,     r,     r, math.pi,           3 * math.pi / 2)
    cr.arc(w - r, r,     r, 3 * math.pi / 2,  0)
    cr.arc(w - r, h - r, r, 0,                 math.pi / 2)
    cr.arc(r,     h - r, r, math.pi / 2,       math.pi)
    cr.close_path()

    cr.set_source_rgba(*BG_COLOR, 1.0)
    cr.fill()
    return False


def _apply_css(win):
    provider = Gtk.CssProvider()
    provider.load_from_data(EDITOR_CSS.encode())
    Gtk.StyleContext.add_provider_for_screen(
        win.get_screen(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
    )


# ── Public entry point ────────────────────────────────────────────────────────

def open_config_editor(config, save_config_fn):
    """Opens the config editor window (blocks until closed).

    Args:
        config:         The live config dict (modified in-place on Save).
        save_config_fn: Callable that persists config to disk.

    Returns:
        False  (so it can be used directly as a GLib.idle_add callback).
    """
    win = Gtk.Window(type=Gtk.WindowType.TOPLEVEL)
    win.set_name("config-editor")
    win.set_title("ShortcutHelper Settings")
    win.set_decorated(False)
    win.set_modal(True)
    win.set_resizable(False)
    win.set_default_size(750, 540)
    win.set_position(Gtk.WindowPosition.NONE)

    # RGBA visual — required for OPERATOR_CLEAR to produce transparency
    screen = win.get_screen()
    rgba   = screen.get_rgba_visual()
    if rgba:
        win.set_visual(rgba)
    win.set_app_paintable(True)
    win.connect('draw', _on_draw)

    _apply_css(win)

    # ── Title bar ────────────────────────────────────────────────────────
    title_label = Gtk.Label()
    title_label.set_markup("<b>ShortcutHelper Settings</b>")

    close_btn = Gtk.Button()
    close_btn.set_relief(Gtk.ReliefStyle.NONE)
    close_btn.add(Gtk.Image.new_from_icon_name("window-close-symbolic",
                                                Gtk.IconSize.BUTTON))
    close_btn.connect("clicked", lambda _: win.destroy())

    title_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
    title_bar.get_style_context().add_class("title-bar")
    title_bar.set_margin_top(10)
    title_bar.set_margin_bottom(6)
    title_bar.set_margin_start(16)
    title_bar.set_margin_end(8)
    title_bar.pack_start(title_label, True, True, 0)
    title_bar.pack_start(close_btn,   False, False, 0)

    # EventBox gives the title bar its own GdkWindow so button events are delivered
    title_event_box = Gtk.EventBox()
    title_event_box.add(title_bar)

    def _on_title_press(_, event):
        if event.button == 1:
            win.begin_move_drag(event.button,
                                int(event.x_root), int(event.y_root),
                                event.time)
    title_event_box.connect('button-press-event', _on_title_press)

    # ── Notebook tabs ────────────────────────────────────────────────────
    notebook = Gtk.Notebook()
    notebook.set_margin_start(8)
    notebook.set_margin_end(8)
    notebook.set_margin_top(8)
    notebook.set_margin_bottom(0)

    shortcuts_store = _build_shortcuts_tab(notebook, config)
    timeout_spin, font_spin, position_combo, opacity_scale, \
        wm_check, media_check, shell_check, custom_check = \
        _build_settings_tab(notebook, config)
    aliases_store  = _build_aliases_tab(notebook, config)
    imported_store = _build_imported_tab(notebook, config)

    # ── Cancel / Save buttons ────────────────────────────────────────────
    result = [False]
    saved_widget_values = [None]

    cancel_btn = Gtk.Button(label="Cancel")
    save_btn   = Gtk.Button(label="Save")
    save_btn.get_style_context().add_class("suggested-action")

    def on_cancel(_): win.destroy()
    def on_save(_):
        result[0] = True
        # Capture widget values before win.destroy() frees them
        saved_widget_values[0] = {
            'timeout':   int(timeout_spin.get_value()),
            'font_size': int(font_spin.get_value()),
            'position':  position_combo.get_active_text(),
            'opacity':   round(opacity_scale.get_value(), 2),
            'wm':        wm_check.get_active(),
            'media':     media_check.get_active(),
            'shell':     shell_check.get_active(),
            'custom':    custom_check.get_active(),
        }
        win.destroy()

    cancel_btn.connect("clicked", on_cancel)
    save_btn.connect("clicked",   on_save)

    btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
    btn_box.set_halign(Gtk.Align.END)
    btn_box.set_margin_top(6)
    btn_box.set_margin_bottom(12)
    btn_box.set_margin_end(14)
    btn_box.pack_start(cancel_btn, False, False, 0)
    btn_box.pack_start(save_btn,   False, False, 0)

    # Escape closes the window
    win.connect('key-press-event',
                lambda w, e: w.destroy() if e.keyval == Gdk.KEY_Escape else None)

    # ── Assemble ─────────────────────────────────────────────────────────
    vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    vbox.pack_start(title_event_box, False, False, 0)
    vbox.pack_start(Gtk.Separator(),  False, False, 0)
    vbox.pack_start(notebook,  True,  True,  0)
    vbox.pack_start(btn_box,   False, False, 0)
    win.add(vbox)

    # Block until the window is closed (nested GTK main loop, same as Dialog.run())
    win.connect('destroy', lambda _: Gtk.main_quit())
    win.show_all()

    # Position top-right after show_all() so the window size is known
    display  = Gdk.Display.get_default()
    monitor  = display.get_primary_monitor().get_geometry()
    win_w, win_h = win.get_size()
    margin_right = 10
    margin_top   = 40
    win.move(monitor.x + monitor.width - win_w - margin_right, monitor.y + margin_top)

    Gtk.main()

    # ── Persist if saved ─────────────────────────────────────────────────
    if result[0]:
        v = saved_widget_values[0]
        config['configured_shortcuts'] = {
            row[0].strip(): row[1].strip()
            for row in shortcuts_store
            if row[0].strip() and row[1].strip()
        }
        config['popup_settings'] = {
            'timeout':   v['timeout'],
            'font_size': v['font_size'],
            'position':  v['position'],
            'opacity':   v['opacity'],
        }
        config['import_sources'] = {
            'window_manager':     v['wm'],
            'media_keys':         v['media'],
            'shell':              v['shell'],
            'custom_keybindings': v['custom'],
        }
        config['key_aliases'] = {
            row[0].strip(): row[1].strip()
            for row in aliases_store
            if row[0].strip() and row[1].strip()
        }

        remaining_imported = {row[0].strip() for row in imported_store if row[0].strip()}
        all_imported       = set(config.get('imported_shortcuts', {}).keys())
        newly_hidden       = all_imported - remaining_imported
        hidden             = set(config.get('hidden_imported_shortcuts', []))
        hidden.update(newly_hidden)
        config['hidden_imported_shortcuts'] = sorted(hidden)

        old_sources = config.get('imported_shortcuts_sources', {})
        config['imported_shortcuts'] = {
            row[0].strip(): row[1].strip()
            for row in imported_store
            if row[0].strip()
        }
        config['imported_shortcuts_sources'] = {
            k: old_sources[k] for k in config['imported_shortcuts'] if k in old_sources
        }

        save_config_fn()
        print("Config saved.")

    return False


# ── Tab builders ──────────────────────────────────────────────────────────────

def _build_shortcuts_tab(notebook, config):
    store = Gtk.ListStore(str, str)
    for key, desc in sorted(config.get('configured_shortcuts', {}).items()):
        store.append([key, desc])

    view = _editable_tree_view(store, ["Shortcut", "Description"])

    add_btn    = Gtk.Button(label="Add")
    remove_btn = Gtk.Button(label="Remove")

    def on_add(_):
        store.append(["Modifier+Key", "Description"])
        path = Gtk.TreePath(len(store) - 1)
        view.scroll_to_cell(path, None, False, 0, 0)
        view.set_cursor(path, view.get_columns()[0], True)

    def on_remove(_):
        model, it = view.get_selection().get_selected()
        if it:
            model.remove(it)

    add_btn.connect("clicked", on_add)
    remove_btn.connect("clicked", on_remove)

    notebook.append_page(
        _vbox_with_buttons(view, add_btn, remove_btn),
        Gtk.Label(label="My Shortcuts"),
    )
    return store


def _build_settings_tab(notebook, config):
    popup_settings = config.get('popup_settings', {})
    import_sources = config.get('import_sources', {})

    grid = Gtk.Grid()
    grid.set_row_spacing(14)
    grid.set_column_spacing(16)
    grid.set_margin_start(24)
    grid.set_margin_end(24)
    grid.set_margin_top(20)
    grid.set_margin_bottom(20)

    row = 0

    row = _grid_heading(grid, row, "Popup")

    grid.attach(Gtk.Label(label="Timeout (ms)", xalign=0), 0, row, 1, 1)
    timeout_spin = Gtk.SpinButton.new_with_range(500, 30000, 500)
    timeout_spin.set_value(popup_settings.get('timeout', 3000))
    timeout_spin.set_hexpand(True)
    grid.attach(timeout_spin, 1, row, 1, 1)
    row += 1

    grid.attach(Gtk.Label(label="Font Size", xalign=0), 0, row, 1, 1)
    font_spin = Gtk.SpinButton.new_with_range(8, 32, 1)
    font_spin.set_value(popup_settings.get('font_size', 12))
    grid.attach(font_spin, 1, row, 1, 1)
    row += 1

    grid.attach(Gtk.Label(label="Position", xalign=0), 0, row, 1, 1)
    position_combo = Gtk.ComboBoxText()
    for pos in POSITIONS:
        position_combo.append_text(pos)
    current = popup_settings.get('position', 'bottom-right')
    position_combo.set_active(POSITIONS.index(current) if current in POSITIONS else 0)
    grid.attach(position_combo, 1, row, 1, 1)
    row += 1

    grid.attach(Gtk.Label(label="Opacity", xalign=0), 0, row, 1, 1)
    opacity_box   = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
    opacity_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0.1, 1.0, 0.05)
    opacity_scale.set_value(popup_settings.get('opacity', 0.8))
    opacity_scale.set_hexpand(True)
    opacity_scale.set_draw_value(False)
    opacity_label = Gtk.Label(label=f"{popup_settings.get('opacity', 0.8):.0%}")
    opacity_label.set_width_chars(5)
    opacity_scale.connect('value-changed',
                          lambda s: opacity_label.set_text(f"{s.get_value():.0%}"))
    opacity_box.pack_start(opacity_scale, True,  True,  0)
    opacity_box.pack_start(opacity_label, False, False, 0)
    grid.attach(opacity_box, 1, row, 1, 1)
    row += 1

    sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
    sep.set_margin_top(4)
    sep.set_margin_bottom(4)
    grid.attach(sep, 0, row, 2, 1)
    row += 1

    row = _grid_heading(grid, row, "Import Sources")

    wm_check = Gtk.CheckButton(label="Window manager shortcuts")
    wm_check.set_active(import_sources.get('window_manager', True))
    grid.attach(wm_check, 0, row, 2, 1)
    row += 1

    media_check = Gtk.CheckButton(label="Media keys")
    media_check.set_active(import_sources.get('media_keys', False))
    grid.attach(media_check, 0, row, 2, 1)
    row += 1

    shell_check = Gtk.CheckButton(label="Shell shortcuts")
    shell_check.set_active(import_sources.get('shell', False))
    grid.attach(shell_check, 0, row, 2, 1)
    row += 1

    custom_check = Gtk.CheckButton(label="Custom keybindings (e.g. Ctrl+Alt+T)")
    custom_check.set_active(import_sources.get('custom_keybindings', True))
    grid.attach(custom_check, 0, row, 2, 1)

    notebook.append_page(grid, Gtk.Label(label="Settings"))
    return (timeout_spin, font_spin, position_combo, opacity_scale,
            wm_check, media_check, shell_check, custom_check)


def _build_aliases_tab(notebook, config):
    store = Gtk.ListStore(str, str)
    for k, v in sorted(config.get('key_aliases', {}).items()):
        store.append([k, v])

    view = _editable_tree_view(store, ["From (pressed)", "Acts as"])

    add_btn    = Gtk.Button(label="Add")
    remove_btn = Gtk.Button(label="Remove")

    def on_add(_):
        store.append(["Modifier+Key", "Modifier+Key"])
        path = Gtk.TreePath(len(store) - 1)
        view.scroll_to_cell(path, None, False, 0, 0)
        view.set_cursor(path, view.get_columns()[0], True)

    def on_remove(_):
        model, it = view.get_selection().get_selected()
        if it:
            model.remove(it)

    add_btn.connect("clicked", on_add)
    remove_btn.connect("clicked", on_remove)

    notebook.append_page(
        _vbox_with_buttons(view, add_btn, remove_btn),
        Gtk.Label(label="Key Aliases"),
    )
    return store


def _build_imported_tab(notebook, config):
    store   = Gtk.ListStore(str, str, str)   # shortcut, description, source
    sources = config.get('imported_shortcuts_sources', {})
    for k, v in sorted(config.get('imported_shortcuts', {}).items()):
        src = SOURCE_DISPLAY.get(sources.get(k, ''), sources.get(k, ''))
        store.append([k, v, src])

    view = Gtk.TreeView(model=store)
    view.set_headers_visible(True)
    for col_idx, title in enumerate(["Shortcut", "Description", "Source"]):
        col = Gtk.TreeViewColumn(title, Gtk.CellRendererText(), text=col_idx)
        col.set_expand(col_idx < 2)
        view.append_column(col)

    scrolled = Gtk.ScrolledWindow()
    scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
    scrolled.set_min_content_height(200)
    scrolled.set_max_content_height(360)
    scrolled.add(view)

    hide_btn = Gtk.Button(label="Hide selected")
    hide_btn.set_margin_start(6)
    hide_btn.set_margin_end(6)
    hide_btn.set_margin_top(4)
    hide_btn.set_margin_bottom(4)

    def on_hide(_):
        model, it = view.get_selection().get_selected()
        if it:
            model.remove(it)

    hide_btn.connect("clicked", on_hide)

    note = Gtk.Label()
    note.set_markup("<small><i>Auto-imported from GNOME. "
                    "Hidden shortcuts are permanently excluded from future imports.</i></small>")
    note.set_margin_start(8)
    note.set_margin_bottom(6)
    note.set_halign(Gtk.Align.START)

    btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
    btn_box.pack_start(hide_btn, False, False, 0)

    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    box.pack_start(scrolled, True,  True,  0)
    box.pack_start(btn_box,  False, False, 0)
    box.pack_start(note,     False, False, 0)

    notebook.append_page(box, Gtk.Label(label="Imported Shortcuts"))
    return store


# ── Helpers ───────────────────────────────────────────────────────────────────

def _editable_tree_view(store, column_titles):
    view = Gtk.TreeView(model=store)
    view.set_headers_visible(True)
    for col_idx, title in enumerate(column_titles):
        renderer = Gtk.CellRendererText()
        renderer.set_property("editable", True)
        renderer.set_property("placeholder-text", title)
        col = Gtk.TreeViewColumn(title, renderer, text=col_idx)
        col.set_expand(True)
        view.append_column(col)

        def on_edited(r, path, new_text, idx=col_idx):
            store[path][idx] = new_text
        renderer.connect("edited", on_edited)
    return view


def _vbox_with_buttons(view, add_btn, remove_btn):
    scrolled = Gtk.ScrolledWindow()
    scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
    scrolled.set_min_content_height(200)
    scrolled.set_max_content_height(380)
    scrolled.add(view)

    btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
    btn_box.set_margin_start(6)
    btn_box.set_margin_end(6)
    btn_box.set_margin_top(4)
    btn_box.set_margin_bottom(6)
    btn_box.pack_start(add_btn,    False, False, 0)
    btn_box.pack_start(remove_btn, False, False, 0)

    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    box.pack_start(scrolled, True,  True,  0)
    box.pack_start(btn_box,  False, False, 0)
    return box


def _grid_heading(grid, row, text):
    label = Gtk.Label()
    label.set_markup(f"<b>{text}</b>")
    label.set_halign(Gtk.Align.START)
    grid.attach(label, 0, row, 2, 1)
    return row + 1
