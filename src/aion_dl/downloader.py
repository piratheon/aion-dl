"""
downloader.py - yt-dlp subprocess engine with threaded execution.

Each DownloadJob runs inside a ThreadPoolExecutor worker. Progress is
parsed from yt-dlp --newline output and marshalled back to the GTK
main loop via GLib.idle_add so UI updates are always thread-safe.
"""

import logging
import re
import shlex
import shutil
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Callable, Optional

import gi
gi.require_version("GLib", "2.0")
from gi.repository import GLib

from .config import AppConfig, ConfigManager
from .models import DownloadJob, DownloadOptions, JobState

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Output parsing regexes
# ---------------------------------------------------------------------------

_RE_PROGRESS = re.compile(
    r"\[download\]\s+(?P<pct>[\d.]+)%\s+of\s+~?\s*(?P<size>[\d.]+\s*\w+)"
    r"(?:\s+at\s+(?P<speed>[\d.]+\s*\w+/s))?(?:\s+ETA\s+(?P<eta>[\d:]+))?",
    re.IGNORECASE,
)
_RE_DEST = re.compile(
    r"\[(?:download|Merger|ffmpeg)\]\s+"
    r"(?:Destination|Merging formats into|Correcting container):\s+(.+)"
)
_RE_ALREADY = re.compile(r"\[download\]\s+(.+?)\s+has already been downloaded")
_RE_PLAYLIST = re.compile(r"\[download\]\s+Downloading item (\d+) of (\d+)")
_RE_POSTPROC = re.compile(
    r"\[(?:ffmpeg|ExtractAudio|EmbedThumbnail|Merger|SponsorBlock"
    r"|ModifyChapters|SplitChapters|VideoRemuxer|VideoConvertor)\]"
)
_RE_ERROR = re.compile(r"^ERROR:\s+(.+)", re.MULTILINE)
_RE_WARNING = re.compile(r"^WARNING:\s+(.+)", re.MULTILINE)
_RE_TITLE = re.compile(r"\[(?:info|youtube|generic)\]\s+(\S+?):\s+Downloading")


# ---------------------------------------------------------------------------
# Command builder
# ---------------------------------------------------------------------------

