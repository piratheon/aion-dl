"""
format_panel.py - Per-download format/options popover.

Uses Gtk.Popover with autohide=True so any click outside the popover
or pressing Escape closes it immediately.
"""

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw

from ..models import DownloadOptions


class FormatPanel(Gtk.Popover):
    def __init__(self) -> None:
        super().__init__()
        # autohide: close on click-outside or Escape — explicit to guarantee it
        self.set_autohide(True)
        self.set_has_arrow(True)
        self.set_size_request(480, -1)
        self._opts = DownloadOptions()
        self._build()

    # ------------------------------------------------------------------

    def get_options(self) -> DownloadOptions:
        return self._opts

    def apply_defaults(self, opts: DownloadOptions) -> None:
        self._opts = opts
        self._populate_from_opts()

    # ------------------------------------------------------------------

    def _build(self) -> None:
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_max_content_height(680)
        scroll.set_propagate_natural_height(True)

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        outer.set_margin_top(8)
        outer.set_margin_bottom(12)
        outer.set_margin_start(8)
        outer.set_margin_end(8)

        hdr = Gtk.Label(label="Download Options")
        hdr.add_css_class("title-4")
        hdr.set_margin_bottom(10)
        outer.append(hdr)

        # ── Format &amp; Quality ──────────────────────────────────────────────
        grp = self._grp("Format &amp; Quality")
        outer.append(grp)

        self._type_row, self._type_combo = self._combo(
            grp, "Type", ["Video + Audio", "Audio Only", "Video Only"])
        self._quality_row, self._quality_combo = self._combo(
            grp, "Quality", ["Best Available", "4K (2160p)", "1080p", "720p", "480p", "360p", "Worst"])
        self._vcontainer_row, self._vcontainer_combo = self._combo(
            grp, "Video Container", ["mp4", "mkv", "webm", "avi", "mov"])
        self._merge_row, self._merge_combo = self._combo(
            grp, "Merge Into", ["mp4", "mkv", "webm", "avi", "mov"])
        self._afmt_row, self._afmt_combo = self._combo(
            grp, "Audio Format", ["mp3", "aac", "flac", "opus", "vorbis", "wav", "m4a", "alac", "best"])
        self._aqual_row = self._erow(grp, "Audio Quality", "5",
                                     "0 (best)–10 (worst) or bitrate e.g. 192K")
        self._fcode_row = self._erow(grp, "Format Code",  "",
                                     "Override: e.g. bestvideo[height<=1080]+bestaudio")
        self._fsort_row = self._erow(grp, "Format Sort (-S)", "",
                                     "e.g. res,ext:mp4,acodec:aac")
        self._free_row, self._free_switch = self._sw(grp, "Prefer Free Formats",
                                                      "Prefer WebM/Opus over MP4/AAC")

        # ── Subtitles ─────────────────────────────────────────────────────
        grp = self._grp("Subtitles")
        outer.append(grp)
        self._wsubs_row, self._wsubs_sw   = self._sw(grp, "Download Subtitles", "--write-subs")
        self._wauto_row, self._wauto_sw   = self._sw(grp, "Auto-Generated",      "--write-auto-subs")
        self._esubs_row, self._esubs_sw   = self._sw(grp, "Embed Subtitles",     "Into mp4/mkv/webm")
        self._sublangs_row                = self._erow(grp, "Languages", "en",   "en,fr  all  en.*,ja")
        self._subfmt_row,   self._subfmt_combo   = self._combo(grp, "Sub Format",   ["srt","ass","vtt","lrc","best"])
        self._convsub_row,  self._convsub_combo  = self._combo(grp, "Convert Subs", ["(none)","srt","ass","vtt","lrc"])

        # ── Thumbnails ────────────────────────────────────────────────────
        grp = self._grp("Thumbnails")
        outer.append(grp)
        self._wthumb_row, self._wthumb_sw    = self._sw(grp, "Write Thumbnail",  "--write-thumbnail")
        self._ethumb_row, self._ethumb_sw    = self._sw(grp, "Embed Thumbnail",  "--embed-thumbnail")
        self._convthumb_row, self._convthumb_combo = self._combo(grp, "Convert To", ["(none)","jpg","png","webp"])

        # ── Metadata ──────────────────────────────────────────────────────
        grp = self._grp("Metadata &amp; Embedding")
        outer.append(grp)
        self._emeta_row,  self._emeta_sw   = self._sw(grp, "Embed Metadata",   "--embed-metadata")
        self._echap_row,  self._echap_sw   = self._sw(grp, "Embed Chapters",   "--embed-chapters")
        self._winfoj_row, self._winfoj_sw  = self._sw(grp, "Write info.json",  "--write-info-json")
        self._einfoj_row, self._einfoj_sw  = self._sw(grp, "Embed info.json",  "mkv/mka only")
        self._wdesc_row,  self._wdesc_sw   = self._sw(grp, "Write Description","--write-description")
        self._wcomm_row,  self._wcomm_sw   = self._sw(grp, "Write Comments",   "--write-comments")
        self._xattr_row,  self._xattr_sw   = self._sw(grp, "Write xattrs",     "Dublin Core + XDG")
        self._wlink_row,  self._wlink_sw   = self._sw(grp, "Write .desktop Link","--write-desktop-link")

        # ── SponsorBlock ──────────────────────────────────────────────────
        grp = self._grp("SponsorBlock")
        outer.append(grp)
        self._sbmark_row   = self._erow(grp, "Mark As Chapters", "",
                                        "sponsor,intro,outro,selfpromo,interaction,…")
        self._sbremove_row = self._erow(grp, "Remove Segments",  "",
                                        "all,-filler  or  sponsor,intro")
        self._sbapi_row    = self._erow(grp, "API URL",
                                        "https://sponsor.ajay.app",
                                        "https://sponsor.ajay.app")

        # ── Playlist ──────────────────────────────────────────────────────
        grp = self._grp("Playlist")
        outer.append(grp)
        self._yesp_row,     self._yesp_sw      = self._sw(grp, "Download Playlist", "--yes-playlist")
        self._yesp_sw.set_active(True)
        self._pitems_row   = self._erow(grp, "Items (-I)", "", "1:5,7,-3::2  (empty=all)")
        self._prandom_row,  self._prandom_sw   = self._sw(grp, "Shuffle Order",       "--playlist-random")
        self._lazy_row,     self._lazy_sw      = self._sw(grp, "Lazy Processing",     "--lazy-playlist")
        self._maxdl_row,    self._maxdl_spin   = self._spin(grp, "Max Downloads",      0, 0, 10000)
        self._skiperr_row,  self._skiperr_spin = self._spin(grp, "Skip After N Errors",0, 0, 100)
        self._concat_row,   self._concat_combo = self._combo(grp, "Concat Policy",
                                                              ["multi_video","never","always"])
        self._livestart_row,self._livestart_sw = self._sw(grp, "Livestream From Start",
                                                           "--live-from-start (experimental)")
        self._waitvid_row  = self._erow(grp, "Wait For Stream", "", "MIN or MIN-MAX seconds")
        self._breakex_row,  self._breakex_sw  = self._sw(grp, "Stop On Existing",    "--break-on-existing")

        # ── Output ────────────────────────────────────────────────────────
        grp = self._grp("Output")
        outer.append(grp)

        self._outdir_row = Adw.ActionRow(title="Output Directory")
        self._outdir_lbl = Gtk.Label(label="(global default)", ellipsize=3)
        self._outdir_lbl.add_css_class("dim-label")
        self._outdir_lbl.add_css_class("caption")
        outdir_btn = Gtk.Button(icon_name="folder-open-symbolic")
        outdir_btn.add_css_class("flat")
        outdir_btn.set_valign(Gtk.Align.CENTER)
        outdir_btn.connect("clicked", self._pick_outdir)
        self._outdir_row.add_suffix(self._outdir_lbl)
        self._outdir_row.add_suffix(outdir_btn)
        grp.add(self._outdir_row)

        self._tmpl_row    = self._erow(grp, "Filename Template",
                                       "%(title)s [%(id)s].%(ext)s",
                                       "%(title)s [%(id)s].%(ext)s")
        self._archive_row = self._erow(grp, "Download Archive", "", "Path to archive file")
        self._restrict_row,  self._restrict_sw   = self._sw(grp, "Restrict Filenames",    "ASCII only")
        self._winfiles_row,  self._winfiles_sw   = self._sw(grp, "Windows Filenames",     "--windows-filenames")
        self._nowrt_row,     self._nowrt_sw      = self._sw(grp, "No Overwrites",          "--no-overwrites")
        self._forcewrt_row,  self._forcewrt_sw   = self._sw(grp, "Force Overwrites",       "--force-overwrites")

        # ── Sections &amp; Chapters ───────────────────────────────────────────
        grp = self._grp("Sections &amp; Chapters")
        outer.append(grp)
        self._sections_row   = self._erow(grp, "Download Sections", "",
                                          "One per line, e.g. *10:15-20:30  or  intro")
        self._splitchap_row, self._splitchap_sw  = self._sw(grp, "Split By Chapters",    "--split-chapters")
        self._rmchap_row     = self._erow(grp, "Remove Chapters (regex)", "", "(?i)intro|outro")
        self._fkeyframe_row, self._fkeyframe_sw  = self._sw(grp, "Force Keyframes At Cuts","Requires re-encode")
        self._hlsmpeg_row,   self._hlsmpeg_sw    = self._sw(grp, "HLS Use MPEG-TS",       "--hls-use-mpegts")
        self._cfrag_row,     self._cfrag_spin    = self._spin(grp, "Concurrent Fragments", 1, 1, 32)

        # ── Video Selection Filters ───────────────────────────────────────
        grp = self._grp("Video Selection Filters")
        outer.append(grp)
        self._minfs_row       = self._erow(grp, "Min Filesize",  "", "e.g. 50k or 10M")
        self._maxfs_row       = self._erow(grp, "Max Filesize",  "", "e.g. 2G or 500M")
        self._date_row        = self._erow(grp, "Upload Date (=)","", "YYYYMMDD or today-2weeks")
        self._datebefore_row  = self._erow(grp, "Before Date",   "", "YYYYMMDD")
        self._dateafter_row   = self._erow(grp, "After Date",    "", "YYYYMMDD")
        self._matchf_row      = self._erow(grp, "Match Filter",  "", "!is_live & like_count>100")
        self._agelimit_row,   self._agelimit_spin = self._spin(grp, "Age Limit", 0, 0, 99)

        # ── Post-Processing ───────────────────────────────────────────────
        grp = self._grp("Post-Processing")
        outer.append(grp)
        self._keepvid_row, self._keepvid_sw = self._sw(grp, "Keep Intermediate Video", "--keep-video")
        self._fixup_row,   self._fixup_combo = self._combo(grp, "Fixup Policy",
                                                            ["detect_or_warn","never","warn","force"])
        self._exec_row     = self._erow(grp, "Execute After (--exec)", "",
                                        "e.g. notify-send 'Done' %(title)q")

        # ── Extra ─────────────────────────────────────────────────────────
        grp = self._grp("Extra Arguments")
        outer.append(grp)
        self._extra_row = self._erow(grp, "Raw yt-dlp Args", "",
                                     "Appended verbatim, e.g. --mark-watched")

        self._connect_signals()
        scroll.set_child(outer)
        self.set_child(scroll)
        self._populate_from_opts()

    # ------------------------------------------------------------------
    # Factories

    @staticmethod
    def _grp(title: str) -> Adw.PreferencesGroup:
        g = Adw.PreferencesGroup(title=title)
        g.set_margin_bottom(12)
        return g

    @staticmethod
    def _sw(grp, title, subtitle="") -> tuple[Adw.ActionRow, Gtk.Switch]:
        row = Adw.ActionRow(title=title, subtitle=subtitle)
        sw = Gtk.Switch()
        sw.set_valign(Gtk.Align.CENTER)
        row.add_suffix(sw)
        row.set_activatable_widget(sw)
        grp.add(row)
        return row, sw

    @staticmethod
    def _combo(grp, title, items) -> tuple[Adw.ActionRow, Gtk.DropDown]:
        row = Adw.ActionRow(title=title)
        dd = Gtk.DropDown(model=Gtk.StringList.new(items))
        dd.set_valign(Gtk.Align.CENTER)
        row.add_suffix(dd)
        grp.add(row)
        return row, dd

    @staticmethod
    def _erow(grp, title, default, placeholder="") -> Adw.EntryRow:
        row = Adw.EntryRow(title=title)
        row.set_text(default or "")
        grp.add(row)
        return row

    @staticmethod
    def _spin(grp, title, default, lo, hi) -> tuple[Adw.ActionRow, Gtk.SpinButton]:
        row = Adw.ActionRow(title=title)
        spin = Gtk.SpinButton.new_with_range(lo, hi, 1)
        spin.set_value(default)
        spin.set_valign(Gtk.Align.CENTER)
        spin.set_size_request(90, -1)
        row.add_suffix(spin)
        grp.add(row)
        return row, spin

    # ------------------------------------------------------------------
    # Signals

    def _connect_signals(self) -> None:
        widgets = [
            self._type_combo, self._quality_combo, self._vcontainer_combo,
            self._merge_combo, self._afmt_combo, self._subfmt_combo,
            self._convsub_combo, self._convthumb_combo, self._concat_combo,
            self._fixup_combo,
        ]
        for w in widgets:
            w.connect("notify::selected", self._sync_to_opts)

        switches = [
            self._free_switch, self._wsubs_sw, self._wauto_sw, self._esubs_sw,
            self._wthumb_sw, self._ethumb_sw, self._emeta_sw, self._echap_sw,
            self._winfoj_sw, self._einfoj_sw, self._wdesc_sw, self._wcomm_sw,
            self._xattr_sw, self._wlink_sw, self._yesp_sw, self._prandom_sw,
            self._lazy_sw, self._livestart_sw, self._breakex_sw,
            self._restrict_sw, self._winfiles_sw, self._nowrt_sw, self._forcewrt_sw,
            self._splitchap_sw, self._fkeyframe_sw, self._hlsmpeg_sw,
            self._keepvid_sw,
        ]
        for sw in switches:
            sw.connect("notify::active", self._sync_to_opts)

        spins = [self._maxdl_spin, self._skiperr_spin, self._cfrag_spin, self._agelimit_spin]
        for sp in spins:
            sp.connect("value-changed", self._sync_to_opts)

        entry_rows = [
            self._aqual_row, self._fcode_row, self._fsort_row,
            self._sublangs_row, self._sbmark_row, self._sbremove_row, self._sbapi_row,
            self._pitems_row, self._waitvid_row, self._tmpl_row, self._archive_row,
            self._sections_row, self._rmchap_row,
            self._minfs_row, self._maxfs_row, self._date_row,
            self._datebefore_row, self._dateafter_row, self._matchf_row,
            self._exec_row, self._extra_row,
        ]
        for er in entry_rows:
            er.connect("changed", self._sync_to_opts)

    # ------------------------------------------------------------------

    def _sync_to_opts(self, *_) -> None:
        o = self._opts
        _T = ["video", "audio", "video_only"]
        _Q = ["best", "2160", "1080", "720", "480", "360", "worst"]
        _VC = ["mp4", "mkv", "webm", "avi", "mov"]
        _AF = ["mp3", "aac", "flac", "opus", "vorbis", "wav", "m4a", "alac", "best"]
        _SF = ["srt", "ass", "vtt", "lrc", "best"]
        _CS = ["", "srt", "ass", "vtt", "lrc"]
        _CT = ["", "jpg", "png", "webp"]
        _CP = ["multi_video", "never", "always"]
        _FX = ["detect_or_warn", "never", "warn", "force"]

        def idx(combo): return combo.get_selected()
        def etext(row): return row.get_text().strip()
        def pick(lst, i): return lst[min(i, len(lst)-1)]

        o.download_type        = pick(_T,  idx(self._type_combo))
        o.quality              = pick(_Q,  idx(self._quality_combo))
        o.video_container      = pick(_VC, idx(self._vcontainer_combo))
        o.merge_output_format  = pick(_VC, idx(self._merge_combo))
        o.audio_format         = pick(_AF, idx(self._afmt_combo))
        o.audio_quality        = etext(self._aqual_row) or "5"
        o.format_code          = etext(self._fcode_row)
        o.format_sort          = etext(self._fsort_row)
        o.prefer_free_formats  = self._free_switch.get_active()
        o.write_subs           = self._wsubs_sw.get_active()
        o.write_auto_subs      = self._wauto_sw.get_active()
        o.embed_subs           = self._esubs_sw.get_active()
        o.sub_langs            = etext(self._sublangs_row) or "en"
        o.sub_format           = pick(_SF, idx(self._subfmt_combo))
        o.convert_subs         = pick(_CS, idx(self._convsub_combo))
        o.write_thumbnail      = self._wthumb_sw.get_active()
        o.embed_thumbnail      = self._ethumb_sw.get_active()
        o.convert_thumbnails   = pick(_CT, idx(self._convthumb_combo))
        o.embed_metadata       = self._emeta_sw.get_active()
        o.embed_chapters       = self._echap_sw.get_active()
        o.write_info_json      = self._winfoj_sw.get_active()
        o.embed_info_json      = self._einfoj_sw.get_active()
        o.write_description    = self._wdesc_sw.get_active()
        o.write_comments       = self._wcomm_sw.get_active()
        o.xattrs               = self._xattr_sw.get_active()
        o.write_desktop_link   = self._wlink_sw.get_active()
        o.sponsorblock_mark    = etext(self._sbmark_row)
        o.sponsorblock_remove  = etext(self._sbremove_row)
        o.sponsorblock_api     = etext(self._sbapi_row) or "https://sponsor.ajay.app"
        o.yes_playlist         = self._yesp_sw.get_active()
        o.playlist_items       = etext(self._pitems_row)
        o.playlist_random      = self._prandom_sw.get_active()
        o.lazy_playlist        = self._lazy_sw.get_active()
        o.max_downloads        = int(self._maxdl_spin.get_value())
        o.skip_playlist_after_errors = int(self._skiperr_spin.get_value())
        o.concat_playlist      = pick(_CP, idx(self._concat_combo))
        o.live_from_start      = self._livestart_sw.get_active()
        o.wait_for_video       = etext(self._waitvid_row)
        o.break_on_existing    = self._breakex_sw.get_active()
        o.output_template      = etext(self._tmpl_row) or "%(title)s [%(id)s].%(ext)s"
        o.download_archive     = etext(self._archive_row)
        o.restrict_filenames   = self._restrict_sw.get_active()
        o.windows_filenames    = self._winfiles_sw.get_active()
        o.no_overwrites        = self._nowrt_sw.get_active()
        o.force_overwrites     = self._forcewrt_sw.get_active()
        o.download_sections    = etext(self._sections_row)
        o.split_chapters       = self._splitchap_sw.get_active()
        o.remove_chapters      = etext(self._rmchap_row)
        o.force_keyframes_at_cuts = self._fkeyframe_sw.get_active()
        o.hls_use_mpegts       = self._hlsmpeg_sw.get_active()
        o.concurrent_fragments = int(self._cfrag_spin.get_value())
        o.min_filesize         = etext(self._minfs_row)
        o.max_filesize         = etext(self._maxfs_row)
        o.date                 = etext(self._date_row)
        o.datebefore           = etext(self._datebefore_row)
        o.dateafter            = etext(self._dateafter_row)
        o.match_filters        = etext(self._matchf_row)
        o.age_limit            = int(self._agelimit_spin.get_value())
        o.keep_video           = self._keepvid_sw.get_active()
        o.fixup                = pick(_FX, idx(self._fixup_combo))
        o.exec_cmd             = etext(self._exec_row)
        o.extra_args           = etext(self._extra_row)

    def _populate_from_opts(self) -> None:
        o = self._opts
        _T  = ["video","audio","video_only"]
        _Q  = ["best","2160","1080","720","480","360","worst"]
        _VC = ["mp4","mkv","webm","avi","mov"]
        _AF = ["mp3","aac","flac","opus","vorbis","wav","m4a","alac","best"]
        _SF = ["srt","ass","vtt","lrc","best"]
        _CS = ["","srt","ass","vtt","lrc"]
        _CT = ["","jpg","png","webp"]
        _CP = ["multi_video","never","always"]
        _FX = ["detect_or_warn","never","warn","force"]

        def si(lst, val): return lst.index(val) if val in lst else 0

        self._type_combo.set_selected(si(_T,  o.download_type))
        self._quality_combo.set_selected(si(_Q, o.quality))
        self._vcontainer_combo.set_selected(si(_VC, o.video_container))
        self._merge_combo.set_selected(si(_VC, o.merge_output_format))
        self._afmt_combo.set_selected(si(_AF, o.audio_format))
        self._aqual_row.set_text(o.audio_quality)
        self._fcode_row.set_text(o.format_code)
        self._fsort_row.set_text(o.format_sort)
        self._free_switch.set_active(o.prefer_free_formats)
        self._wsubs_sw.set_active(o.write_subs)
        self._wauto_sw.set_active(o.write_auto_subs)
        self._esubs_sw.set_active(o.embed_subs)
        self._sublangs_row.set_text(o.sub_langs)
        self._subfmt_combo.set_selected(si(_SF, o.sub_format))
        self._convsub_combo.set_selected(si(_CS, o.convert_subs))
        self._wthumb_sw.set_active(o.write_thumbnail)
        self._ethumb_sw.set_active(o.embed_thumbnail)
        self._convthumb_combo.set_selected(si(_CT, o.convert_thumbnails))
        self._emeta_sw.set_active(o.embed_metadata)
        self._echap_sw.set_active(o.embed_chapters)
        self._winfoj_sw.set_active(o.write_info_json)
        self._einfoj_sw.set_active(o.embed_info_json)
        self._wdesc_sw.set_active(o.write_description)
        self._wcomm_sw.set_active(o.write_comments)
        self._xattr_sw.set_active(o.xattrs)
        self._wlink_sw.set_active(o.write_desktop_link)
        self._sbmark_row.set_text(o.sponsorblock_mark)
        self._sbremove_row.set_text(o.sponsorblock_remove)
        self._sbapi_row.set_text(o.sponsorblock_api)
        self._yesp_sw.set_active(o.yes_playlist)
        self._pitems_row.set_text(o.playlist_items)
        self._prandom_sw.set_active(o.playlist_random)
        self._lazy_sw.set_active(o.lazy_playlist)
        self._maxdl_spin.set_value(o.max_downloads)
        self._skiperr_spin.set_value(o.skip_playlist_after_errors)
        self._concat_combo.set_selected(si(_CP, o.concat_playlist))
        self._livestart_sw.set_active(o.live_from_start)
        self._waitvid_row.set_text(o.wait_for_video)
        self._breakex_sw.set_active(o.break_on_existing)
        self._tmpl_row.set_text(o.output_template)
        self._archive_row.set_text(o.download_archive)
        self._restrict_sw.set_active(o.restrict_filenames)
        self._winfiles_sw.set_active(o.windows_filenames)
        self._nowrt_sw.set_active(o.no_overwrites)
        self._forcewrt_sw.set_active(o.force_overwrites)
        self._sections_row.set_text(o.download_sections)
        self._splitchap_sw.set_active(o.split_chapters)
        self._rmchap_row.set_text(o.remove_chapters)
        self._fkeyframe_sw.set_active(o.force_keyframes_at_cuts)
        self._hlsmpeg_sw.set_active(o.hls_use_mpegts)
        self._cfrag_spin.set_value(o.concurrent_fragments)
        self._minfs_row.set_text(o.min_filesize)
        self._maxfs_row.set_text(o.max_filesize)
        self._date_row.set_text(o.date)
        self._datebefore_row.set_text(o.datebefore)
        self._dateafter_row.set_text(o.dateafter)
        self._matchf_row.set_text(o.match_filters)
        self._agelimit_spin.set_value(o.age_limit)
        self._keepvid_sw.set_active(o.keep_video)
        self._fixup_combo.set_selected(si(_FX, o.fixup))
        self._exec_row.set_text(o.exec_cmd)
        self._extra_row.set_text(o.extra_args)

    # ------------------------------------------------------------------

    def _pick_outdir(self, *_) -> None:
        dlg = Gtk.FileDialog()
        dlg.set_title("Select Output Directory")
        dlg.select_folder(self.get_root(), None, self._on_dir_picked)

    def _on_dir_picked(self, dlg, result) -> None:
        try:
            folder = dlg.select_folder_finish(result)
            if folder:
                path = folder.get_path()
                self._opts.output_dir = path
                self._outdir_lbl.set_label(path.split("/")[-1] or path)
        except Exception:
            pass
