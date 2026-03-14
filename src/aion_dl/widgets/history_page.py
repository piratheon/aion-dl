"""
history_page.py - Completed downloads history with search, sort, open, copy.
"""

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gio, GLib

from ..config import ConfigManager


class HistoryPage(Gtk.Box):
    def __init__(self, config: ConfigManager) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self._config = config
        self._all_entries: list[dict] = []
        self._build()
        self.reload()

    # ------------------------------------------------------------------

    def _build(self) -> None:
        # Search bar
        self._search_bar = Gtk.SearchBar()
        self._search_entry = Gtk.SearchEntry()
        self._search_entry.set_hexpand(True)
        self._search_entry.connect("search-changed", self._on_search)
        self._search_bar.set_child(self._search_entry)
        self._search_bar.connect_entry(self._search_entry)
        self.append(self._search_bar)

        # Toolbar
        toolbar = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=8,
            margin_top=8,
            margin_bottom=4,
            margin_start=12,
            margin_end=12,
        )
        count_lbl = Gtk.Label(label="Download history", xalign=0, hexpand=True)
        count_lbl.add_css_class("title-4")
        self._count_label = count_lbl
        toolbar.append(count_lbl)

        clear_btn = Gtk.Button(label="Clear All")
        clear_btn.add_css_class("destructive-action")
        clear_btn.add_css_class("flat")
        clear_btn.connect("clicked", self._clear_history)
        toolbar.append(clear_btn)
        self.append(toolbar)

        # Scrolled list
        scroll = Gtk.ScrolledWindow()
        scroll.set_hexpand(True)
        scroll.set_vexpand(True)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        self._list = Gtk.ListBox()
        self._list.add_css_class("boxed-list")
        self._list.set_margin_top(4)
        self._list.set_margin_bottom(12)
        self._list.set_margin_start(12)
        self._list.set_margin_end(12)
        self._list.set_selection_mode(Gtk.SelectionMode.NONE)
        self._list.set_placeholder(self._build_empty())
        scroll.set_child(self._list)
        self.append(scroll)

    def _build_empty(self) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_valign(Gtk.Align.CENTER)
        box.set_halign(Gtk.Align.CENTER)
        box.set_margin_top(60)
        icon = Gtk.Image.new_from_icon_name("document-open-recent-symbolic")
        icon.set_pixel_size(48)
        icon.add_css_class("dim-label")
        box.append(icon)
        lbl = Gtk.Label(label="No history yet")
        lbl.add_css_class("title-2")
        box.append(lbl)
        sub = Gtk.Label(label="Completed downloads will appear here")
        sub.add_css_class("dim-label")
        box.append(sub)
        return box

    # ------------------------------------------------------------------

    def reload(self) -> None:
        self._all_entries = self._config.load_history()
        self._render(self._all_entries)

    def set_search_visible(self, visible: bool) -> None:
        self._search_bar.set_search_mode(visible)
        if visible:
            self._search_entry.grab_focus()

    # ------------------------------------------------------------------

    def _on_search(self, entry: Gtk.SearchEntry) -> None:
        query = entry.get_text().lower().strip()
        if not query:
            self._render(self._all_entries)
            return
        filtered = [
            e for e in self._all_entries
            if query in e.get("title", "").lower()
            or query in e.get("url", "").lower()
            or query in e.get("output_path", "").lower()
        ]
        self._render(filtered)

    def _render(self, entries: list[dict]) -> None:
        # Remove existing rows
        child = self._list.get_first_child()
        while child:
            nxt = child.get_next_sibling()
            self._list.remove(child)
            child = nxt

        for entry in entries:
            row = self._build_row(entry)
            self._list.append(row)

        n = len(entries)
        self._count_label.set_label(
            f"Download history  ·  {n} item{'s' if n != 1 else ''}"
        )

    def _build_row(self, entry: dict) -> Gtk.ListBoxRow:
        row = Gtk.ListBoxRow()
        row.set_margin_top(2)
        row.set_margin_bottom(2)

        outer = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=12,
            margin_top=10,
            margin_bottom=10,
            margin_start=12,
            margin_end=12,
        )

        icon = Gtk.Image.new_from_icon_name("emblem-ok-symbolic")
        icon.set_pixel_size(18)
        icon.add_css_class("success")
        icon.set_valign(Gtk.Align.CENTER)
        outer.append(icon)

        info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2, hexpand=True)

        title = entry.get("title", entry.get("url", "(unknown)"))
        title_lbl = Gtk.Label(label=title[:100], xalign=0, ellipsize=3)
        title_lbl.add_css_class("body")
        info.append(title_lbl)

        ts = entry.get("timestamp", "")
        path = entry.get("output_path", "")
        fmt = entry.get("format_note", "")
        sub_parts = [p for p in [fmt, path or entry.get("url", "")] if p]
        sub_lbl = Gtk.Label(label="  ·  ".join(sub_parts)[:120], xalign=0, ellipsize=3)
        sub_lbl.add_css_class("caption")
        sub_lbl.add_css_class("dim-label")
        info.append(sub_lbl)

        if ts:
            ts_lbl = Gtk.Label(label=ts, xalign=0)
            ts_lbl.add_css_class("caption")
            ts_lbl.add_css_class("dim-label")
            info.append(ts_lbl)

        outer.append(info)

        # Buttons
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)

        if path:
            open_btn = Gtk.Button(icon_name="media-playback-start-symbolic")
            open_btn.add_css_class("flat")
            open_btn.set_tooltip_text("Open file")
            open_btn.connect(
                "clicked",
                lambda _b, p=path: self._open_file(p),
            )
            btn_box.append(open_btn)

            folder_btn = Gtk.Button(icon_name="folder-open-symbolic")
            folder_btn.add_css_class("flat")
            folder_btn.set_tooltip_text("Show in folder")
            folder_btn.connect(
                "clicked",
                lambda _b, p=path: self._open_folder(p),
            )
            btn_box.append(folder_btn)

        url = entry.get("url", "")
        if url:
            copy_btn = Gtk.Button(icon_name="edit-copy-symbolic")
            copy_btn.add_css_class("flat")
            copy_btn.set_tooltip_text("Copy URL")
            copy_btn.connect(
                "clicked",
                lambda _b, u=url: self._copy_text(u),
            )
            btn_box.append(copy_btn)

        outer.append(btn_box)
        row.set_child(outer)
        return row

    # ------------------------------------------------------------------

    def _open_file(self, path: str) -> None:
        launcher = Gtk.FileLauncher.new(Gio.File.new_for_path(path))
        launcher.launch(self.get_root(), None, None)

    def _open_folder(self, path: str) -> None:
        import os
        folder = os.path.dirname(path)
        launcher = Gtk.FileLauncher.new(Gio.File.new_for_path(folder))
        launcher.launch(self.get_root(), None, None)

    def _copy_text(self, text: str) -> None:
        display = self.get_display()
        clipboard = display.get_clipboard()
        clipboard.set(text)

    def _clear_history(self, *_args) -> None:
        dlg = Adw.MessageDialog(
            transient_for=self.get_root(),
            heading="Clear Download History?",
            body="This will remove all history entries. Downloads already on disk are not affected.",
        )
        dlg.add_response("cancel", "Cancel")
        dlg.add_response("clear", "Clear All")
        dlg.set_response_appearance("clear", Adw.ResponseAppearance.DESTRUCTIVE)
        dlg.connect("response", self._on_clear_confirm)
        dlg.present()

    def _on_clear_confirm(self, dlg: Adw.MessageDialog, response: str) -> None:
        if response == "clear":
            self._config.clear_history()
            self.reload()
