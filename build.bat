@echo off
chcp 65001 >nul
type assets\art.txt
echo.
python -m PyInstaller --onedir --noconsole --icon="assets/icon.ico" --add-binary "bin/ffmpeg.exe;bin" --add-binary "bin/ffprobe.exe;bin" --add-data "assets/icon.ico;assets" --add-data "assets/icon.png;assets" --add-data "assets/art.txt;assets" fetch.py
echo.
pause