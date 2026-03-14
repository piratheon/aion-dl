"""
url_bar.py - URL input bar with format popover and paste button.
"""

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Gdk", "4.0")
from gi.repository import Gtk, Adw, Gdk, GLib

from ..models import DownloadOptions
from ..config import ConfigManager
from .format_panel import FormatPanel


class UrlBar(Gtk.Box):
    """
    Composite widget:
      [  URL entry  ... ] [Paste] [Add] [v → FormatPanel popover]
    """

    def __init__(self, config: ConfigManager, on_add) -> None:
        super().__init__(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=8,
            margin_top=10,
            margin_bottom=10,
            margin_start=12,
            margin_end=12,
        )
        self._config = config
        self._on_add = on_add
        self._format_panel = FormatPanel()
        self._build()

    # ------------------------------------------------------------------

    def _build(self) -> None:
        # URL entry
        self._entry = Gtk.Entry()
        self._entry.set_hexpand(True)
        self._entry.set_placeholder_text(
            "Paste a URL — YouTube, Twitch, SoundCloud, Twitter/X, …"
        )
        self._entry.set_icon_from_icon_name(
            Gtk.EntryIconPosition.PRIMARY, "edit-paste-symbolic"
        )
        self._entry.connect("activate", self._on_activate)
        self._entry.connect("icon-press", self._on_icon_press)
        self.append(self._entry)

        # Paste button
        paste_btn = Gtk.Button(label="Paste")
        paste_btn.add_css_class("flat")
        paste_btn.set_tooltip_text("Paste from clipboard (Ctrl+V)")
        paste_btn.connect("clicked", self._paste_from_clipboard)
        self.append(paste_btn)

        # Separator
        sep = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        sep.set_margin_top(6)
        sep.set_margin_bottom(6)
        self.append(sep)

        # Add button
        add_btn = Gtk.Button(label="Add")
        add_btn.add_css_class("suggested-action")
        add_btn.set_tooltip_text("Add URL to queue (Enter)")
        add_btn.connect("clicked", self._on_activate)
        self.append(add_btn)

        # Options dropdown button
        opts_btn = Gtk.MenuButton(
            icon_name="go-down-symbolic",
            tooltip_text="Download options",
        )
        opts_btn.add_css_class("flat")
        opts_btn.set_popover(self._format_panel)
        self.append(opts_btn)

    # ------------------------------------------------------------------

    def _on_activate(self, *_args) -> None:
        url = self._entry.get_text().strip()
        if not url:
            self._shake_entry()
            return
        opts = self._format_panel.get_options()
        # Apply global defaults for output dir if not set per-job
        if not opts.output_dir:
            opts.output_dir = self._config.config.default_output_dir
        if not opts.output_template:
            opts.output_template = self._config.config.output_template
        self._on_add(url, opts)
        self._entry.set_text("")

    def _on_icon_press(self, entry, icon_pos) -> None:
        if icon_pos == Gtk.EntryIconPosition.PRIMARY:
            self._paste_from_clipboard()

    def _paste_from_clipboard(self, *_args) -> None:
        display = Gdk.Display.get_default()
        clipboard = display.get_clipboard()
        clipboard.read_text_async(None, self._on_clipboard_text)

    def _on_clipboard_text(self, clipboard, result) -> None:
        try:
            text = clipboard.read_text_finish(result)
            if text:
                self._entry.set_text(text.strip())
                self._entry.set_position(-1)
        except Exception:
            pass

    def _shake_entry(self) -> None:
        self._entry.add_css_class("error")
        GLib.timeout_add(600, self._clear_error_class)

    def _clear_error_class(self) -> bool:
        self._entry.remove_css_class("error")
        return False

    def get_entry(self) -> Gtk.Entry:
        return self._entry
