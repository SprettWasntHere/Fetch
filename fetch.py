import sys
import os
import ctypes
from time import sleep
import yt_dlp

def art():
    pawPrint = [
        "⠀⠀⠀⠀⣀⡀",
        "⢠⣤⡀⣾⣿⣿⠀⣤⣤⡄",
        "⢿⣿⡇⠘⠛⠁⢸⣿⣿⠃",
        "⠈⣉⣤⣾⣿⣿⡆⠉⣴⣶⣶",
        "⣾⣿⣿⣿⣿⣿⣿⡀⠻⠟⠃",
        "⠙⠛⠻⢿⣿⣿⣿⡇",
        "⠀⠀⠀⠀⠈⠙⠋⠁"
    ]

    for line in pawPrint:
        print(line)
        sleep(0.05)

def download_media(url, audioFormat):
    download_path = os.path.join(os.path.expanduser('~'), 'Downloads')
    if not os.path.exists(download_path):
        download_path = os.getcwd()

    ydl_opts = {
        'outtmpl': os.path.join(download_path, '%(title)s.%(ext)s')
    }

    if audioFormat:
        ydl_opts.update({
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': audioFormat,
                'preferredquality': '192',
            }],
        })
    else:
        ydl_opts['format'] = 'bestvideo+bestaudio/best'
        ydl_opts['merge_output_format'] = 'mp4'

    print(f"\nFetching from: {url}\n")

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        
        currentFolder = os.path.abspath(download_path)

        art()
        print("\nMedia fetched!")
        print(f"Saved to: {currentFolder}")
        
    except Exception as e:
        print(f"\nAn error occurred: {e}", file=sys.stderr)
        
    finally:
        print("\n" + "="*30)
        input("Press Enter to close...")

def main():
    if sys.platform.startswith('win'):
        try:
            myappid = 'Sprett.FetchMedia'
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except Exception:
            pass

    print("Media Fetcher\n")
    
    url = input("Enter the media URL: ").strip()
    if not url:
        print("URL cannot be empty. Exiting.")
        input("Press Enter to close...")
        return

    print("\nSelect download format:")
    print("1. Video (MP4)")
    print("2. Audio (MP3)")
    print("3. Audio (WAV)")
    
    choice = input("Enter choice (1-3) [Default: 1]: ").strip()

    if choice == '2':
        audioFormat = 'mp3'
    elif choice == '3':
        audioFormat = 'wav'
    else:
        audioFormat = None

    download_media(url, audioFormat)

if __name__ == '__main__':
    main()