# ResidentialIP

Routes **all traffic** on your Windows laptop through a static residential IP in Lincoln, UK using [tun2socks](https://github.com/xjasonlyu/tun2socks) + [wintun](https://wintun.net).

Unlike a browser proxy, this captures every application — browsers, Discord, games, CLI tools, everything.

---

## How it works

```
Your apps
   |
   v
Windows routing table  (0.0.0.0/0 → TUN adapter)
   |
   v
tun2socks  (reads packets from TUN, sends via SOCKS5)
   |
   v
Residential proxy in Lincoln, UK
   |
   v
Internet
```

The proxy host itself is exempted from the tunnel route (direct via your real gateway) to avoid a routing loop.

---

## Requirements

- Windows 10/11
- Python 3.8+
- A **static residential SOCKS5 proxy** with a Lincoln, UK exit IP

### Proxy providers with city-level targeting (Lincoln, GB)

| Provider | City targeting | Notes |
|---|---|---|
| Bright Data | Yes | Username encodes location: `user-country-gb-city-lincoln` |
| Oxylabs | Yes | Dedicated static residential endpoints |
| IPRoyal | Yes | Supports city-level static IPs |
| Soax | Yes | City targeting via dashboard |

Set the port to **SOCKS5** (not HTTP) in your provider dashboard.

---

## Setup

**1. Install Python dependencies**
```
pip install -r requirements.txt
```

**2. Download binaries (tun2socks + wintun)**
```
python setup.py
```
This creates `bin/tun2socks.exe` and `bin/wintun.dll`.

**3. Configure your proxy**
```
copy config.json.example config.json
```
Edit `config.json`:
```json
{
  "proxy": {
    "host": "gate.your-provider.com",
    "port": 1080,
    "username": "user-country-gb-city-lincoln",
    "password": "yourpassword"
  }
}
```

**4. Verify your IP before starting** (optional)
```
python check_ip.py
```

---

## Running

```
python tunnel.py
```

The script automatically requests Administrator privileges (required to modify the routing table). It will:

1. Print your current IP
2. Start tun2socks and configure the TUN adapter
3. Redirect all traffic through Lincoln, UK
4. Confirm the new IP is residential/Lincoln
5. Monitor every 60 seconds and restart tun2socks if it dies
6. Restore original routing when you press Ctrl+C

---

## Files

| File | Purpose |
|---|---|
| `tunnel.py` | Main tunnel manager — run this |
| `setup.py` | One-time download of tun2socks + wintun |
| `check_ip.py` | Quick IP/location check |
| `config.json` | Your proxy credentials (not committed) |
| `config.json.example` | Template for config.json |
| `bin/tun2socks.exe` | Tunnel binary (created by setup.py) |
| `bin/wintun.dll` | WinTUN kernel driver (created by setup.py) |

---

## Troubleshooting

**"Could not determine default gateway"** — Run `route print` and check you have an active network connection.

**IP check shows wrong city** — Your proxy provider may need city targeting explicitly set in the username or dashboard. Confirm the endpoint is configured for `city=Lincoln, country=GB`.

**tun2socks keeps restarting** — Check `bin/tun2socks.exe` exists and that your proxy credentials in `config.json` are correct. Test the proxy directly: `curl --socks5 user:pass@host:port https://api.ipify.org`.

**No internet after Ctrl+C** — Routes should be cleaned up automatically. If not, run: `route delete 0.0.0.0 mask 0.0.0.0 198.18.0.1`
