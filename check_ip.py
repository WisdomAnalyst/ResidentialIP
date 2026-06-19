"""Quick check of your current public IP and location."""
import requests


def main():
    try:
        ip = requests.get("https://api.ipify.org?format=json", timeout=10).json()["ip"]
        loc = requests.get(f"https://ipapi.co/{ip}/json/", timeout=10).json()
        print(f"IP      : {ip}")
        print(f"City    : {loc.get('city')}")
        print(f"Region  : {loc.get('region')}")
        print(f"Country : {loc.get('country_name')}")
        print(f"ISP     : {loc.get('org')}")
        print(f"Type    : {loc.get('connection', {}).get('type', 'unknown') if isinstance(loc.get('connection'), dict) else '?'}")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
