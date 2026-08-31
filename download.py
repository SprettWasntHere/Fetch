import os
import shutil
from concurrent.futures import ThreadPoolExecutor
import yt_dlp
import time

def run_download(url, format_choice, download_path, log_callback, resource_path_func, progress_callback = None):
    audio_format = "mp3" if "MP3" in format_choice else ("wav" if "WAV" in format_choice else None)
    embed_cover = "Cover" in format_choice

    log_callback(f"Analyzing URL: {url}")
    
    try:
        pre_opts = {"quiet": True, "no_warnings": True, "extract_flat": "in_playlist"}
        bundled_ffmpeg_dir = resource_path_func("bin")
        if shutil.which("ffmpeg", path=bundled_ffmpeg_dir):
            pre_opts["ffmpeg_location"] = bundled_ffmpeg_dir

        with yt_dlp.YoutubeDL(pre_opts) as ydl:
            info = ydl.extract_info(url, download=False)
        
        if not info:
            log_callback("Failed to extract metadata.")
            return False

        is_playlist = 'entries' in info or info.get('_type') in ['playlist', 'multi_video'] or bool(info.get('playlist_title') or info.get('album'))

        if is_playlist and 'entries' in info:
            track_urls = [entry.get('url') or f"https://www.youtube.com/watch?v={entry.get('id')}" for entry in info['entries']]
            playlist_name = info.get('playlist_title') or info.get('title') or info.get('album') or 'Playlist'
            target_dir = os.path.join(download_path, playlist_name)
        else:
            track_urls = [url]
            target_dir = download_path
            playlist_name = "Single"

        os.makedirs(target_dir, exist_ok=True)
        total_tracks = len(track_urls)
        completed_tracks = [0]

        if len(track_urls) > 1:
            log_callback(f"Found playlist with {len(track_urls)} tracks.")

        def download_single_track(track_url):
            track_opts = {
                "quiet": True,
                "no_warnings": True,
                "concurrent_fragment_downloads": 4,
                "outtmpl": os.path.join(target_dir, '%(title)s [%(id)s].%(ext)s'),
            }

            if bundled_ffmpeg_dir and os.path.exists(bundled_ffmpeg_dir):
                track_opts["ffmpeg_location"] = bundled_ffmpeg_dir

            if audio_format:
                fallback_album = playlist_name if playlist_name != "Single" else os.path.basename(target_dir) or "Single"

                track_opts["format"] = "bestaudio/best"
                track_opts["embedmetadata"] = True
                track_opts["postprocessors"] = [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": audio_format,
                        "preferredquality": "192",
                    },
                    {
                        "key": "FFmpegMetadata",
                    }
                ]
                
                track_opts["postprocessor_args"] = [
                    "-metadata", f"album={fallback_album}"
                ]

                if embed_cover:
                    track_opts["writethumbnail"] = True
                    track_opts["embedthumbnail"] = True
                    track_opts["outtmpl"] = {
                        "default": os.path.join(target_dir, '%(title)s [%(id)s].%(ext)s'),
                        "thumbnail": os.path.join(target_dir, '%(title)s [%(id)s]')
                    }
                    track_opts["postprocessor_args"].extend(["-id3v2_version", "3", "-write_id3v1", "1"])
                    track_opts["postprocessors"].append({"key": "EmbedThumbnail"})
            else:
                track_opts["format"] = "bestvideo+bestaudio/best"
                track_opts["merge_output_format"] = "mp4"

            logged_files = set()

            def ydl_hook(d):
                timestamp = time.strftime("%H:%M:%S")
                if d['status'] == 'downloading':
                    filename = os.path.basename(d.get('filename', 'file'))
                    if filename not in logged_files:
                        log_callback(f"[{timestamp}] Downloading: {filename}")
                        logged_files.add(filename)
                    
                    total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate')
                    downloaded_bytes = d.get('downloaded_bytes', 0)
                    if total_bytes and progress_callback:
                        track_fraction = (downloaded_bytes / total_bytes) / total_tracks
                        base_progress = (completed_tracks[0] / total_tracks) * 100
                        current_progress = base_progress + (track_fraction * 100)
                        progress_callback(current_progress)

                elif d['status'] == 'finished':
                    log_callback(f"[{timestamp}] Finished processing: {os.path.basename(d.get('filename', 'file'))}")

            track_opts["progress_hooks"] = [ydl_hook]

            try:
                with yt_dlp.YoutubeDL(track_opts) as ydl:
                    ydl.download([track_url])
                completed_tracks[0] += 1
                if progress_callback:
                    progress_callback((completed_tracks[0] / total_tracks) * 100)
            except Exception as e:
                log_callback(f"Error downloading track: {e}")
                completed_tracks[0] += 1

        max_workers = min(4, len(track_urls)) if track_urls else 1
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            executor.map(download_single_track, track_urls)

        if progress_callback:
            progress_callback(100)

        log_callback("\nMedia fetched successfully!")
        log_callback(f"Saved to: {target_dir}")
        return True

    except Exception as e:
        log_callback(f"\nAn error occurred: {e}")
        return False