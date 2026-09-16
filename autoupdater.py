import os
import subprocess
import sys
import tempfile
import requests

GITHUB_OWNER = "SprettWasntHere"
GITHUB_REPO = "Fetch"

def check_for_updates(current_version, owner, repo):
    url = f"https://api.github.com/repos/{owner}/{repo}/releases/latest"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            latest_version = data["tag_name"].lstrip("v")

            if latest_version != current_version:
                for asset in data["assets"]:
                    if asset["name"].endswith(".exe"):
                        return (
                            latest_version,
                            asset["browser_download_url"],
                            asset["name"],
                        )
    except Exception as error:
        print(f"Update check failed: {error}")

    return None, None, None

def download_and_execute_update(download_url, asset_name, progress_callback=None, log_callback=None):
    response = requests.get(download_url, stream=True)
    response.raise_for_status()
    
    total_size = int(response.headers.get("content-length", 0))
    temp_dir = tempfile.gettempdir()
    installer_path = os.path.join(temp_dir, asset_name)

    downloaded_size = 0
    with open(installer_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
                downloaded_size += len(chunk)
                if total_size > 0 and progress_callback:
                    percent = int((downloaded_size / total_size) * 100)
                    progress_callback(percent)

    if progress_callback:
        progress_callback(100)

    if log_callback:
        log_callback("Update downloaded successfully.")

    subprocess.Popen(
        [installer_path, "/NORESTART"]
    )
    sys.exit(0)