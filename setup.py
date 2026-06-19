"""
Downloads tun2socks.exe and wintun.dll into bin/.
Run once before using tunnel.py.
"""
import io
import os
import sys
import zipfile

import requests

GITHUB_API = "https://api.github.com/repos/xjasonlyu/tun2socks/releases/latest"
WINTUN_URL = "https://wintun.net/builds/wintun-0.14.1.zip"


def download_tun2socks():
    print("Fetching latest tun2socks release from GitHub...")
    r = requests.get(GITHUB_API, timeout=30)
    r.raise_for_status()
    assets = r.json()["assets"]

    asset = next((a for a in assets if "windows-amd64" in a["name"] and a["name"].endswith(".zip")), None)
    if not asset:
        print("ERROR: Could not find windows-amd64 zip asset in latest release.")
        print("Assets found:", [a["name"] for a in assets])
        sys.exit(1)

    print(f"Downloading {asset['name']} ...")
    data = requests.get(asset["browser_download_url"], timeout=120).content

    with zipfile.ZipFile(io.BytesIO(data)) as z:
        exe = next((n for n in z.namelist() if n.endswith(".exe")), None)
        if not exe:
            print("ERROR: No .exe found inside zip.")
            sys.exit(1)
        with z.open(exe) as src, open(r"bin\tun2socks.exe", "wb") as dst:
            dst.write(src.read())
    print("  -> bin/tun2socks.exe")


def download_wintun():
    print(f"Downloading wintun from {WINTUN_URL} ...")
    data = requests.get(WINTUN_URL, timeout=60).content

    with zipfile.ZipFile(io.BytesIO(data)) as z:
        target = "wintun/bin/amd64/wintun.dll"
        if target not in z.namelist():
            print("ERROR: Expected path not found in wintun zip.")
            print("Contents:", z.namelist())
            sys.exit(1)
        with z.open(target) as src, open(r"bin\wintun.dll", "wb") as dst:
            dst.write(src.read())
    print("  -> bin/wintun.dll")


if __name__ == "__main__":
    os.makedirs("bin", exist_ok=True)
    download_tun2socks()
    download_wintun()
    print("\nSetup complete.")
    print("Next: copy config.json.example -> config.json and fill in your proxy details.")
    print("Then run:  python tunnel.py")
