# Fetch
A simple python program for downloading media such as audio and video without those stupid websites that constantly redirect you.


# Supported sources
- Youtube
- Soundcloud
- Spotify (Kinda. It only grabs the metadata and tries to download it from youtube.)



# Build instructions
1. Download the ffmpeg and the ffprobe binaries (https://www.gyan.dev/ffmpeg/builds/).
2. Create a folder named bin in the project directory and place both binaries inside it.
3. Make sure you have PyInstaller installed.
4. Open your terminal in the folder mentioned above and run the following command: `python -m PyInstaller --onedir --noconsole --add-binary "bin/ffmpeg.exe;." --add-binary "bin/ffprobe.exe;." fetch.py`
5. Done