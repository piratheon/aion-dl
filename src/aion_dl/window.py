"""
window.py - Main application window.

Navigation: Adw.ViewSwitcher in header bar (Queue / History).
Settings: Opens as a separate Adw.PreferencesWindow subwindow.
"""

import time
import logging

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Gdk", "4.0")
from gi.repository import Gtk, Adw, Gio, Gdk, GLib

from .models import DownloadJob, DownloadOptions, JobState, TERMINAL_STATES, ACTIVE_STATES
from .config import ConfigManager
from .downloader import DownloadEngine
from .widgets.url_bar import UrlBar
from .widgets.download_row import DownloadRow
from .widgets.history_page import HistoryPage
from . import APP_ID

logger = logging.getLogger(__name__)

SHORTCUTS_XML = """<?xml version="1.0" encoding="UTF-8"?>
<interface>
  <object class="GtkShortcutsWindow" id="shortcuts_window">
    <property name="modal">1</property>
    <child>
      <object class="GtkShortcutsSection">
        <child>
          <object class="GtkShortcutsGroup">
            <property name="title">General</property>
            <child>
              <object class="GtkShortcutsShortcut">
                <property name="title">Add URL / confirm</property>
                <property name="accelerator">Return</property>
              </object>
            </child>
            <child>
              <object class="GtkShortcutsShortcut">
                <property name="title">Focus URL bar</property>
                <property name="accelerator">&lt;Primary&gt;l</property>
              </object>
            </child>
            <child>
              <object class="GtkShortcutsShortcut">
                <property name="title">Preferences</property>
                <property name="accelerator">&lt;Primary&gt;comma</property>
              </object>
            </child>
            <child>
              <object class="GtkShortcutsShortcut">
                <property name="title">Queue page</property>
                <property name="accelerator">&lt;Primary&gt;1</property>
              </object>
            </child>
            <child>
              <object class="GtkShortcutsShortcut">
                <property name="title">History page</property>
                <property name="accelerator">&lt;Primary&gt;2</property>
              </object>
            </child>
            <child>
              <object class="GtkShortcutsShortcut">
                <property name="title">Search history</property>
                <property name="accelerator">&lt;Primary&gt;f</property>
              </object>
            </child>
            <child>
              <object class="GtkShortcutsShortcut">
                <property name="title">Clear finished jobs</property>
                <property name="accelerator">&lt;Primary&gt;Delete</property>
              </object>
            </child>
            <child>
              <object class="GtkShortcutsShortcut">
                <property name="title">Keyboard shortcuts</property>
                <property name="accelerator">&lt;Primary&gt;question</property>
              </object>
            </child>
            <child>
              <object class="GtkShortcutsShortcut">
                <property name="title">Quit</property>
                <property name="accelerator">&lt;Primary&gt;q</property>
              </object>
            </child>
          </object>
        </child>
      </object>
    </child>
  </object>
</interface>"""


