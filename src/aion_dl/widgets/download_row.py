"""
download_row.py - Per-job GtkListBoxRow widget showing progress, controls, etc.
"""

import os
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gio, GLib

from ..models import DownloadJob, JobState, STATE_ICON, STATE_CSS, TERMINAL_STATES


class DownloadRow(Gtk.ListBoxRow):
    """
    Displays a single DownloadJob:

      [status icon]  Title — Channel               [format badge]
                     [=========progress========]   speed  ETA
                     url / error / done path        [Cancel] [Open] [Retry]
    """

    def __init__(
        self,
        job: DownloadJob,
        on_cancel,
        on_open,
        on_retry,
    ) -> None:
        super().__init__()
        self.job_id: str = job.job_id
        self._on_cancel = on_cancel
        self._on_open = on_open
        self._on_retry = on_retry
        self._job = job
        self._build()
        self.update(job)

    # ------------------------------------------------------------------

    def _build(self) -> None:
        self.set_margin_top(4)
        self.set_margin_bottom(4)

        outer = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=12,
            margin_top=12,
            margin_bottom=12,
            margin_start=14,
            margin_end=14,
        )

        # Status icon
        self._state_icon = Gtk.Image.new_from_icon_name("task-due-symbolic")
        self._state_icon.set_pixel_size(22)
        self._state_icon.set_valign(Gtk.Align.START)
        self._state_icon.set_margin_top(2)
        outer.append(self._state_icon)

        # Main info column
        info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4, hexpand=True)

        # Row 1: title + format badge
        title_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self._title_label = Gtk.Label(xalign=0, hexpand=True, ellipsize=3)
        self._title_label.add_css_class("body")
        title_row.append(self._title_label)

        self._badge_label = Gtk.Label(label="")
        self._badge_label.add_css_class("tag")
        self._badge_label.add_css_class("caption")
        self._badge_label.set_valign(Gtk.Align.CENTER)
        title_row.append(self._badge_label)
        info.append(title_row)

        # Row 2: progress bar + speed + eta
        prog_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self._progress = Gtk.ProgressBar()
        self._progress.set_hexpand(True)
        self._progress.set_valign(Gtk.Align.CENTER)
        prog_row.append(self._progress)

        self._speed_label = Gtk.Label(label="")
        self._speed_label.add_css_class("caption")
        self._speed_label.add_css_class("dim-label")
        self._speed_label.set_width_chars(10)
        self._speed_label.set_xalign(1)
        prog_row.append(self._speed_label)

        self._eta_label = Gtk.Label(label="")
        self._eta_label.add_css_class("caption")
        self._eta_label.add_css_class("dim-label")
        self._eta_label.set_width_chars(8)
        prog_row.append(self._eta_label)
        info.append(prog_row)

        # Row 3: sub-label (URL / error / output path / playlist progress)
        self._sub_label = Gtk.Label(xalign=0, ellipsize=3)
        self._sub_label.add_css_class("caption")
        self._sub_label.add_css_class("dim-label")
        info.append(self._sub_label)

        # Row 4: action buttons
        btn_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

        self._cancel_btn = Gtk.Button(label="Cancel")
        self._cancel_btn.add_css_class("flat")
        self._cancel_btn.add_css_class("destructive-action")
        self._cancel_btn.connect("clicked", lambda _: self._on_cancel(self.job_id))

        self._open_btn = Gtk.Button(label="Open File")
        self._open_btn.add_css_class("flat")
        self._open_btn.connect("clicked", lambda _: self._on_open(self._job.output_path))

        self._open_dir_btn = Gtk.Button(icon_name="folder-open-symbolic")
        self._open_dir_btn.add_css_class("flat")
        self._open_dir_btn.set_tooltip_text("Open containing folder")
        self._open_dir_btn.connect("clicked", self._open_folder)

        self._retry_btn = Gtk.Button(label="Retry")
        self._retry_btn.add_css_class("flat")
        self._retry_btn.connect("clicked", lambda _: self._on_retry(self._job))

        self._copy_url_btn = Gtk.Button(icon_name="edit-copy-symbolic")
        self._copy_url_btn.add_css_class("flat")
        self._copy_url_btn.set_tooltip_text("Copy URL")
        self._copy_url_btn.connect("clicked", self._copy_url)

        for w in [self._cancel_btn, self._open_btn, self._open_dir_btn,
                  self._retry_btn, self._copy_url_btn]:
            btn_row.append(w)
        info.append(btn_row)

        outer.append(info)
        self.set_child(outer)

    # ------------------------------------------------------------------

    def update(self, job: DownloadJob) -> None:
        self._job = job

        # State icon + colour class
        icon_name = STATE_ICON.get(job.state, "task-due-symbolic")
        self._state_icon.set_from_icon_name(icon_name)
        for css_color in STATE_CSS.values():
            self._state_icon.remove_css_class(css_color)
        if job.state in STATE_CSS:
            self._state_icon.add_css_class(STATE_CSS[job.state])

        # Title
        self._title_label.set_label(job.display_title)
        self._title_label.set_tooltip_text(job.url)

        # Badge
        badge = self._build_badge(job)
        self._badge_label.set_label(badge)
        self._badge_label.set_visible(bool(badge))

        # Progress bar
        if job.state in (JobState.DOWNLOADING, JobState.POST_PROCESS):
            self._progress.set_visible(True)
            self._progress.set_fraction(job.progress)
            pct = f"{job.progress * 100:.1f}%"
            self._progress.set_text(pct)
            self._progress.set_show_text(True)
        elif job.state == JobState.FETCHING_INFO:
            self._progress.set_visible(True)
            self._progress.pulse()
            self._progress.set_text("Fetching info…")
            self._progress.set_show_text(True)
        elif job.state == JobState.DONE:
            self._progress.set_visible(True)
            self._progress.set_fraction(1.0)
            self._progress.set_text("Done")
            self._progress.set_show_text(True)
        else:
            self._progress.set_visible(job.state == JobState.QUEUED)
            self._progress.set_fraction(0)
            self._progress.set_text(job.state.name.replace("_", " ").title())
            self._progress.set_show_text(True)

        # Speed / ETA
        self._speed_label.set_label(job.speed or "")
        if job.eta:
            self._eta_label.set_label(f"ETA {job.eta}")
        else:
            self._eta_label.set_label("")

        # Sub-label
        if job.state == JobState.FAILED and job.error_message:
            self._sub_label.set_label(f"Error: {job.error_message}")
            self._sub_label.remove_css_class("dim-label")
            self._sub_label.add_css_class("error")
        elif job.state == JobState.DONE and job.output_path:
            self._sub_label.set_label(job.output_path)
            self._sub_label.add_css_class("dim-label")
            self._sub_label.remove_css_class("error")
        elif job.is_playlist and job.playlist_count:
            self._sub_label.set_label(
                f"Playlist: item {job.playlist_index}/{job.playlist_count}  ·  {job.short_url}"
            )
            self._sub_label.add_css_class("dim-label")
            self._sub_label.remove_css_class("error")
        elif job.state == JobState.QUEUED:
            self._sub_label.set_label(job.short_url)
            self._sub_label.add_css_class("dim-label")
            self._sub_label.remove_css_class("error")
        else:
            self._sub_label.set_label(job.short_url)
            self._sub_label.add_css_class("dim-label")
            self._sub_label.remove_css_class("error")

        # Button visibility
        is_terminal = job.is_terminal()
        is_done = job.state == JobState.DONE
        is_failed = job.state == JobState.FAILED

        self._cancel_btn.set_visible(job.is_active())
        self._open_btn.set_visible(is_done and bool(job.output_path))
        self._open_dir_btn.set_visible(is_done and bool(job.output_path))
        self._retry_btn.set_visible(is_failed or job.state == JobState.CANCELLED)
        self._copy_url_btn.set_visible(True)

    # ------------------------------------------------------------------

    def _build_badge(self, job: DownloadJob) -> str:
        opts = job.options
        if job.state == JobState.QUEUED:
            return "Queued"
        if job.state == JobState.FETCHING_INFO:
            return "Fetching…"
        if opts.download_type == "audio":
            return f"Audio · {opts.audio_format.upper()}"
        if opts.download_type == "video_only":
            return f"Video · {opts.quality}"
        q = opts.quality if opts.quality != "best" else "Best"
        container = opts.video_container.upper()
        return f"{container} · {q}"

    def _open_folder(self, *_args) -> None:
        path = self._job.output_path
        if not path:
            return
        folder = os.path.dirname(path)
        launcher = Gtk.FileLauncher.new(Gio.File.new_for_path(folder))
        launcher.launch(self.get_root(), None, None)

    def _copy_url(self, *_args) -> None:
        display = self.get_display()
        clipboard = display.get_clipboard()
        clipboard.set(self._job.url)
