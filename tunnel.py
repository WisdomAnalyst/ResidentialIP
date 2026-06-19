"""
Routes all laptop traffic through a SOCKS5 residential proxy using tun2socks.
Must be run as Administrator.

How it works:
  1. tun2socks creates a virtual TUN network adapter (via wintun.dll).
  2. We assign an IP to that adapter and add a default route through it.
  3. To avoid a routing loop, the proxy host itself is exempted and routed
     through the original gateway.
  4. tun2socks forwards all packets received on the TUN adapter out via SOCKS5.
"""
import ctypes
import json
import os
import re
import subprocess
import sys
import time

import requests

ADAPTER_NAME = "ResidentialTUN"
TUN_IP = "198.18.0.1"
TUN_MASK = "255.255.0.0"
CHECK_INTERVAL = 60  # seconds between IP health checks


# ---------------------------------------------------------------------------
# Admin check
# ---------------------------------------------------------------------------

def require_admin():
    try:
        is_admin = ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        is_admin = False

    if not is_admin:
        print("Relaunching as Administrator...")
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, " ".join(f'"{a}"' for a in sys.argv), None, 1
        )
        sys.exit(0)


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def load_config():
    if not os.path.exists("config.json"):
        print("ERROR: config.json not found.")
        print("  Copy config.json.example -> config.json and fill in your proxy details.")
        sys.exit(1)
    with open("config.json") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# IP / location helpers
# ---------------------------------------------------------------------------

def get_ip_info():
    try:
        ip = requests.get("https://api.ipify.org?format=json", timeout=10).json()["ip"]
        loc = requests.get(f"https://ipapi.co/{ip}/json/", timeout=10).json()
        return ip, loc.get("city", "?"), loc.get("region", "?"), loc.get("country_name", "?")
    except Exception:
        return None, None, None, None


# ---------------------------------------------------------------------------
# Routing helpers
# ---------------------------------------------------------------------------

def get_default_gateway():
    """Return the current default IPv4 gateway IP."""
    out = subprocess.check_output(["route", "print", "0.0.0.0"], text=True, stderr=subprocess.DEVNULL)
    for line in out.splitlines():
        parts = line.split()
        # Active Routes table row: Network   Netmask   Gateway   Interface   Metric
        if len(parts) >= 3 and parts[0] == "0.0.0.0" and parts[1] == "0.0.0.0":
            gw = parts[2]
            if re.match(r"^\d+\.\d+\.\d+\.\d+$", gw) and gw != "On-link":
                return gw
    return None


def _run(cmd):
    subprocess.run(cmd, capture_output=True)


def add_routes(proxy_host, original_gateway):
    # Keep proxy traffic on the real NIC (otherwise tun2socks can't reach the proxy)
    _run(["route", "add", proxy_host, "mask", "255.255.255.255", original_gateway, "metric", "1"])
    # Send everything else through the TUN adapter
    _run(["route", "add", "0.0.0.0", "mask", "0.0.0.0", TUN_IP, "metric", "1"])


def remove_routes(proxy_host):
    _run(["route", "delete", proxy_host, "mask", "255.255.255.255"])
    _run(["route", "delete", "0.0.0.0", "mask", "0.0.0.0", TUN_IP])


def configure_tun_adapter():
    """Assign a static IP to the TUN adapter after tun2socks creates it."""
    time.sleep(2)
    _run(["netsh", "interface", "ip", "set", "address",
          ADAPTER_NAME, "static", TUN_IP, TUN_MASK])
    # Use Cloudflare DNS on the TUN adapter to avoid DNS leaks
    _run(["netsh", "interface", "ip", "set", "dns", ADAPTER_NAME, "static", "1.1.1.1"])


# ---------------------------------------------------------------------------
# tun2socks process
# ---------------------------------------------------------------------------

def start_tun2socks(proxy):
    socks5 = (
        f"socks5://{proxy['username']}:{proxy['password']}"
        f"@{proxy['host']}:{proxy['port']}"
    )
    cmd = [
        r"bin\tun2socks.exe",
        "-device", f"tun://{ADAPTER_NAME}",
        "-proxy", socks5,
        "-loglevel", "warning",
    ]
    return subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def ts():
    return time.strftime("%H:%M:%S")


def main():
    require_admin()
    config = load_config()
    proxy = config["proxy"]

    if not os.path.exists(r"bin\tun2socks.exe"):
        print("ERROR: bin/tun2socks.exe not found. Run: python setup.py")
        sys.exit(1)
    if not os.path.exists(r"bin\wintun.dll"):
        print("ERROR: bin/wintun.dll not found. Run: python setup.py")
        sys.exit(1)

    # wintun.dll must be in the same directory as tun2socks.exe (bin/)
    # tun2socks finds it automatically when launched from that directory.

    print("=== ResidentialIP Tunnel ===\n")

    print("IP before tunnel:")
    ip, city, region, country = get_ip_info()
    print(f"  {ip}  |  {city}, {region}, {country}\n")

    original_gateway = get_default_gateway()
    if not original_gateway:
        print("ERROR: Could not determine your default gateway from the routing table.")
        sys.exit(1)
    print(f"Original gateway : {original_gateway}")
    print(f"Proxy            : {proxy['host']}:{proxy['port']}")
    print(f"TUN adapter IP   : {TUN_IP}\n")

    print("Starting tun2socks...")
    proc = start_tun2socks(proxy)
    configure_tun_adapter()
    add_routes(proxy["host"], original_gateway)

    print("Waiting for tunnel to stabilise...")
    time.sleep(4)

    ip, city, region, country = get_ip_info()
    print(f"\nIP through tunnel:")
    print(f"  {ip}  |  {city}, {region}, {country}")

    if city and "Lincoln" in city and "United Kingdom" in (country or ""):
        print("\nConfirmed: Lincoln, UK residential IP active.")
    else:
        print(f"\nWARNING: Expected Lincoln, UK — got {city}, {country}.")
        print("Check your proxy provider's geo-targeting settings (city=Lincoln, country=GB).")

    print(f"\nMonitoring every {CHECK_INTERVAL}s — Ctrl+C to stop.\n")

    try:
        while True:
            time.sleep(CHECK_INTERVAL)

            if proc.poll() is not None:
                print(f"[{ts()}] tun2socks stopped unexpectedly — restarting...")
                proc = start_tun2socks(proxy)
                configure_tun_adapter()
                time.sleep(3)

            ip, city, region, country = get_ip_info()
            ok = city and "Lincoln" in city
            flag = "OK  " if ok else "WARN"
            print(f"[{ts()}] [{flag}] {ip}  |  {city}, {region}, {country}")

    except KeyboardInterrupt:
        print("\nShutting down...")

    finally:
        proc.terminate()
        remove_routes(proxy["host"])
        print("Tunnel closed. Original routing restored.")


if __name__ == "__main__":
    main()
