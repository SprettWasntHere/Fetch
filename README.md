# Fetch
A simple python program for downloading media such as audio and video using yt-dlp.
It has UI based on the Windows 95 operating system (super cool).
It supports playlist downloads if you use the link to the playlist.


# Why use this?
Some sites make downloading a video or audio paywalled (for some reason), and the websites that are made for downloading the videos or audio from these sites are really agressive with their ads.
Fetch is an ad-free alternative to these sites, enjoy your free downloading.
Also it supports file-embedded metadata, that's cool.


# Supported sources
- Anything with a media link (Youtube, Soundcloud, Tiktok, etc.)
- Spotify (Kinda. It only grabs the metadata and tries to download it from youtube because spotify tracks are encrypted and hosted behind closed APIs.)


# Build instructions
1. Download the project zip or use git clone to download the repo.
2. Open your terminal in the project directory.
3. Make sure you have PyInstaller installed.
4. Open your terminal in the folder mentioned above and run the following command: `python -m PyInstaller --onedir --noconsole --icon="media/icon.ico" --add-binary "bin/ffmpeg.exe;bin" --add-binary "bin/ffprobe.exe;bin" --add-data "media/icon.ico;media" --add-data "media/icon.png;media" fetch.py`
5. Done