class MainWindow(Adw.ApplicationWindow):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.set_title("Aion-dl")
        self.set_icon_name(APP_ID)
        self.set_default_size(980, 680)
        self.set_size_request(640, 480)

        self._config = ConfigManager()
        self._jobs: list[DownloadJob] = []
        self._engine = DownloadEngine(self._config, self._on_job_update)
        self._settings_win = None  # lazily created, single instance

        self._build_ui()
        self._setup_actions()
        self._apply_theme()

    # ------------------------------------------------------------------
    # UI

    def _build_ui(self) -> None:
        self._toast_overlay = Adw.ToastOverlay()
        self.set_content(self._toast_overlay)

        toolbar_view = Adw.ToolbarView()
        self._toast_overlay.set_child(toolbar_view)

        # ── Header bar ───────────────────────────────────────────────────
        header = Adw.HeaderBar()
        header.add_css_class("flat")

        # ViewSwitcher in center of header (WIDE policy = horizontal tabs)
        self._view_stack = Adw.ViewStack()
        self._view_stack.set_hexpand(True)
        self._view_stack.set_vexpand(True)

        view_switcher = Adw.ViewSwitcher()
        view_switcher.set_stack(self._view_stack)
        view_switcher.set_policy(Adw.ViewSwitcherPolicy.WIDE)
        header.set_title_widget(view_switcher)

        # Right-side header buttons
        settings_btn = Gtk.Button(
            icon_name="preferences-system-symbolic",
            tooltip_text="Preferences (Ctrl+,)",
        )
        settings_btn.connect("clicked", lambda _: self._open_settings())
        header.pack_end(settings_btn)

        self._search_btn = Gtk.ToggleButton(
            icon_name="system-search-symbolic",
            tooltip_text="Search history (Ctrl+F)",
        )
        self._search_btn.set_sensitive(False)
        self._search_btn.connect("toggled", self._toggle_search)
        header.pack_end(self._search_btn)

        # Hamburger menu
        menu_model = Gio.Menu()
        s1 = Gio.Menu()
        s1.append("Add Batch File…",            "win.batch-file")
        s1.append("Check for yt-dlp Update",    "win.check-update")
        menu_model.append_section(None, s1)
        s2 = Gio.Menu()
        s2.append("Keyboard Shortcuts",         "app.shortcuts")
        s2.append("About Aion-dl",              "app.about")
        menu_model.append_section(None, s2)

        menu_btn = Gtk.MenuButton(
            icon_name="open-menu-symbolic",
            menu_model=menu_model,
            tooltip_text="Main Menu",
        )
        header.pack_end(menu_btn)

        toolbar_view.add_top_bar(header)

        # ── ViewStack pages ──────────────────────────────────────────────
        queue_page = self._build_queue_page()
        self._view_stack.add_titled_with_icon(
            queue_page, "queue", "Queue", "folder-download-symbolic"
        )

        self._history_page = HistoryPage(config=self._config)
        self._view_stack.add_titled_with_icon(
            self._history_page, "history", "History", "document-open-recent-symbolic"
        )

        # Connect page-switch to toggle search button sensitivity
        self._view_stack.connect("notify::visible-child", self._on_page_switched)

        # ── URL bar above stack ──────────────────────────────────────────
        self._url_bar = UrlBar(config=self._config, on_add=self._on_add_url)

        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        content_box.append(self._url_bar)
        content_box.append(Gtk.Separator())
        content_box.append(self._view_stack)

        # ── ViewSwitcherBar at bottom (shown when window is narrow) ──────
        switcher_bar = Adw.ViewSwitcherBar()
        switcher_bar.set_stack(self._view_stack)
        # Reveal bar automatically when the header switcher overflows
        # via a breakpoint (libadwaita 1.4+)
        try:
            bp = Adw.Breakpoint.new(
                Adw.BreakpointCondition.parse("max-width: 500sp")
            )
            bp.add_setter(view_switcher, "visible", False)
            bp.add_setter(switcher_bar, "reveal", True)
            self.add_breakpoint(bp)
        except Exception:
            # Older libadwaita: just show bar always but hide header switcher on narrow
            pass

        # ── Status bar ───────────────────────────────────────────────────
        status_bar = self._build_statusbar()

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        outer.append(content_box)
        outer.append(switcher_bar)
        outer.append(status_bar)

        toolbar_view.set_content(outer)

    def _build_queue_page(self) -> Gtk.Widget:
        scroll = Gtk.ScrolledWindow()
        scroll.set_hexpand(True)
        scroll.set_vexpand(True)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        self._job_list = Gtk.ListBox()
        self._job_list.add_css_class("boxed-list")
        self._job_list.set_margin_top(12)
        self._job_list.set_margin_bottom(12)
        self._job_list.set_margin_start(12)
        self._job_list.set_margin_end(12)
        self._job_list.set_selection_mode(Gtk.SelectionMode.NONE)
        self._job_list.set_placeholder(self._build_empty_state())
        scroll.set_child(self._job_list)
        return scroll

    @staticmethod
    def _build_empty_state() -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_valign(Gtk.Align.CENTER)
        box.set_halign(Gtk.Align.CENTER)
        box.set_margin_top(80)
        box.set_margin_bottom(80)

        icon = Gtk.Image.new_from_icon_name("folder-download-symbolic")
        icon.set_pixel_size(80)
        icon.add_css_class("dim-label")
        box.append(icon)

        title = Gtk.Label(label="No downloads yet")
        title.add_css_class("title-1")
        box.append(title)

        sub = Gtk.Label(label="Paste a URL above and press Add")
        sub.add_css_class("body")
        sub.add_css_class("dim-label")
        box.append(sub)
        return box

    def _build_statusbar(self) -> Gtk.ActionBar:
        bar = Gtk.ActionBar()

        self._status_label = Gtk.Label(label="Ready", xalign=0)
        self._status_label.add_css_class("caption")
        bar.pack_start(self._status_label)

        self._speed_label = Gtk.Label(label="")
        self._speed_label.add_css_class("caption")
        self._speed_label.add_css_class("dim-label")
        self._speed_label.set_margin_start(12)
        bar.pack_start(self._speed_label)

        self._eta_label = Gtk.Label(label="")
        self._eta_label.add_css_class("caption")
        self._eta_label.add_css_class("dim-label")
        self._eta_label.set_margin_start(8)
        bar.pack_start(self._eta_label)

        clear_btn = Gtk.Button(label="Clear Finished")
        clear_btn.add_css_class("flat")
        clear_btn.set_tooltip_text("Remove completed/failed/cancelled (Ctrl+Del)")
        clear_btn.connect("clicked", lambda _: self._clear_done())
        bar.pack_end(clear_btn)

        return bar

    # ------------------------------------------------------------------
    # Actions

    def _setup_actions(self) -> None:
        def add(name, cb):
            act = Gio.SimpleAction.new(name, None)
            act.connect("activate", lambda _a, _p: cb())
            self.add_action(act)

        add("settings",     self._open_settings)
        add("queue",        lambda: self._view_stack.set_visible_child_name("queue"))
        add("history",      lambda: self._view_stack.set_visible_child_name("history"))
        add("clear-done",   self._clear_done)
        add("search",       self._focus_search)
        add("focus-url",    self._focus_url)
        add("check-update", self._check_update)
        add("batch-file",   self._pick_batch_file)

        app = self.get_application()
        accels = {
            "win.settings":   ["<primary>comma"],
            "win.queue":      ["<primary>1"],
            "win.history":    ["<primary>2"],
            "win.clear-done": ["<primary>Delete"],
            "win.search":     ["<primary>f"],
            "win.focus-url":  ["<primary>l"],
        }
        for action, keys in accels.items():
            app.set_accels_for_action(action, keys)

        ctrl = Gtk.EventControllerKey()
        ctrl.connect("key-pressed", self._on_key)
        self.add_controller(ctrl)

    # ------------------------------------------------------------------
    # Page switching

    def _on_page_switched(self, stack, _param) -> None:
        name = stack.get_visible_child_name()
        is_history = name == "history"
        self._search_btn.set_sensitive(is_history)
        if not is_history:
            self._search_btn.set_active(False)

    def _toggle_search(self, btn: Gtk.ToggleButton) -> None:
        self._history_page.set_search_visible(btn.get_active())

    def _focus_search(self) -> None:
        self._view_stack.set_visible_child_name("history")
        self._search_btn.set_active(True)

    def _focus_url(self) -> None:
        self._url_bar.get_entry().grab_focus()

    def _on_key(self, _ctrl, keyval, _keycode, _state) -> bool:
        if keyval == Gdk.KEY_Escape:
            self._search_btn.set_active(False)
            return True
        return False

    # ------------------------------------------------------------------
    # Settings window

    def _open_settings(self) -> None:
        # Import here to avoid circular import at module level
        from .widgets.settings_page import SettingsWindow
        if self._settings_win is None:
            self._settings_win = SettingsWindow(
                config=self._config,
                on_change=self._on_settings_change,
                transient_for=self,
                modal=False,
            )
            self._settings_win.connect(
                "close-request",
                lambda _w: self._on_settings_closed(),
            )
        self._settings_win.present()

    def _on_settings_closed(self) -> bool:
        self._settings_win = None
        return False   # allow destroy

    # ------------------------------------------------------------------
    # Download management

    def _on_add_url(self, url: str, options: DownloadOptions) -> None:
        job = DownloadJob(url=url, options=options)
        self._jobs.append(job)

        row = DownloadRow(
            job=job,
            on_cancel=self._engine.cancel,
            on_open=self._open_file,
            on_retry=self._retry_job,
        )
        self._job_list.append(row)
        self._engine.submit(job)
        self._view_stack.set_visible_child_name("queue")
        self._update_statusbar()

    def _on_job_update(self, job: DownloadJob) -> bool:
        child = self._job_list.get_first_child()
        while child:
            if isinstance(child, DownloadRow) and child.job_id == job.job_id:
                child.update(job)
                break
            child = child.get_next_sibling()

        if job.state == JobState.DONE:
            self._config.append_history({
                "url":         job.url,
                "title":       job.title,
                "output_path": job.output_path,
                "format_note": job.format_note,
                "state":       "done",
                "timestamp":   time.strftime("%Y-%m-%d %H:%M"),
            })
            self._history_page.reload()
            if self._config.config.notify_on_complete:
                self._toast(f"Downloaded: {job.display_title[:60]}")
        elif job.state == JobState.FAILED:
            self._toast(f"Failed: {job.error_message[:80]}")

        self._update_statusbar()
        return False

    def _retry_job(self, job: DownloadJob) -> None:
        job.state = JobState.QUEUED
        job.progress = 0.0
        job.speed = ""
        job.eta = ""
        job.error_message = ""
        job.output_path = ""
        self._engine.submit(job)
        self._update_statusbar()

    def _open_file(self, path: str) -> None:
        if not path:
            return
        Gtk.FileLauncher.new(Gio.File.new_for_path(path)).launch(self, None, None)

    # ------------------------------------------------------------------
    # Batch file

    def _pick_batch_file(self) -> None:
        dlg = Gtk.FileDialog()
        dlg.set_title("Open Batch File — one URL per line")
        f_filter = Gtk.FileFilter()
        f_filter.add_mime_type("text/plain")
        f_filter.set_name("Text files")
        store = Gio.ListStore.new(Gtk.FileFilter)
        store.append(f_filter)
        dlg.set_filters(store)
        dlg.open(self, None, self._on_batch_chosen)

    def _on_batch_chosen(self, dlg, result) -> None:
        try:
            f = dlg.open_finish(result)
            if not f:
                return
            with open(f.get_path(), "r", encoding="utf-8", errors="replace") as fh:
                lines = fh.readlines()
            opts = DownloadOptions(
                output_dir=self._config.config.default_output_dir,
                output_template=self._config.config.output_template,
            )
            count = sum(
                1
                for line in lines
                if (url := line.strip()) and not url.startswith(("#", ";", "]"))
                and not self._on_add_url(url, opts)   # always None → counts all
            )
            self._toast(f"Added {count} URL{'s' if count != 1 else ''} from batch file")
        except Exception as exc:
            logger.error("Batch file error: %s", exc)
            self._toast(f"Batch file error: {exc}")

    # ------------------------------------------------------------------
    # Status bar

    def _update_statusbar(self) -> None:
        active  = [j for j in self._jobs if j.state in ACTIVE_STATES]
        queued  = [j for j in self._jobs if j.state == JobState.QUEUED]
        done    = [j for j in self._jobs if j.state == JobState.DONE]
        total   = len(self._jobs)

        if active:
            speeds = [j.speed for j in active if j.speed]
            etas   = [j.eta   for j in active if j.eta]
            n_act  = len(active)
            n_q    = len(queued)
            txt = f"{n_act} downloading"
            if n_q:
                txt += f" · {n_q} queued"
            self._status_label.set_label(txt)
            self._speed_label.set_label("  ".join(speeds[:2]))
            self._eta_label.set_label(f"ETA {etas[0]}" if etas else "")
        elif queued:
            self._status_label.set_label(f"{len(queued)} queued")
            self._speed_label.set_label("")
            self._eta_label.set_label("")
        elif total > 0:
            n_done  = len(done)
            n_other = total - n_done
            self._status_label.set_label(
                f"{n_done} completed" + (f" · {n_other} other" if n_other else "")
            )
            self._speed_label.set_label("")
            self._eta_label.set_label("")
        else:
            self._status_label.set_label("Ready")
            self._speed_label.set_label("")
            self._eta_label.set_label("")

    def _clear_done(self) -> None:
        child = self._job_list.get_first_child()
        to_remove = []
        while child:
            nxt = child.get_next_sibling()
            if isinstance(child, DownloadRow):
                job = next((j for j in self._jobs if j.job_id == child.job_id), None)
                if job and job.state in TERMINAL_STATES:
                    to_remove.append((child, job))
            child = nxt
        for widget, job in to_remove:
            self._job_list.remove(widget)
            self._jobs.remove(job)
            self._engine.remove(job.job_id)
        self._update_statusbar()

    # ------------------------------------------------------------------
    # Settings / theme

    def _on_settings_change(self) -> None:
        self._apply_theme()

    def _apply_theme(self) -> None:
        theme = self._config.config.theme
        mgr = Adw.StyleManager.get_default()
        mgr.set_color_scheme({
            "light":  Adw.ColorScheme.FORCE_LIGHT,
            "dark":   Adw.ColorScheme.FORCE_DARK,
        }.get(theme, Adw.ColorScheme.DEFAULT))

    # ------------------------------------------------------------------
    # yt-dlp update check

    def _check_update(self) -> None:
        import subprocess, shutil
        binary = self._config.config.ytdlp_binary
        if not shutil.which(binary):
            self._toast(f"yt-dlp binary not found: {binary}")
            return
        try:
            ver = subprocess.check_output(
                [binary, "--version"], text=True, timeout=5
            ).strip()
            self._toast(f"yt-dlp version: {ver}")
        except Exception as exc:
            self._toast(f"Update check failed: {exc}")

    # ------------------------------------------------------------------

    def _toast(self, msg: str, timeout: int = 4) -> None:
        self._toast_overlay.add_toast(Adw.Toast(title=msg, timeout=timeout))

    def do_close_request(self) -> bool:
        self._engine.shutdown()
        self._config.save()
        return False
