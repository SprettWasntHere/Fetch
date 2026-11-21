import os
import shutil
import threading
import time
import random
from concurrent.futures import ThreadPoolExecutor
from texts import COMPLETED_TEXTS
from shared import append_history_entry

cookie_log_state = set()

def random_text():
    return random.choice(COMPLETED_TEXTS)

def update_ytdlp(log_callback):
    try:
        import yt_dlp
        return yt_dlp
    except ImportError:
        log_callback("Error: yt-dlp is missing from the environment.")
        return None

def format_speed(speed_bps):
    if not speed_bps or speed_bps <= 0:
        return "-- KB/s"
    if speed_bps >= 1024 * 1024:
        return f"{speed_bps / (1024 * 1024):.2f} MB/s"
    return f"{speed_bps / 1024:.1f} KB/s"

def format_eta(eta_seconds):
    if eta_seconds is None or eta_seconds < 0:
        return "--:--"
    eta_int = int(eta_seconds)
    hours, rem = divmod(eta_int, 3600)
    minutes, seconds = divmod(rem, 60)
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"

def _build_video_format_selector(quality_choice):
    q = (quality_choice or "Best").strip()
    height_map = {
        "2160p (4K)": 2160,
        "1440p (2K)": 1440,
        "1080p": 1080,
        "720p": 720,
        "480p": 480,
        "360p": 360,
    }
    if q in height_map:
        h = height_map[q]
        return (
            f"bestvideo[height<={h}][vcodec^=avc1]+bestaudio/"
            f"bestvideo[height<={h}]+bestaudio/"
            f"best[height<={h}]/best"
        )
    return "bestvideo[vcodec^=avc1]+bestaudio/best[ext=mp4]/best"

def _parse_audio_bitrate(quality_choice):
    q = (quality_choice or "192k").strip().lower()
    if q.endswith("k"):
        q = q[:-1]
    return q if q.isdigit() else "192"

def _apply_cookie_opts(
    opts,
    cookie_mode="None",
    cookie_file="",
    cookie_browser="",
    log_callback=None,
    warn_once=None,
):
    mode = (cookie_mode or "None").strip()
    if mode == "Cookies File":
        clean_path = (cookie_file or "").strip().strip('"')
        if clean_path and os.path.isfile(clean_path):
            opts["cookiefile"] = clean_path
            if log_callback and (warn_once is None or "loaded_file" not in warn_once):
                if warn_once is not None:
                    warn_once.add("loaded_file")
                log_callback(f"Using cookie file: {os.path.basename(clean_path)}")
        else:
            if log_callback and (warn_once is None or "missing_file" not in warn_once):
                if warn_once is not None:
                    warn_once.add("missing_file")
                log_callback(f"Warning: Cookie file not found: {clean_path or '(empty)'}")
    elif mode == "Browser" and cookie_browser:
        opts["cookiesfrombrowser"] = (cookie_browser.strip().lower(),)
        if log_callback and (warn_once is None or "loaded_browser" not in warn_once):
            if warn_once is not None:
                warn_once.add("loaded_browser")
            log_callback(f"Using cookies from browser: {cookie_browser.strip().lower()}")

