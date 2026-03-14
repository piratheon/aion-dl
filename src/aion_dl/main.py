#!/usr/bin/env python3
"""
main.py - Entry point for Aion-dl.

Usage:
    python main.py
    python main.py https://www.youtube.com/watch?v=...
"""

import logging
import sys

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gio, GLib, Gdk

from . import APP_ID, __version__ as APP_VERSION
from .window import MainWindow, SHORTCUTS_XML


class YtDlpApplication(Adw.Application):
    def __init__(self) -> None:
        super().__init__(
            application_id=APP_ID,
            flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
        )
        # Ensure icon is loaded from local assets for dev
        import os
        asset_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "assets")
        Gtk.IconTheme.get_for_display(Gdk.Display.get_default()).add_search_path(asset_path)

        GLib.set_application_name("Aion-dl")
        GLib.set_prgname(APP_ID)
        self.connect("activate", self._on_activate)
        self.connect("open", self._on_open)
        self._setup_app_actions()

    # ------------------------------------------------------------------

    def _on_activate(self, _app) -> None:
        win = self._get_or_create_window()
        win.present()

    def _on_open(self, _app, files, _hint) -> None:
        win = self._get_or_create_window()
        from .models import DownloadOptions
        for f in files:
            url = f.get_uri()
            opts = DownloadOptions()
            win._on_add_url(url, opts)
        win.present()

    def _get_or_create_window(self) -> MainWindow:
        win = self.get_active_window()
        if win is None:
            win = MainWindow(application=self)
        return win

    # ------------------------------------------------------------------

    def _setup_app_actions(self) -> None:
        actions = {
            "quit":        lambda: self.quit(),
            "shortcuts":   self._show_shortcuts,
            "about":       self._show_about,
        }
        for name, cb in actions.items():
            act = Gio.SimpleAction.new(name, None)
            act.connect("activate", lambda _a, _p, fn=cb: fn())
            self.add_action(act)

        self.set_accels_for_action("app.quit",      ["<primary>q"])
        self.set_accels_for_action("app.shortcuts", ["<primary>question"])

    def _show_shortcuts(self) -> None:
        builder = Gtk.Builder.new_from_string(SHORTCUTS_XML, -1)
        shortcuts = builder.get_object("shortcuts_window")
        shortcuts.set_transient_for(self.get_active_window())
        shortcuts.present()

    def _show_about(self) -> None:
        about = Adw.AboutWindow(
            transient_for=self.get_active_window(),
            application_name="Aion-dl",
            application_icon=APP_ID,
            developer_name="Piratheon",
            version=APP_VERSION,
            website="https://github.com/Piratheon/Aion-dl",
            issue_url="https://github.com/Piratheon/Aion-dl/issues",
            license_type=Gtk.License.GPL_3_0,
            comments=(
                "A full-featured GTK4/Adwaita frontend for yt-dlp.\n"
                "Download video and audio from 1000+ sites."
            ),
            developers=["Piratheon"],
        )
        about.present()


def main() -> int:
    app = YtDlpApplication()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
