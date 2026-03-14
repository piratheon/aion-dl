"""
settings_page.py - Adw.PreferencesWindow with one page per category.

Each category maps to an Adw.PreferencesPage with its own icon,
displayed in the window's built-in ViewSwitcher sidebar.

Open with: SettingsWindow(config, on_change, transient_for=parent).present()
"""

from pathlib import Path
from typing import Callable

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gio

from ..config import AppConfig, ConfigManager


class SettingsWindow(Adw.PreferencesWindow):
    """
    Full settings window.

    Adw.PreferencesWindow provides:
      - Built-in ViewSwitcher showing all pages in a sidebar / top bar
      - Search across all preference rows
      - Back navigation on narrow displays
    """

    def __init__(self, config: ConfigManager, on_change: Callable, **kwargs) -> None:
        super().__init__(**kwargs)
        self.set_title("Preferences")
        self.set_default_size(780, 680)
        self.set_search_enabled(True)
        self._config = config
        self._on_change = on_change
        self._build_pages()

    # ------------------------------------------------------------------
    # Pages

    def _build_pages(self) -> None:
        cfg = self._config.config

        self._add_general_page(cfg)
        self._add_output_page(cfg)
        self._add_network_page(cfg)
        self._add_auth_page(cfg)
        self._add_download_page(cfg)
        self._add_postprocessing_page(cfg)
        self._add_sleep_page(cfg)
        self._add_workarounds_page(cfg)
        self._add_extractor_page(cfg)

    # ── General ──────────────────────────────────────────────────────────

    def _add_general_page(self, cfg: AppConfig) -> None:
        page = Adw.PreferencesPage(
            title="General",
            icon_name="preferences-system-symbolic",
        )
        self.add(page)

        # Application group
        app_grp = Adw.PreferencesGroup(title="Application")
        page.add(app_grp)

        self._ytdlp_bin = self._erow(
            app_grp, "yt-dlp Binary", cfg.ytdlp_binary,
            "Path or command name, e.g. yt-dlp  or  /usr/local/bin/yt-dlp",
            "ytdlp_binary",
        )
        self._theme_combo = self._combo(
            app_grp, "Theme",
            ["System Default", "Light", "Dark"],
            ["system", "light", "dark"].index(cfg.theme),
            "theme", ["system", "light", "dark"],
        )
        self._notify_sw = self._sw(
            app_grp, "Notify on Completion",
            "Show an in-app toast when a download finishes",
            cfg.notify_on_complete, "notify_on_complete",
        )
        self._show_speed_sw = self._sw(
            app_grp, "Show Speed in Status Bar",
            "Display live download speed in the bottom bar",
            cfg.show_speed_in_statusbar, "show_speed_in_statusbar",
        )

        # Concurrency group
        conc_grp = Adw.PreferencesGroup(title="Concurrency")
        page.add(conc_grp)

        self._concurrent_spin = self._spin(
            conc_grp, "Concurrent Downloads",
            "Maximum number of simultaneous download jobs",
            cfg.concurrent_downloads, 1, 16, "concurrent_downloads",
        )
        self._maxhist_spin = self._spin(
            conc_grp, "Max History Entries",
            "Entries beyond this limit are dropped from history",
            cfg.max_history_entries, 10, 5000, "max_history_entries",
        )

    # ── Output ───────────────────────────────────────────────────────────

    def _add_output_page(self, cfg: AppConfig) -> None:
        page = Adw.PreferencesPage(
            title="Output",
            icon_name="folder-download-symbolic",
        )
        self.add(page)

        paths_grp = Adw.PreferencesGroup(title="Paths")
        page.add(paths_grp)

        # Output directory — custom row with file picker button
        self._outdir_row = Adw.ActionRow(
            title="Default Output Directory",
            subtitle=cfg.default_output_dir or str(Path.home() / "Videos"),
        )
        outdir_btn = Gtk.Button(icon_name="folder-open-symbolic")
        outdir_btn.add_css_class("flat")
        outdir_btn.set_valign(Gtk.Align.CENTER)
        outdir_btn.set_tooltip_text("Choose directory")
        outdir_btn.connect("clicked", self._pick_outdir)
        self._outdir_row.add_suffix(outdir_btn)
        paths_grp.add(self._outdir_row)

        self._tmpl_entry = self._erow(
            paths_grp, "Default Filename Template",
            cfg.output_template,
            "%(title)s [%(id)s].%(ext)s — all OUTPUT TEMPLATE fields supported",
            "output_template",
        )
        self._cache_entry = self._erow(
            paths_grp, "Cache Directory",
            cfg.cache_dir,
            "Default: ${XDG_CACHE_HOME}/yt-dlp",
            "cache_dir",
        )

        files_grp = Adw.PreferencesGroup(title="File Handling")
        page.add(files_grp)

        self._restrict_sw = self._sw(
            files_grp, "Restrict Filenames",
            "ASCII only — no &amp; or spaces",
            cfg.restrict_filenames, "restrict_filenames",
        )
        self._winfiles_sw = self._sw(
            files_grp, "Windows-Compatible Filenames",
            "--windows-filenames",
            cfg.windows_filenames, "windows_filenames",
        )
        self._nowrt_sw = self._sw(
            files_grp, "No Overwrites",
            "--no-overwrites: skip if file exists",
            cfg.no_overwrites, "no_overwrites",
        )
        self._part_sw = self._sw(
            files_grp, "Use .part Files",
            "Write to .part while in progress (safer on crash)",
            cfg.use_part_files, "use_part_files",
        )
        self._mtime_sw = self._sw(
            files_grp, "Set File Modification Time",
            "--mtime: use Last-Modified HTTP header",
            cfg.set_mtime, "set_mtime",
        )
        self._nocache_sw = self._sw(
            files_grp, "Disable Cache",
            "--no-cache-dir",
            cfg.no_cache_dir, "no_cache_dir",
        )

    # ── Network ───────────────────────────────────────────────────────────

    def _add_network_page(self, cfg: AppConfig) -> None:
        page = Adw.PreferencesPage(
            title="Network",
            icon_name="network-wired-symbolic",
        )
        self.add(page)

        proxy_grp = Adw.PreferencesGroup(title="Proxy &amp; Routing")
        page.add(proxy_grp)

        self._proxy_entry = self._erow(
            proxy_grp, "HTTP / SOCKS Proxy",
            cfg.proxy,
            "socks5://127.0.0.1:1080  or  http://proxy:3128  (empty = direct)",
            "proxy",
        )
        self._geo_proxy_entry = self._erow(
            proxy_grp, "Geo Verification Proxy",
            cfg.geo_verification_proxy,
            "--geo-verification-proxy URL",
            "geo_verification_proxy",
        )
        self._xff_entry = self._erow(
            proxy_grp, "X-Forwarded-For (--xff)",
            cfg.xff,
            "default | never | CIDR block | ISO-3166-2 country code",
            "xff",
        )
        self._ipv4_sw = self._sw(
            proxy_grp, "Force IPv4", "--force-ipv4",
            cfg.force_ipv4, "force_ipv4",
        )
        self._ipv6_sw = self._sw(
            proxy_grp, "Force IPv6", "--force-ipv6",
            cfg.force_ipv6, "force_ipv6",
        )

        conn_grp = Adw.PreferencesGroup(title="Connection")
        page.add(conn_grp)

        self._timeout_spin = self._spin(
            conn_grp, "Socket Timeout",
            "Seconds before giving up on a connection",
            cfg.socket_timeout, 5, 300, "socket_timeout",
        )
        self._srcaddr_entry = self._erow(
            conn_grp, "Source Address",
            cfg.source_address,
            "Client-side IP to bind to (--source-address)",
            "source_address",
        )
        self._impersonate_entry = self._erow(
            conn_grp, "Impersonate Client",
            cfg.impersonate,
            "e.g. chrome, chrome-110, chrome:windows-10",
            "impersonate",
        )

    # ── Authentication ────────────────────────────────────────────────────

    def _add_auth_page(self, cfg: AppConfig) -> None:
        page = Adw.PreferencesPage(
            title="Authentication",
            icon_name="dialog-password-symbolic",
        )
        self.add(page)

        cookies_grp = Adw.PreferencesGroup(title="Cookies")
        page.add(cookies_grp)

        self._cookies_entry = self._erow(
            cookies_grp, "Cookies File",
            cfg.cookies_file,
            "Netscape cookies.txt file path",
            "cookies_file",
            file_pick=True,
        )
        browsers = [
            "(none)", "brave", "chrome", "chromium",
            "edge", "firefox", "opera", "safari", "vivaldi", "whale",
        ]
        bidx = browsers.index(cfg.cookies_from_browser) \
               if cfg.cookies_from_browser in browsers else 0
        self._browser_combo = self._combo(
            cookies_grp, "Cookies From Browser",
            browsers, bidx,
            "cookies_from_browser", browsers,
        )

        creds_grp = Adw.PreferencesGroup(title="Credentials")
        page.add(creds_grp)

        self._user_entry = self._erow(
            creds_grp, "Username (-u)",
            cfg.username,
            "Account login ID",
            "username",
        )
        self._netrc_sw = self._sw(
            creds_grp, "Use .netrc (-n)",
            "Read credentials from ~/.netrc",
            cfg.use_netrc, "use_netrc",
        )
        self._netrc_loc_entry = self._erow(
            creds_grp, ".netrc Location",
            cfg.netrc_location,
            "Path to .netrc (default: ~/.netrc)",
            "netrc_location",
            file_pick=True,
        )

        cert_grp = Adw.PreferencesGroup(title="Client Certificate")
        page.add(cert_grp)

        self._cert_entry = self._erow(
            cert_grp, "Certificate File (PEM)",
            cfg.client_certificate,
            "--client-certificate path",
            "client_certificate",
            file_pick=True,
        )
        self._certkey_entry = self._erow(
            cert_grp, "Private Key File",
            cfg.client_certificate_key,
            "--client-certificate-key path",
            "client_certificate_key",
            file_pick=True,
        )

    # ── Download ─────────────────────────────────────────────────────────

    def _add_download_page(self, cfg: AppConfig) -> None:
        page = Adw.PreferencesPage(
            title="Download",
            icon_name="emblem-downloads-symbolic",
        )
        self.add(page)

        rate_grp = Adw.PreferencesGroup(title="Rate &amp; Concurrency")
        page.add(rate_grp)

        self._cfrag_spin = self._spin(
            rate_grp, "Concurrent Fragments (-N)",
            "DASH/HLS fragments downloaded in parallel per job",
            cfg.concurrent_fragments, 1, 32, "concurrent_fragments",
        )
        self._rate_entry = self._erow(
            rate_grp, "Rate Limit (-r)",
            cfg.limit_rate,
            "e.g. 2M or 500K  (empty = unlimited)",
            "limit_rate",
        )
        self._throttle_entry = self._erow(
            rate_grp, "Throttle Detection Rate",
            cfg.throttled_rate,
            "Min acceptable rate, e.g. 100K — triggers re-extraction if slower",
            "throttled_rate",
        )
        self._chunk_entry = self._erow(
            rate_grp, "HTTP Chunk Size",
            cfg.http_chunk_size,
            "e.g. 10M — chunk-based download to bypass throttling",
            "http_chunk_size",
        )
        self._buf_entry = self._erow(
            rate_grp, "Buffer Size",
            cfg.buffer_size,
            "Default 1024 bytes",
            "buffer_size",
        )

        retry_grp = Adw.PreferencesGroup(title="Retries")
        page.add(retry_grp)

        self._retries_spin = self._spin(
            retry_grp, "Retries (-R)",
            "Number of HTTP retries per segment",
            cfg.retries, 0, 9999, "retries",
        )
        self._frag_retries_spin = self._spin(
            retry_grp, "Fragment Retries",
            "Retries per DASH/HLS fragment",
            cfg.fragment_retries, 0, 9999, "fragment_retries",
        )
        self._fa_retries_spin = self._spin(
            retry_grp, "File Access Retries",
            "Retries on file access errors",
            cfg.file_access_retries, 0, 100, "file_access_retries",
        )
        self._retrysleep_entry = self._erow(
            retry_grp, "Retry Sleep Expression",
            cfg.retry_sleep,
            "e.g. linear=1::2  or  fragment:exp=1:20",
            "retry_sleep",
        )

        ext_dl_grp = Adw.PreferencesGroup(title="External Downloader")
        page.add(ext_dl_grp)

        dl_opts = ["(native)", "aria2c", "axel", "curl", "ffmpeg", "httpie", "wget"]
        dl_idx = dl_opts.index(cfg.external_downloader) \
                 if cfg.external_downloader in dl_opts else 0
        self._dl_combo = self._combo(
            ext_dl_grp, "Downloader",
            dl_opts, dl_idx,
            "external_downloader", dl_opts,
        )
        self._dl_args_entry = self._erow(
            ext_dl_grp, "Downloader Args",
            cfg.external_downloader_args,
            "NAME:ARGS  e.g. aria2c:--max-connection-per-server=4",
            "external_downloader_args",
        )
        self._keepfrag_sw = self._sw(
            ext_dl_grp, "Keep Fragments",
            "Keep .frag files on disk after merging",
            cfg.keep_fragments, "keep_fragments",
        )

    # ── Post-Processing ───────────────────────────────────────────────────

    def _add_postprocessing_page(self, cfg: AppConfig) -> None:
        page = Adw.PreferencesPage(
            title="Post-Process",
            icon_name="applications-multimedia-symbolic",
        )
        self.add(page)

        ffmpeg_grp = Adw.PreferencesGroup(title="FFmpeg")
        page.add(ffmpeg_grp)

        self._ffmpeg_entry = self._erow(
            ffmpeg_grp, "FFmpeg Location",
            cfg.ffmpeg_location,
            "Path to ffmpeg binary or its containing directory",
            "ffmpeg_location",
            file_pick=True,
        )
        self._ppargs_entry = self._erow(
            ffmpeg_grp, "Postprocessor Args (--ppa)",
            cfg.postprocessor_args,
            "e.g. Merger+ffmpeg_i:-v quiet",
            "postprocessor_args",
        )

        policy_grp = Adw.PreferencesGroup(title="Policy")
        page.add(policy_grp)

        self._keepvid_sw = self._sw(
            policy_grp, "Keep Intermediate Video",
            "--keep-video: retain pre-merge video file",
            cfg.keep_video, "keep_video",
        )
        fixup_opts = ["detect_or_warn", "never", "warn", "force"]
        fixup_idx = fixup_opts.index(cfg.fixup) if cfg.fixup in fixup_opts else 0
        self._fixup_combo = self._combo(
            policy_grp, "Fixup Policy",
            fixup_opts, fixup_idx,
            "fixup", fixup_opts,
        )

    # ── Sleep / Rate-Limiting ─────────────────────────────────────────────

    def _add_sleep_page(self, cfg: AppConfig) -> None:
        page = Adw.PreferencesPage(
            title="Rate Limiting",
            icon_name="media-playback-pause-symbolic",
        )
        self.add(page)

        sleep_grp = Adw.PreferencesGroup(
            title="Sleep Intervals",
            description="Slow down requests to avoid server-side rate-limiting or bans",
        )
        page.add(sleep_grp)

        self._sleep_req  = self._float_erow(sleep_grp, "Sleep Between Requests (s)",
                                            cfg.sleep_requests,  "sleep_requests")
        self._sleep_int  = self._float_erow(sleep_grp, "Sleep Before Each Download (s)",
                                            cfg.sleep_interval,  "sleep_interval")
        self._sleep_max  = self._float_erow(sleep_grp, "Max Sleep Interval (s)",
                                            cfg.max_sleep_interval, "max_sleep_interval")
        self._sleep_sub  = self._float_erow(sleep_grp, "Sleep Before Subtitle DL (s)",
                                            cfg.sleep_subtitles, "sleep_subtitles")

    # ── Workarounds ───────────────────────────────────────────────────────

    def _add_workarounds_page(self, cfg: AppConfig) -> None:
        page = Adw.PreferencesPage(
            title="Workarounds",
            icon_name="dialog-warning-symbolic",
        )
        self.add(page)

        tls_grp = Adw.PreferencesGroup(title="TLS / HTTPS")
        page.add(tls_grp)

        self._nochk_sw = self._sw(
            tls_grp, "Skip Certificate Validation",
            "--no-check-certificates (insecure)",
            cfg.no_check_certificates, "no_check_certificates",
        )
        self._insecure_sw = self._sw(
            tls_grp, "Prefer Insecure Connection",
            "--prefer-insecure (YouTube only)",
            cfg.prefer_insecure, "prefer_insecure",
        )
        self._legacy_sw = self._sw(
            tls_grp, "Legacy Server Connect",
            "Allow HTTPS to servers without RFC-5746 renegotiation",
            cfg.legacy_server_connect, "legacy_server_connect",
        )

        misc_grp = Adw.PreferencesGroup(title="Miscellaneous")
        page.add(misc_grp)

        self._bidi_sw = self._sw(
            misc_grp, "BiDi Workaround",
            "--bidi-workaround (requires bidiv/fribidi in PATH)",
            cfg.bidi_workaround, "bidi_workaround",
        )
        self._headers_entry = self._erow(
            misc_grp, "Custom HTTP Headers",
            "  |  ".join(cfg.add_headers),
            "FIELD:VALUE separated by | e.g. Referer:https://example.com",
            "_add_headers_raw",
        )

    # ── Extractor ─────────────────────────────────────────────────────────

    def _add_extractor_page(self, cfg: AppConfig) -> None:
        page = Adw.PreferencesPage(
            title="Extractor",
            icon_name="emblem-system-symbolic",
        )
        self.add(page)

        ext_grp = Adw.PreferencesGroup(title="Extractor Behaviour")
        page.add(ext_grp)

        self._extretries_spin = self._spin(
            ext_grp, "Extractor Retries",
            "Retries on known extractor errors",
            cfg.extractor_retries, 0, 100, "extractor_retries",
        )
        self._dynmpd_sw = self._sw(
            ext_grp, "Allow Dynamic DASH Manifests",
            "--allow-dynamic-mpd (default on)",
            cfg.allow_dynamic_mpd, "allow_dynamic_mpd",
        )
        self._hlssplit_sw = self._sw(
            ext_grp, "Split HLS At Discontinuities",
            "--hls-split-discontinuity",
            cfg.hls_split_discontinuity, "hls_split_discontinuity",
        )
        self._extargs_entry = self._erow(
            ext_grp, "Extractor Args",
            cfg.extractor_args,
            "IE_KEY:ARGS  e.g. youtube:player_client=android",
            "extractor_args",
        )

        runtime_grp = Adw.PreferencesGroup(title="JavaScript Runtimes")
        page.add(runtime_grp)

        self._jsrt_entry = self._erow(
            runtime_grp, "Enabled Runtimes",
            cfg.js_runtimes,
            "Comma-separated priority list: deno, node, quickjs, bun",
            "js_runtimes",
        )

    # ------------------------------------------------------------------
    # Widget factories

    def _sw(self, grp, title, subtitle, active, key) -> Gtk.Switch:
        row = Adw.ActionRow(title=title, subtitle=subtitle)
        sw = Gtk.Switch()
        sw.set_active(active)
        sw.set_valign(Gtk.Align.CENTER)
        sw.connect("notify::active",
                   lambda s, _p, k=key: self._set_bool(k, s.get_active()))
        row.add_suffix(sw)
        row.set_activatable_widget(sw)
        grp.add(row)
        return sw

    def _combo(self, grp, title, items, selected, key, values) -> Gtk.DropDown:
        row = Adw.ActionRow(title=title)
        dd = Gtk.DropDown(model=Gtk.StringList.new(items))
        dd.set_selected(selected)
        dd.set_valign(Gtk.Align.CENTER)
        dd.connect("notify::selected",
                   lambda d, _p, k=key, v=values: self._set_str(
                       k, v[min(d.get_selected(), len(v)-1)]))
        row.add_suffix(dd)
        grp.add(row)
        return dd

    def _erow(self, grp, title, value, placeholder, key,
              file_pick=False) -> Adw.EntryRow:
        row = Adw.EntryRow(title=title)
        row.set_text(value or "")
        row.connect("changed",
                    lambda r, k=key: self._on_entry_changed(r, k))
        if file_pick:
            btn = Gtk.Button(icon_name="folder-open-symbolic")
            btn.add_css_class("flat")
            btn.set_valign(Gtk.Align.CENTER)
            btn.connect("clicked",
                        lambda _b, r=row, k=key: self._pick_file(r, k))
            row.add_suffix(btn)
        grp.add(row)
        return row

    def _float_erow(self, grp, title, value, key) -> Adw.EntryRow:
        row = Adw.EntryRow(title=title)
        row.set_text(str(value) if value else "0")
        row.set_input_purpose(Gtk.InputPurpose.NUMBER)
        row.connect("changed",
                    lambda r, k=key: self._on_float_changed(r, k))
        grp.add(row)
        return row

    def _spin(self, grp, title, subtitle, value, lo, hi, key) -> Gtk.SpinButton:
        row = Adw.ActionRow(title=title, subtitle=subtitle)
        spin = Gtk.SpinButton.new_with_range(lo, hi, 1)
        spin.set_value(value)
        spin.set_valign(Gtk.Align.CENTER)
        spin.set_size_request(110, -1)
        spin.connect("value-changed",
                     lambda s, k=key: self._set_int(k, int(s.get_value())))
        row.add_suffix(spin)
        grp.add(row)
        return spin

    # ------------------------------------------------------------------
    # Config setters

    def _set_bool(self, key, value) -> None:
        self._config.set(key, value)
        self._on_change()

    def _set_str(self, key, value) -> None:
        self._config.set(key, "" if value == "(native)" or value == "(none)" else value)
        self._on_change()

    def _set_int(self, key, value) -> None:
        self._config.set(key, value)
        self._on_change()

    def _on_entry_changed(self, row: Adw.EntryRow, key: str) -> None:
        text = row.get_text().strip()
        if key == "_add_headers_raw":
            headers = [h.strip() for h in text.split("|") if h.strip()]
            self._config.set("add_headers", headers)
        else:
            self._config.set(key, text)
        self._on_change()

    def _on_float_changed(self, row: Adw.EntryRow, key: str) -> None:
        try:
            val = float(row.get_text().strip() or "0")
        except ValueError:
            val = 0.0
        self._config.set(key, val)

    # ------------------------------------------------------------------
    # File / directory pickers

    def _pick_outdir(self, *_) -> None:
        dlg = Gtk.FileDialog()
        dlg.set_title("Select Default Output Directory")
        dlg.select_folder(self, None, self._on_outdir_picked)

    def _on_outdir_picked(self, dlg, result) -> None:
        try:
            folder = dlg.select_folder_finish(result)
            if folder:
                path = folder.get_path()
                self._config.set("default_output_dir", path)
                self._outdir_row.set_subtitle(path)
                self._on_change()
        except Exception:
            pass

    def _pick_file(self, row: Adw.EntryRow, key: str) -> None:
        dlg = Gtk.FileDialog()
        dlg.set_title(f"Select: {row.get_title()}")
        dlg.open(self, None,
                 lambda d, r, k=key, ro=row: self._on_file_picked(d, r, k, ro))

    def _on_file_picked(self, dlg, result, key, row) -> None:
        try:
            f = dlg.open_finish(result)
            if f:
                path = f.get_path()
                row.set_text(path)
                self._config.set(key, path)
                self._on_change()
        except Exception:
            pass