def parse_urls_from_txt(txt_path):
    urls = []
    with open(txt_path, "r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith(("http://", "https://")):
                urls.append(line)
    return urls


def run_download(
    url_or_urls,
    format_choice,
    download_path,
    log_callback,
    resource_path_func,
    progress_callback=None,
    dump_thumbnail=False,
    quality_choice="Best",
    cookie_mode="None",
    cookie_file="",
    cookie_browser="",
    cancel_event=None,
):
    yt_dlp = update_ytdlp(log_callback)
    if not yt_dlp:
        log_callback("Error: yt-dlp is not available.")
        return False

    if cancel_event is None:
        cancel_event = threading.Event()

    def is_cancelled():
        return cancel_event.is_set()

    def report_progress(percent, speed_text="-- KB/s", eta_text="--:--"):
        if progress_callback:
            try:
                progress_callback(percent, speed_text, eta_text)
            except TypeError:
                progress_callback(percent)

    audio_format = (
        "mp3"
        if "MP3" in format_choice
        else ("wav" if "WAV" in format_choice else None)
    )
    embed_cover = "Cover" in format_choice
    audio_bitrate = _parse_audio_bitrate(quality_choice)
    video_selector = _build_video_format_selector(quality_choice)

    if isinstance(url_or_urls, (list, tuple)):
        input_sources = [u.strip() for u in url_or_urls if u and u.strip()]
    else:
        input_sources = [url_or_urls.strip()] if url_or_urls and url_or_urls.strip() else []

    if not input_sources:
        log_callback("No valid URLs provided.")
        return False

    bundled_ffmpeg_dir = resource_path_func("bin")
    has_bundled_ffmpeg = bool(
        bundled_ffmpeg_dir and shutil.which("ffmpeg", path=bundled_ffmpeg_dir)
    )

    tasks = []
    for source_url in input_sources:
        if is_cancelled():
            log_callback("Download cancelled by user.")
            report_progress(100, "-- KB/s", "--:--")
            return False

        log_callback(f"Analyzing URL: {source_url}")
        try:
            pre_opts = {
                "quiet": True,
                "no_warnings": True,
                "extract_flat": "in_playlist",
            }
            if has_bundled_ffmpeg:
                pre_opts["ffmpeg_location"] = bundled_ffmpeg_dir
            _apply_cookie_opts(
                pre_opts,
                cookie_mode,
                cookie_file,
                cookie_browser,
                log_callback=log_callback,
                warn_once=cookie_log_state,
            )

            with yt_dlp.YoutubeDL(pre_opts) as ydl:
                info = ydl.extract_info(source_url, download=False)

            if not info:
                log_callback(f"Failed to extract metadata for: {source_url}")
                append_history_entry(
                    source_url, source_url, format_choice, quality_choice, download_path, "Failed"
                )
                continue

            is_playlist = (
                "entries" in info
                or info.get("_type") in ["playlist", "multi_video"]
                or bool(info.get("playlist_title") or info.get("album"))
            )

            if is_playlist and "entries" in info:
                playlist_name = (
                    info.get("playlist_title")
                    or info.get("title")
                    or info.get("album")
                    or "Playlist"
                )
                safe_playlist_name = "".join(
                    c for c in playlist_name if c not in '<>:"/\\|?*'
                ).strip() or "Playlist"
                target_dir = os.path.join(download_path, safe_playlist_name)
                entries = [e for e in info["entries"] if e]
                log_callback(f"Found playlist '{playlist_name}' with {len(entries)} tracks.")

                for entry in entries:
                    track_url = (
                        entry.get("url")
                        or (f"https://www.youtube.com/watch?v={entry['id']}" if entry.get("id") else None)
                    )
                    if track_url:
                        tasks.append({
                            "url": track_url,
                            "title": entry.get("title") or track_url,
                            "target_dir": target_dir,
                            "album": playlist_name,
                        })
            else:
                tasks.append({
                    "url": info.get("webpage_url") or source_url,
                    "title": info.get("title") or source_url,
                    "target_dir": download_path,
                    "album": info.get("album") or os.path.basename(download_path) or "Single",
                })

        except yt_dlp.utils.DownloadCancelled:
            log_callback("Download cancelled by user.")
            report_progress(100, "-- KB/s", "--:--")
            return False
        except Exception as e:
            log_callback(f"Error analyzing {source_url}: {e}")
            append_history_entry(
                source_url, source_url, format_choice, quality_choice, download_path, "Error"
            )

    if not tasks:
        log_callback("No downloadable items found.")
        report_progress(100, "-- KB/s", "--:--")
        return False

    total_tracks = len(tasks)
    completed_tracks = [0]
    progress_lock = threading.Lock()
    cancelled_flag = [False]

    def download_single_track(task):
        if is_cancelled():
            cancelled_flag[0] = True
            return

        track_url = task["url"]
        track_title = task["title"]
        target_dir = task["target_dir"]
        fallback_album = task["album"]

        os.makedirs(target_dir, exist_ok=True)

        track_opts = {
            "quiet": True,
            "no_warnings": True,
            "concurrent_fragment_downloads": 4,
            "outtmpl": os.path.join(target_dir, "%(title)s [%(id)s].%(ext)s"),
        }

        if has_bundled_ffmpeg:
            track_opts["ffmpeg_location"] = bundled_ffmpeg_dir

        _apply_cookie_opts(
            pre_opts,
            cookie_mode,
            cookie_file,
            cookie_browser,
            log_callback=log_callback,
            warn_once=cookie_log_state,
        )

        if dump_thumbnail:
            track_opts["writethumbnail"] = True

        if audio_format:
            track_opts["format"] = "bestaudio/best"
            track_opts["embedmetadata"] = True
            pp_extract = {
                "key": "FFmpegExtractAudio",
                "preferredcodec": audio_format,
            }
            if audio_format == "mp3":
                pp_extract["preferredquality"] = audio_bitrate

            track_opts["postprocessors"] = [
                pp_extract,
                {"key": "FFmpegMetadata"},
            ]
            track_opts["postprocessor_args"] = [
                "-metadata",
                f"album={fallback_album}",
            ]

            if embed_cover:
                track_opts["writethumbnail"] = True
                track_opts["embedthumbnail"] = True
                track_opts["postprocessor_args"].extend(
                    ["-id3v2_version", "3", "-write_id3v1", "1"]
                )
                embed_pp = {"key": "EmbedThumbnail"}
                if dump_thumbnail:
                    embed_pp["already_have_thumbnail"] = True
                track_opts["postprocessors"].append(embed_pp)
        else:
            track_opts["format"] = video_selector
            track_opts["merge_output_format"] = "mp4"

        logged_files = set()

        def ydl_hook(d):
            if is_cancelled():
                cancelled_flag[0] = True
                raise yt_dlp.utils.DownloadCancelled("Cancelled by user.")

            timestamp = time.strftime("%H:%M:%S")
            status = d.get("status")

            if status == "downloading":
                filename = os.path.basename(d.get("filename", "file"))
                if filename not in logged_files:
                    log_callback(f"[{timestamp}] Downloading: {filename}")
                    logged_files.add(filename)

                speed_str = format_speed(d.get("speed"))
                eta_str = format_eta(d.get("eta"))

                total_bytes = d.get("total_bytes") or d.get("total_bytes_estimate")
                downloaded_bytes = d.get("downloaded_bytes", 0)

                with progress_lock:
                    base_progress = (completed_tracks[0] / total_tracks) * 100
                    if total_bytes and total_bytes > 0:
                        track_fraction = min(1.0, max(0.0, downloaded_bytes / total_bytes)) / total_tracks
                        current_progress = base_progress + (track_fraction * 100)
                    else:
                        current_progress = base_progress

                report_progress(current_progress, speed_str, eta_str)

            elif status == "finished":
                log_callback(
                    f"[{timestamp}] Finished processing: {os.path.basename(d.get('filename', 'file'))}"
                )

        track_opts["progress_hooks"] = [ydl_hook]

        try:
            with yt_dlp.YoutubeDL(track_opts) as ydl:
                ydl.download([track_url])

            with progress_lock:
                completed_tracks[0] += 1
                pct = (completed_tracks[0] / total_tracks) * 100

            report_progress(pct, "-- KB/s", "--:--")
            append_history_entry(
                track_url,
                track_title,
                format_choice,
                quality_choice,
                target_dir,
                "Completed",
            )

        except yt_dlp.utils.DownloadCancelled:
            cancelled_flag[0] = True
            append_history_entry(
                track_url,
                track_title,
                format_choice,
                quality_choice,
                target_dir,
                "Cancelled",
            )
        except Exception as e:
            if is_cancelled():
                cancelled_flag[0] = True
                return
            log_callback(f"Error downloading '{track_title}': {e}")
            with progress_lock:
                completed_tracks[0] += 1
                pct = (completed_tracks[0] / total_tracks) * 100
            report_progress(pct, "-- KB/s", "--:--")
            append_history_entry(
                track_url,
                track_title,
                format_choice,
                quality_choice,
                target_dir,
                "Failed",
            )

    if total_tracks >= 100:
        max_workers, batch_size, pause_duration = 1, 1, 0
    else:
        max_workers = min(4, total_tracks)
        batch_size = 10 if total_tracks >= 20 else total_tracks

        if total_tracks >= 50:
            pause_duration = 30
        elif total_tracks >= 35:
            pause_duration = 10
        elif total_tracks >= 20:
            pause_duration = 5
        else:
            pause_duration = 0

    for i in range(0, len(tasks), batch_size):
        if is_cancelled():
            cancelled_flag[0] = True
            break

        batch_tasks = tasks[i : i + batch_size]
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            list(executor.map(download_single_track, batch_tasks))

        if cancelled_flag[0] or is_cancelled():
            cancelled_flag[0] = True
            break

        if pause_duration > 0 and i + batch_size < len(tasks):
            timestamp = time.strftime("%H:%M:%S")
            log_callback(
                f"[{timestamp}] Downloaded {len(batch_tasks)} tracks. Pausing for {pause_duration}s..."
            )
            for _ in range(pause_duration * 10):
                if is_cancelled():
                    cancelled_flag[0] = True
                    break
                time.sleep(0.1)

    report_progress(100, "-- KB/s", "--:--")

    if cancelled_flag[0] or is_cancelled():
        log_callback("\nDownload stopped / cancelled.")
        return False

    log_callback(f"\n{random_text()}")
    log_callback(f"Saved to: {download_path}")
    return True