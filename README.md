# Fetch
A simple python script for grabbing media such as audio and video.


# Supported sources
- Youtube
- Soundcloud
- Spotify (kinda)



# Build instructions
1. Place Fetch.py in the same folder as the ffmpeg and ffprobe binaries.
2. Make sure you have PyInstaller installed.
3. Open your terminal in the folder mentioned above and run the following command: `pyinstaller --onefile --console --icon="icon.ico" --add-binary "ffmpeg.exe;." --add-binary "ffprobe.exe;." fetch.py`
4. Done