def build_command(job: DownloadJob, cfg: AppConfig) -> list[str]:  # noqa: C901
    opts: DownloadOptions = job.options
    cmd: list[str] = [
        cfg.ytdlp_binary,
        "--newline",
        "--progress",
        "--no-color",
        "--ignore-errors",
    ]

    # ---- Format selection --------------------------------------------------
    if opts.format_code:
        cmd += ["-f", opts.format_code]
    elif opts.download_type == "audio":
        cmd += [
            "-x",
            "--audio-format", opts.audio_format,
            "--audio-quality", opts.audio_quality,
        ]
    elif opts.download_type == "video_only":
        q_map = {
            "best": "bestvideo",
            "2160": "bestvideo[height<=2160]",
            "1080": "bestvideo[height<=1080]",
            "720":  "bestvideo[height<=720]",
            "480":  "bestvideo[height<=480]",
            "360":  "bestvideo[height<=360]",
            "worst": "worstvideo",
        }
        cmd += ["-f", q_map.get(opts.quality, "bestvideo")]
    else:
        q_map = {
            "best": "bestvideo+bestaudio/best",
            "2160": "bestvideo[height<=2160]+bestaudio/best[height<=2160]",
            "1080": "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
            "720":  "bestvideo[height<=720]+bestaudio/best[height<=720]",
            "480":  "bestvideo[height<=480]+bestaudio/best[height<=480]",
            "360":  "bestvideo[height<=360]+bestaudio/best[height<=360]",
            "worst": "worstvideo+worstaudio/worst",
        }
        cmd += ["-f", q_map.get(opts.quality, "bestvideo+bestaudio/best")]

    if opts.download_type != "audio":
        if opts.merge_output_format:
            cmd += ["--merge-output-format", opts.merge_output_format]
        if opts.remux_video:
            cmd += ["--remux-video", opts.remux_video]
        if opts.recode_video:
            cmd += ["--recode-video", opts.recode_video]
    if opts.prefer_free_formats:
        cmd.append("--prefer-free-formats")
    if opts.format_sort:
        cmd += ["-S", opts.format_sort]

    # ---- Subtitles ---------------------------------------------------------
    if opts.write_subs:
        cmd.append("--write-subs")
        if opts.sub_format:
            cmd += ["--sub-format", opts.sub_format]
        if opts.sub_langs:
            cmd += ["--sub-langs", opts.sub_langs]
    if opts.write_auto_subs:
        cmd.append("--write-auto-subs")
    if opts.embed_subs:
        cmd.append("--embed-subs")
    if opts.convert_subs:
        cmd += ["--convert-subs", opts.convert_subs]

    # ---- Thumbnails --------------------------------------------------------
    if opts.write_thumbnail:
        cmd.append("--write-thumbnail")
    if opts.embed_thumbnail:
        cmd.append("--embed-thumbnail")
    if opts.convert_thumbnails:
        cmd += ["--convert-thumbnails", opts.convert_thumbnails]

    # ---- Metadata ----------------------------------------------------------
    if opts.embed_metadata:
        cmd.append("--embed-metadata")
    if opts.embed_chapters:
        cmd.append("--embed-chapters")
    if opts.write_info_json:
        cmd.append("--write-info-json")
        if opts.clean_info_json:
            cmd.append("--clean-info-json")
    if opts.write_description:
        cmd.append("--write-description")
    if opts.write_comments:
        cmd.append("--write-comments")
    if opts.embed_info_json:
        cmd.append("--embed-info-json")
    if opts.xattrs:
        cmd.append("--xattrs")
    if opts.write_desktop_link:
        cmd.append("--write-desktop-link")

    # ---- SponsorBlock ------------------------------------------------------
    if opts.sponsorblock_mark:
        cmd += ["--sponsorblock-mark", opts.sponsorblock_mark]
    if opts.sponsorblock_remove:
        cmd += ["--sponsorblock-remove", opts.sponsorblock_remove]
    if opts.sponsorblock_api and opts.sponsorblock_api != "https://sponsor.ajay.app":
        cmd += ["--sponsorblock-api", opts.sponsorblock_api]

    # ---- Playlist ----------------------------------------------------------
    if opts.yes_playlist:
        cmd.append("--yes-playlist")
    else:
        cmd.append("--no-playlist")
    if opts.playlist_items:
        cmd += ["-I", opts.playlist_items]
    if opts.playlist_random:
        cmd.append("--playlist-random")
    if opts.lazy_playlist:
        cmd.append("--lazy-playlist")
    if opts.max_downloads > 0:
        cmd += ["--max-downloads", str(opts.max_downloads)]
    if opts.break_on_existing:
        cmd.append("--break-on-existing")
    if opts.skip_playlist_after_errors > 0:
        cmd += ["--skip-playlist-after-errors", str(opts.skip_playlist_after_errors)]
    if opts.concat_playlist and opts.concat_playlist != "multi_video":
        cmd += ["--concat-playlist", opts.concat_playlist]
    if opts.live_from_start:
        cmd.append("--live-from-start")
    if opts.wait_for_video:
        cmd += ["--wait-for-video", opts.wait_for_video]

    # ---- Output / filesystem -----------------------------------------------
    out_dir = opts.output_dir or cfg.default_output_dir
    template = opts.output_template or cfg.output_template
    output_path = str(Path(out_dir) / template)
    cmd += ["-o", output_path]

    if opts.temp_path:
        cmd += ["-P", f"temp:{opts.temp_path}"]
    if opts.restrict_filenames:
        cmd.append("--restrict-filenames")
    if opts.windows_filenames:
        cmd.append("--windows-filenames")
    if opts.trim_filenames > 0:
        cmd += ["--trim-filenames", str(opts.trim_filenames)]
    if opts.no_overwrites:
        cmd.append("--no-overwrites")
    elif opts.force_overwrites:
        cmd.append("--force-overwrites")
    if opts.download_archive:
        cmd += ["--download-archive", opts.download_archive]

    # ---- Download sections / chapters --------------------------------------
    for sec in opts.download_sections.splitlines():
        if sec.strip():
            cmd += ["--download-sections", sec.strip()]
    if opts.split_chapters:
        cmd.append("--split-chapters")
    if opts.remove_chapters:
        cmd += ["--remove-chapters", opts.remove_chapters]
    if opts.force_keyframes_at_cuts:
        cmd.append("--force-keyframes-at-cuts")
    if opts.hls_use_mpegts:
        cmd.append("--hls-use-mpegts")
    if opts.concurrent_fragments > 1:
        cmd += ["-N", str(opts.concurrent_fragments)]

    # ---- Video selection filters -------------------------------------------
    if opts.min_filesize:
        cmd += ["--min-filesize", opts.min_filesize]
    if opts.max_filesize:
        cmd += ["--max-filesize", opts.max_filesize]
    if opts.date:
        cmd += ["--date", opts.date]
    if opts.datebefore:
        cmd += ["--datebefore", opts.datebefore]
    if opts.dateafter:
        cmd += ["--dateafter", opts.dateafter]
    if opts.age_limit > 0:
        cmd += ["--age-limit", str(opts.age_limit)]
    if opts.match_filters:
        cmd += ["--match-filters", opts.match_filters]
    if opts.break_match_filters:
        cmd += ["--break-match-filters", opts.break_match_filters]

    # ---- Post-processing ---------------------------------------------------
    if opts.keep_video:
        cmd.append("--keep-video")
    if opts.fixup and opts.fixup != "detect_or_warn":
        cmd += ["--fixup", opts.fixup]
    if opts.exec_cmd:
        cmd += ["--exec", opts.exec_cmd]

    # ==== Global config options ============================================

    # Network
    if cfg.proxy:
        cmd += ["--proxy", cfg.proxy]
    if cfg.socket_timeout != 30:
        cmd += ["--socket-timeout", str(cfg.socket_timeout)]
    if cfg.source_address:
        cmd += ["--source-address", cfg.source_address]
    if cfg.impersonate:
        cmd += ["--impersonate", cfg.impersonate]
    if cfg.xff and cfg.xff != "default":
        cmd += ["--xff", cfg.xff]
    if cfg.force_ipv4:
        cmd.append("--force-ipv4")
    elif cfg.force_ipv6:
        cmd.append("--force-ipv6")
    if cfg.geo_verification_proxy:
        cmd += ["--geo-verification-proxy", cfg.geo_verification_proxy]

    # Auth
    if cfg.cookies_file:
        cmd += ["--cookies", cfg.cookies_file]
    if cfg.cookies_from_browser:
        cmd += ["--cookies-from-browser", cfg.cookies_from_browser]
    if cfg.username:
        cmd += ["--username", cfg.username]
    if cfg.use_netrc:
        cmd.append("--netrc")
    if cfg.netrc_location:
        cmd += ["--netrc-location", cfg.netrc_location]
    if cfg.client_certificate:
        cmd += ["--client-certificate", cfg.client_certificate]
    if cfg.client_certificate_key:
        cmd += ["--client-certificate-key", cfg.client_certificate_key]

    # Download
    if cfg.concurrent_fragments > 1:
        cmd += ["-N", str(cfg.concurrent_fragments)]
    if cfg.limit_rate:
        cmd += ["-r", cfg.limit_rate]
    if cfg.throttled_rate:
        cmd += ["--throttled-rate", cfg.throttled_rate]
    if cfg.retries != 10:
        cmd += ["-R", str(cfg.retries)]
    if cfg.fragment_retries != 10:
        cmd += ["--fragment-retries", str(cfg.fragment_retries)]
    if cfg.file_access_retries != 3:
        cmd += ["--file-access-retries", str(cfg.file_access_retries)]
    if cfg.retry_sleep:
        cmd += ["--retry-sleep", cfg.retry_sleep]
    if cfg.external_downloader:
        cmd += ["--downloader", cfg.external_downloader]
        if cfg.external_downloader_args:
            cmd += ["--downloader-args", cfg.external_downloader_args]
    if cfg.http_chunk_size:
        cmd += ["--http-chunk-size", cfg.http_chunk_size]
    if cfg.buffer_size and cfg.buffer_size != "1024":
        cmd += ["--buffer-size", cfg.buffer_size]
    if cfg.keep_fragments:
        cmd.append("--keep-fragments")

    # Filesystem
    if not cfg.use_part_files:
        cmd.append("--no-part")
    if cfg.set_mtime:
        cmd.append("--mtime")
    if cfg.no_cache_dir:
        cmd.append("--no-cache-dir")
    elif cfg.cache_dir:
        cmd += ["--cache-dir", cfg.cache_dir]

    # Post-processing
    if cfg.ffmpeg_location:
        cmd += ["--ffmpeg-location", cfg.ffmpeg_location]
    if cfg.keep_video:
        cmd.append("--keep-video")
    if cfg.fixup and cfg.fixup != "detect_or_warn":
        cmd += ["--fixup", cfg.fixup]
    if cfg.postprocessor_args:
        cmd += ["--postprocessor-args", cfg.postprocessor_args]

    # Sleep
    if cfg.sleep_requests > 0:
        cmd += ["--sleep-requests", str(cfg.sleep_requests)]
    if cfg.sleep_interval > 0:
        cmd += ["--sleep-interval", str(cfg.sleep_interval)]
        if cfg.max_sleep_interval > cfg.sleep_interval:
            cmd += ["--max-sleep-interval", str(cfg.max_sleep_interval)]
    if cfg.sleep_subtitles > 0:
        cmd += ["--sleep-subtitles", str(cfg.sleep_subtitles)]

    # Workarounds
    if cfg.no_check_certificates:
        cmd.append("--no-check-certificates")
    if cfg.prefer_insecure:
        cmd.append("--prefer-insecure")
    if cfg.legacy_server_connect:
        cmd.append("--legacy-server-connect")
    for header in cfg.add_headers:
        cmd += ["--add-headers", header]
    if cfg.bidi_workaround:
        cmd.append("--bidi-workaround")

    # Extractor
    if cfg.extractor_retries != 3:
        cmd += ["--extractor-retries", str(cfg.extractor_retries)]
    if not cfg.allow_dynamic_mpd:
        cmd.append("--ignore-dynamic-mpd")
    if cfg.hls_split_discontinuity:
        cmd.append("--hls-split-discontinuity")
    if cfg.extractor_args:
        cmd += ["--extractor-args", cfg.extractor_args]

    # JS runtimes
    if cfg.js_runtimes:
        for rt in cfg.js_runtimes.split(","):
            rt = rt.strip()
            if rt:
                cmd += ["--js-runtimes", rt]

    # Extra user args (job-level)
    if opts.extra_args:
        try:
            cmd += shlex.split(opts.extra_args)
        except ValueError as exc:
            logger.warning("Invalid extra_args: %s", exc)

    cmd.append(job.url)
    return cmd


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class DownloadEngine:
    """
    Thread-pool based download engine.

    Runs one yt-dlp subprocess per job inside a ThreadPoolExecutor.
    All UI callbacks are posted via GLib.idle_add to ensure they run
    on the GTK main thread.
    """

    def __init__(
        self,
        config_manager: ConfigManager,
        on_job_update: Callable[[DownloadJob], None],
    ) -> None:
        self._config = config_manager
        self._on_job_update = on_job_update
        self._jobs: dict[str, DownloadJob] = {}
        self._lock = threading.Lock()
        self._executor: Optional[ThreadPoolExecutor] = None
        self._rebuild_executor()

    # ------------------------------------------------------------------

    def _rebuild_executor(self) -> None:
        n = max(1, self._config.config.concurrent_downloads)
        if self._executor:
            self._executor.shutdown(wait=False, cancel_futures=False)
        self._executor = ThreadPoolExecutor(
            max_workers=n, thread_name_prefix="ytdlp"
        )

    def submit(self, job: DownloadJob) -> None:
        with self._lock:
            self._jobs[job.job_id] = job
        job.state = JobState.QUEUED
        self._notify(job)
        self._executor.submit(self._run_job, job)

    def cancel(self, job_id: str) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
        if job is None:
            return
        if job.process:
            try:
                job.process.terminate()
            except (ProcessLookupError, OSError):
                pass
        job.state = JobState.CANCELLED
        self._notify(job)

    def remove(self, job_id: str) -> None:
        with self._lock:
            self._jobs.pop(job_id, None)

    def shutdown(self) -> None:
        with self._lock:
            jobs = list(self._jobs.values())
        for job in jobs:
            if job.is_active():
                self.cancel(job.job_id)
        if self._executor:
            self._executor.shutdown(wait=True, cancel_futures=True)

    # ------------------------------------------------------------------

    def _run_job(self, job: DownloadJob) -> None:
        cfg = self._config.config
        try:
            binary = cfg.ytdlp_binary
            if not shutil.which(binary):
                job.state = JobState.FAILED
                job.error_message = (
                    f"yt-dlp binary not found: '{binary}'. "
                    "Install it with: pip install yt-dlp"
                )
                self._notify(job)
                return

            job.state = JobState.FETCHING_INFO
            job.start_time = time.monotonic()
            self._notify(job)

            cmd = build_command(job, cfg)
            logger.info("Launching: %s", " ".join(cmd))

            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                encoding="utf-8",
                errors="replace",
            )
            job.process = proc

            for raw_line in proc.stdout:
                line = raw_line.rstrip()
                if not line:
                    continue
                logger.debug("[yt-dlp] %s", line)
                self._parse_line(job, line)
                self._notify(job)
                if job.state == JobState.CANCELLED:
                    proc.terminate()
                    break

            proc.wait(timeout=5)

            if job.state == JobState.CANCELLED:
                return

            if proc.returncode == 0:
                job.state = JobState.DONE
                job.progress = 1.0
                job.end_time = time.monotonic()
            else:
                if not job.error_message:
                    job.error_message = f"yt-dlp exited with code {proc.returncode}"
                job.state = JobState.FAILED

        except subprocess.TimeoutExpired:
            job.state = JobState.FAILED
            job.error_message = "Process did not terminate in time after cancel"
        except Exception as exc:
            logger.exception("Unexpected error in job %s", job.job_id)
            job.state = JobState.FAILED
            job.error_message = str(exc)
        finally:
            job.process = None
            self._notify(job)

    def _parse_line(self, job: DownloadJob, line: str) -> None:
        # Download progress
        m = _RE_PROGRESS.search(line)
        if m:
            job.state = JobState.DOWNLOADING
            pct = float(m.group("pct"))
            job.progress = min(pct / 100.0, 1.0)
            if m.group("speed"):
                job.speed = m.group("speed").strip()
            if m.group("eta"):
                job.eta = m.group("eta")
            return

        # Post-processing marker
        if _RE_POSTPROC.search(line):
            if job.state == JobState.DOWNLOADING:
                job.state = JobState.POST_PROCESS
                job.progress = 1.0
            return

        # Output path
        m = _RE_DEST.search(line)
        if m:
            job.output_path = m.group(1).strip()
            return

        # Already downloaded
        m = _RE_ALREADY.search(line)
        if m:
            job.output_path = m.group(1).strip()
            job.state = JobState.DONE
            job.progress = 1.0
            return

        # Playlist tracking
        m = _RE_PLAYLIST.search(line)
        if m:
            job.is_playlist = True
            job.playlist_index = int(m.group(1))
            job.playlist_count = int(m.group(2))
            return

        # Errors
        m = _RE_ERROR.search(line)
        if m:
            job.error_message = m.group(1).strip()[:200]
            return

        # Title extraction from [info] lines
        if "[info]" in line and ":" in line:
            m = _RE_TITLE.search(line)
            if m and job.title == job.url:
                # Title arrives later via a dedicated info line; this is the ID
                pass

        # Detect title from "Downloading webpage" style lines
        if "Title:" in line:
            title_part = line.split("Title:", 1)[-1].strip()
            if title_part:
                job.title = title_part[:120]

    def _notify(self, job: DownloadJob) -> None:
        GLib.idle_add(self._on_job_update, job)
