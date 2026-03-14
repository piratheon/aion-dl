"""
config.py - JSON-based persistent configuration with XDG paths.
"""

import json
import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

CONFIG_DIR  = Path.home() / ".config" / "aion-dl"
CONFIG_FILE = CONFIG_DIR / "config.json"
HISTORY_FILE = CONFIG_DIR / "history.json"

MAX_HISTORY = 1000


@dataclass
class AppConfig:
    # Network
    proxy: str = ""
    socket_timeout: int = 30
    source_address: str = ""
    impersonate: str = ""
    xff: str = "default"
    force_ipv4: bool = False
    force_ipv6: bool = False
    enable_file_urls: bool = False

    # Authentication
    cookies_file: str = ""
    cookies_from_browser: str = ""
    username: str = ""
    use_netrc: bool = False
    netrc_location: str = ""
    client_certificate: str = ""
    client_certificate_key: str = ""

    # Download
    concurrent_downloads: int = 3
    concurrent_fragments: int = 1
    limit_rate: str = ""
    throttled_rate: str = ""
    retries: int = 10
    fragment_retries: int = 10
    file_access_retries: int = 3
    retry_sleep: str = ""
    external_downloader: str = ""
    external_downloader_args: str = ""
    http_chunk_size: str = ""
    buffer_size: str = "1024"
    keep_fragments: bool = False

    # Filesystem
    default_output_dir: str = str(Path.home() / "Videos")
    output_template: str = "%(title)s [%(id)s].%(ext)s"
    restrict_filenames: bool = False
    windows_filenames: bool = False
    trim_filenames: int = 0
    no_overwrites: bool = False
    force_overwrites: bool = False
    use_part_files: bool = True
    set_mtime: bool = False
    cache_dir: str = ""
    no_cache_dir: bool = False

    # Post-processing
    ffmpeg_location: str = ""
    keep_video: bool = False
    fixup: str = "detect_or_warn"
    postprocessor_args: str = ""

    # Sleep / rate-limiting (anti-throttle)
    sleep_requests: float = 0.0
    sleep_interval: float = 0.0
    max_sleep_interval: float = 0.0
    sleep_subtitles: float = 0.0

    # Workarounds
    no_check_certificates: bool = False
    prefer_insecure: bool = False
    legacy_server_connect: bool = False
    add_headers: list = field(default_factory=list)
    bidi_workaround: bool = False

    # Extractor
    extractor_retries: int = 3
    allow_dynamic_mpd: bool = True
    hls_split_discontinuity: bool = False
    extractor_args: str = ""

    # Geo-restriction
    geo_verification_proxy: str = ""

    # Application
    theme: str = "system"
    notify_on_complete: bool = True
    show_speed_in_statusbar: bool = True
    max_history_entries: int = MAX_HISTORY
    ytdlp_binary: str = "yt-dlp"
    check_for_updates: bool = True
    js_runtimes: str = ""


class ConfigManager:
    def __init__(self) -> None:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        self._config = self._load()

    # ------------------------------------------------------------------
    def _load(self) -> AppConfig:
        if CONFIG_FILE.exists():
            try:
                raw: dict[str, Any] = json.loads(CONFIG_FILE.read_text("utf-8"))
                cfg = AppConfig()
                for key, val in raw.items():
                    if hasattr(cfg, key):
                        setattr(cfg, key, val)
                return cfg
            except (json.JSONDecodeError, OSError) as exc:
                logger.error("Config load failed: %s — using defaults", exc)
        return AppConfig()

    def save(self) -> None:
        try:
            CONFIG_FILE.write_text(
                json.dumps(asdict(self._config), indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except OSError as exc:
            logger.error("Config save failed: %s", exc)

    # ------------------------------------------------------------------
    @property
    def config(self) -> AppConfig:
        return self._config

    def set(self, key: str, value: Any) -> None:
        if not hasattr(self._config, key):
            raise KeyError(f"Unknown config key: {key!r}")
        setattr(self._config, key, value)
        self.save()

    # ------------------------------------------------------------------
    def load_history(self) -> list[dict]:
        if HISTORY_FILE.exists():
            try:
                return json.loads(HISTORY_FILE.read_text("utf-8"))
            except (json.JSONDecodeError, OSError):
                pass
        return []

    def append_history(self, entry: dict) -> None:
        history = self.load_history()
        # Deduplicate by url — keep newest on top
        history = [h for h in history if h.get("url") != entry.get("url")]
        history.insert(0, entry)
        history = history[: self._config.max_history_entries]
        try:
            HISTORY_FILE.write_text(
                json.dumps(history, indent=2, ensure_ascii=False), encoding="utf-8"
            )
        except OSError as exc:
            logger.error("History save failed: %s", exc)

    def clear_history(self) -> None:
        try:
            HISTORY_FILE.write_text("[]", encoding="utf-8")
        except OSError as exc:
            logger.error("History clear failed: %s", exc)
