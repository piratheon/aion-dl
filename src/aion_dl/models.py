"""
models.py - DownloadJob GObject and DownloadOptions dataclass.
"""

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional

import gi
gi.require_version("GObject", "2.0")
from gi.repository import GObject


class JobState(Enum):
    QUEUED         = auto()
    FETCHING_INFO  = auto()
    DOWNLOADING    = auto()
    POST_PROCESS   = auto()
    PAUSED         = auto()
    DONE           = auto()
    CANCELLED      = auto()
    FAILED         = auto()


STATE_ICON: dict[JobState, str] = {
    JobState.QUEUED:        "task-due-symbolic",
    JobState.FETCHING_INFO: "emblem-synchronizing-symbolic",
    JobState.DOWNLOADING:   "folder-download-symbolic",
    JobState.POST_PROCESS:  "media-playback-start-symbolic",
    JobState.PAUSED:        "media-playback-pause-symbolic",
    JobState.DONE:          "emblem-ok-symbolic",
    JobState.CANCELLED:     "process-stop-symbolic",
    JobState.FAILED:        "dialog-error-symbolic",
}

STATE_CSS: dict[JobState, str] = {
    JobState.DONE:      "success",
    JobState.FAILED:    "error",
    JobState.CANCELLED: "warning",
    JobState.PAUSED:    "accent",
}

ACTIVE_STATES = frozenset({
    JobState.QUEUED,
    JobState.FETCHING_INFO,
    JobState.DOWNLOADING,
    JobState.POST_PROCESS,
})

TERMINAL_STATES = frozenset({
    JobState.DONE,
    JobState.CANCELLED,
    JobState.FAILED,
})


@dataclass
class DownloadOptions:
    # Format / quality
    download_type: str = "video"
    quality: str = "best"
    video_container: str = "mp4"
    audio_format: str = "mp3"
    audio_quality: str = "5"
    format_code: str = ""
    merge_output_format: str = "mp4"
    remux_video: str = ""
    recode_video: str = ""
    prefer_free_formats: bool = False
    format_sort: str = ""

    # Subtitles
    write_subs: bool = False
    write_auto_subs: bool = False
    embed_subs: bool = False
    sub_format: str = "srt"
    sub_langs: str = "en"
    convert_subs: str = ""

    # Thumbnails
    write_thumbnail: bool = False
    embed_thumbnail: bool = False
    convert_thumbnails: str = ""

    # Metadata
    embed_metadata: bool = True
    embed_chapters: bool = False
    write_info_json: bool = False
    clean_info_json: bool = True
    write_description: bool = False
    write_comments: bool = False
    embed_info_json: bool = False
    xattrs: bool = False
    write_desktop_link: bool = False

    # SponsorBlock
    sponsorblock_mark: str = ""
    sponsorblock_remove: str = ""
    sponsorblock_api: str = "https://sponsor.ajay.app"

    # Playlist
    yes_playlist: bool = True
    playlist_items: str = ""
    playlist_random: bool = False
    lazy_playlist: bool = False
    max_downloads: int = 0
    break_on_existing: bool = False
    skip_playlist_after_errors: int = 0
    concat_playlist: str = "multi_video"
    live_from_start: bool = False
    wait_for_video: str = ""

    # Output
    output_dir: str = ""
    output_template: str = "%(title)s [%(id)s].%(ext)s"
    temp_path: str = ""
    restrict_filenames: bool = False
    windows_filenames: bool = False
    trim_filenames: int = 0
    no_overwrites: bool = False
    force_overwrites: bool = False
    download_archive: str = ""

    # Download sections / chapters
    download_sections: str = ""
    split_chapters: bool = False
    remove_chapters: str = ""
    force_keyframes_at_cuts: bool = False
    hls_use_mpegts: bool = False
    concurrent_fragments: int = 1

    # Video selection filters
    min_filesize: str = ""
    max_filesize: str = ""
    date: str = ""
    datebefore: str = ""
    dateafter: str = ""
    age_limit: int = 0
    match_filters: str = ""
    break_match_filters: str = ""

    # Post-processing
    keep_video: bool = False
    fixup: str = "detect_or_warn"
    exec_cmd: str = ""

    # Extra
    extra_args: str = ""


class DownloadJob(GObject.Object):
    __gtype_name__ = "YtDlpDownloadJob"

    def __init__(self, url: str, options: DownloadOptions) -> None:
        super().__init__()
        self.job_id: str = str(uuid.uuid4())
        self.url: str = url
        self.options: DownloadOptions = options

        self.title: str = url
        self.channel: str = ""
        self.thumbnail_url: str = ""
        self.duration: int = 0
        self.format_note: str = ""

        self.state: JobState = JobState.QUEUED
        self.progress: float = 0.0
        self.speed: str = ""
        self.eta: str = ""
        self.downloaded_bytes: int = 0
        self.total_bytes: int = 0
        self.error_message: str = ""
        self.output_path: str = ""

        self.is_playlist: bool = False
        self.playlist_count: int = 0
        self.playlist_index: int = 0

        self.start_time: float = 0.0
        self.end_time: float = 0.0
        self.process: Optional[object] = None

    @property
    def elapsed(self) -> float:
        if self.start_time == 0:
            return 0.0
        end = self.end_time if self.end_time else time.monotonic()
        return end - self.start_time

    @property
    def display_title(self) -> str:
        t = self.title
        return t if len(t) <= 90 else t[:87] + "…"

    @property
    def short_url(self) -> str:
        return self.url if len(self.url) <= 70 else self.url[:67] + "…"

    @property
    def playlist_label(self) -> str:
        if self.is_playlist and self.playlist_count:
            return f"Item {self.playlist_index}/{self.playlist_count}"
        return ""

    def is_active(self) -> bool:
        return self.state in ACTIVE_STATES

    def is_terminal(self) -> bool:
        return self.state in TERMINAL_STATES
