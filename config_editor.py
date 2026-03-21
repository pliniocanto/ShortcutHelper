"""
config_editor — friendly tabbed GTK dialog for editing ShortcutHelper's config.
"""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk


POSITIONS = ["bottom-right", "bottom-left", "top-right", "top-left"]


def open_config_editor(config, save_config_fn):
    """Opens the config editor dialog.

    Args:
        config:         The live config dict (modified in-place on Save).
        save_config_fn: Callable that persists config to disk.

    Returns:
        False  (so it can be used directly as a GLib.idle_add callback).
    """
    dialog = Gtk.Dialog(title="ShortcutHelper Settings", transient_for=None, modal=True)
    dialog.set_default_size(750, 520)
    dialog.add_button("Cancel", Gtk.ResponseType.CANCEL)
    save_btn = dialog.add_button("Save", Gtk.ResponseType.OK)
    save_btn.get_style_context().add_class("suggested-action")

    notebook = Gtk.Notebook()
    notebook.set_margin_start(8)
    notebook.set_margin_end(8)
    notebook.set_margin_top(8)
    notebook.set_margin_bottom(8)
    dialog.get_content_area().pack_start(notebook, True, True, 0)

    shortcuts_store  = _build_shortcuts_tab(notebook, config)
    timeout_spin, font_spin, position_combo, wm_check, media_check, shell_check = \
        _build_settings_tab(notebook, config)
    aliases_store    = _build_aliases_tab(notebook, config)
    _build_imported_tab(notebook, config)

    dialog.show_all()
    response = dialog.run()

    if response == Gtk.ResponseType.OK:
        config['configured_shortcuts'] = {
            row[0].strip(): row[1].strip()
            for row in shortcuts_store
            if row[0].strip() and row[1].strip()
        }
        config['popup_settings'] = {
            'timeout':   int(timeout_spin.get_value()),
            'font_size': int(font_spin.get_value()),
            'position':  position_combo.get_active_text(),
        }
        config['import_sources'] = {
            'window_manager': wm_check.get_active(),
            'media_keys':     media_check.get_active(),
            'shell':          shell_check.get_active(),
        }
        config['key_aliases'] = {
            row[0].strip(): row[1].strip()
            for row in aliases_store
            if row[0].strip() and row[1].strip()
        }
        save_config_fn()
        print("Config saved.")

    dialog.destroy()
    return False


# ── Tab builders ─────────────────────────────────────────────────────────────

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

    notebook.append_page(grid, Gtk.Label(label="Settings"))
    return timeout_spin, font_spin, position_combo, wm_check, media_check, shell_check


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
    store = Gtk.ListStore(str, str)
    for k, v in sorted(config.get('imported_shortcuts', {}).items()):
        store.append([k, v])

    view = Gtk.TreeView(model=store)
    view.set_headers_visible(True)
    for col_idx, title in enumerate(["Shortcut", "Description"]):
        col = Gtk.TreeViewColumn(title, Gtk.CellRendererText(), text=col_idx)
        col.set_expand(True)
        view.append_column(col)

    scrolled = Gtk.ScrolledWindow()
    scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
    scrolled.add(view)

    note = Gtk.Label()
    note.set_markup("<small><i>Auto-imported from GNOME — not editable here.</i></small>")
    note.set_margin_start(8)
    note.set_margin_bottom(6)
    note.set_halign(Gtk.Align.START)

    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    box.pack_start(scrolled, True, True, 0)
    box.pack_start(note, False, False, 0)

    notebook.append_page(box, Gtk.Label(label="Imported Shortcuts"))


# ── Helpers ───────────────────────────────────────────────────────────────────

def _editable_tree_view(store, column_titles):
    """Creates a TreeView with editable columns backed by the given ListStore."""
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
    """Wraps a TreeView in a scrolled window and adds Add/Remove buttons below."""
    scrolled = Gtk.ScrolledWindow()
    scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
    scrolled.add(view)

    btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
    btn_box.set_margin_start(6)
    btn_box.set_margin_end(6)
    btn_box.set_margin_top(4)
    btn_box.set_margin_bottom(6)
    btn_box.pack_start(add_btn, False, False, 0)
    btn_box.pack_start(remove_btn, False, False, 0)

    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    box.pack_start(scrolled, True, True, 0)
    box.pack_start(btn_box, False, False, 0)
    return box


def _grid_heading(grid, row, text):
    label = Gtk.Label()
    label.set_markup(f"<b>{text}</b>")
    label.set_halign(Gtk.Align.START)
    grid.attach(label, 0, row, 2, 1)
    return row + 1
