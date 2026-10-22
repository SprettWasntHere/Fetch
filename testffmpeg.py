import os
import subprocess
from shared import *

bundled_ffmpeg_dir = resource_path("bin")
command = f"{bundled_ffmpeg_dir}/ffmpeg.exe -i C:/Users/Elias/Downloads/vine-boom.mp3 C:/Users/Elias/Downloads/vine-boom_converted.wav"

subprocess.call(command,shell=True)