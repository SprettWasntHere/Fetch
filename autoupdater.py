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

def download_and_execute_update(download_url, asset_name):
    response = requests.get(download_url, stream=True)
    temp_dir = tempfile.gettempdir()
    installer_path = os.path.join(temp_dir, asset_name)

    with open(installer_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)

    subprocess.Popen(
        [installer_path, "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART"]
    )

    sys.exit(0)