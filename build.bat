@echo off
echo Building with PyInstaller
python -m PyInstaller --onedir --noconsole --icon="assets/icon.ico" --add-binary "bin/ffmpeg.exe;bin" --add-binary "bin/ffprobe.exe;bin" --add-data "assets/icon.ico;assets" --add-data "assets/icon.png;assets" fetch.py
echo Build complete.
pause