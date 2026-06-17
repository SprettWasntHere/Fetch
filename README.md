# Fetch
A simple python script for grabbing media such as audio and video.


# Supported sources
- Youtube
- Soundcloud
- Spotify (kinda)



# Build instructions
1. Download the ffmpeg and the ffprobe binaries.
2. Place `fetch.py` in the same folder as the ffmpeg and ffprobe binaries.
3. Make sure you have PyInstaller installed.
4. Open your terminal in the folder mentioned above and run the following command: `pyinstaller --onefile --console --add-binary "ffmpeg.exe;." --add-binary "ffprobe.exe;." fetch.py`
5. Done
