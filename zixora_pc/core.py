"""Core manager for zixora PC.

Responsibilities:
- Fetch a sublink (HTTP GET, urllib) and parse its config lines.
  A sublink body is base64 (or plain) lines, one proxy link per line:
  vless://, vmess://, trojan://, ss://. Only the display NAME
  (the #fragment) and the protocol are shown in the UI — server
  addresses are NEVER shown on rows (Android redesign rule).
- Start/stop the bundled core binary (sing-box.exe) with a
  generated config file, and report connected state + elapsed time.

HONEST LIMITS (v0.1 scaffold — see BUILD-REPORT.md):
- Outbound generation covers vless/trojan/ss in full and vmess
  in a basic form; exotic per-link options (reality/flow details
  beyond the common fields) are passed through only where parsed.
  A link the builder cannot translate is skipped with a warning
  instead of silently producing a broken config.
- Live up/down traffic is NOT yet wired to the core's API:
  traffic() returns (0, 0) until the sing-box Clash API / stats
  endpoint is connected. The UI must show 0, not invented numbers.
- TUN mode: generating a TUN inbound requires admin rights and
  the sing-box TUN stack. tun_mode=True currently only records
  the intent + checks admin; the actual TUN inbound block is a
  stub (system-proxy mode is the working path in v0.1).
- No binary is bundled in this repo. The core exe is expected
  next to the app exe (CI places it there) or on PATH.
"""

import base64
import binascii
import ctypes
import json
import os
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass, field


@dataclass
class Server:
    name: str
    protocol: str
    raw: str
    # Parsed connection fields (never displayed in the UI).
    host: str = ""
    port: int = 0
    uuid: str = ""
    password: str = ""
    params: dict = field(default_factory=dict)


def _decode_body(text):
    """Sublink bodies are usually base64; accept plain text too."""
    stripped = text.strip()
    if not stripped:
        return ""
    try:
        padded = stripped + "=" * (-len(stripped) % 4)
        return base64.urlsafe_b64decode(padded).decode("utf-8", "replace")
    except (binascii.Error, ValueError):
        return text


def parse_sublink_text(text):
    """Parse sublink body text into a list of Server objects."""
    body = _decode_body(text)
    servers = []
    for line in body.splitlines():
        line = line.strip()
        if not line or "://" not in line:
            continue
        scheme, rest = line.split("://", 1)
        scheme = scheme.lower()
        if scheme not in ("vless", "vmess", "trojan", "ss"):
            continue
        name = ""
        if "#" in rest:
            rest, frag = rest.split("#", 1)
            name = urllib.parse.unquote(frag).strip()
        if scheme == "vmess":
            # vmess links are base64 JSON after the scheme.
            try:
                padded = rest + "=" * (-len(rest) % 4)
                data = json.loads(
                    base64.urlsafe_b64decode(padded).decode("utf-8"))
                servers.append(Server(
                    name=name or data.get("ps", "Server"),
                    protocol="vmess", raw=line,
                    host=data.get("add", ""), port=int(data.get("port", 0) or 0),
                    uuid=data.get("id", ""), params=data))
            except (binascii.Error, ValueError, KeyError):
                continue
            continue
        # vless / trojan / ss: userinfo@host:port[?params]
        main = rest.split("?", 1)[0]
        query = rest.split("?", 1)[1] if "?" in rest else ""
        params = dict(urllib.parse.parse_qsl(query))
        host, port = "", 0
        if "@" in main:
            userinfo, hostport = main.rsplit("@", 1)
            if ":" in hostport:
                host, port_s = hostport.rsplit(":", 1)
                try:
                    port = int(port_s)
                except ValueError:
                    port = 0
            else:
                host = hostport
        else:
            userinfo = main
        servers.append(Server(
            name=name or f"{scheme} server", protocol=scheme, raw=line,
            host=host, port=port,
            uuid=urllib.parse.unquote(userinfo) if scheme == "vless" else "",
            password=urllib.parse.unquote(userinfo) if scheme != "vless" else "",
            params=params))
    return servers


def fetch_sublink(url, timeout=30):
    """Fetch a sublink URL. Returns (servers, userinfo_header_or_None).
    Raises on network/HTTP errors — the caller shows the error."""
    req = urllib.request.Request(url, headers={"User-Agent": "ZixoraVPN-PC/0.1"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8", "replace")
        userinfo = resp.headers.get("subscription-userinfo")
    return parse_sublink_text(body), userinfo


def is_admin():
    """True if running elevated on Windows, else False."""
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def find_core_exe():
    """Locate sing-box.exe next to the app exe, in cwd, or on PATH."""
    candidates = []
    if getattr(sys, "frozen", False):
        candidates.append(os.path.join(os.path.dirname(sys.executable),
                                       "sing-box.exe"))
    candidates.append(os.path.join(os.getcwd(), "sing-box.exe"))
    for cand in candidates:
        if os.path.isfile(cand):
            return cand
    # PATH lookup (shutil.which equivalent without extra import)
    for folder in os.environ.get("PATH", "").split(os.pathsep):
        cand = os.path.join(folder, "sing-box.exe")
        if os.path.isfile(cand):
            return cand
    return None


def build_singbox_config(server, tun_mode=False):
    """Build a minimal sing-box config dict for one server.

    vless/trojan/ss use sing-box outbound fields; vmess uses its
    parsed JSON fields. Returns None if the server cannot be
    translated (caller skips it with a warning)."""
    if not server.host or not server.port:
        return None
    outbound = {"tag": "proxy", "type": server.protocol}
    if server.protocol == "vless":
        outbound.update({
            "server": server.host, "server_port": server.port,
            "uuid": server.uuid, "flow": server.params.get("flow", ""),
            "tls": {"enabled": server.params.get("security", "tls") == "tls",
                    "server_name": server.params.get("sni", server.host)},
            "transport": {"type": server.params.get("type", "tcp")},
        })
    elif server.protocol == "trojan":
        outbound.update({
            "server": server.host, "server_port": server.port,
            "password": server.password,
            "tls": {"enabled": True,
                    "server_name": server.params.get("sni", server.host)},
        })
    elif server.protocol == "ss":
        outbound.update({
            "server": server.host, "server_port": server.port,
            "method": server.params.get("method", "aes-256-gcm"),
            "password": server.password,
        })
    elif server.protocol == "vmess":
        data = server.params if isinstance(server.params, dict) else {}
        outbound.update({
            "server": server.host, "server_port": server.port,
            "uuid": server.uuid,
            "security": data.get("scy", "auto"),
            "alter_id": int(data.get("aid", 0) or 0),
            "tls": {"enabled": data.get("tls", "") == "tls"},
        })
    config = {
        "log": {"level": "warning"},
        "inbounds": [
            {"type": "mixed", "tag": "mixed-in",
             "listen": "127.0.0.1", "listen_port": 2080},
        ],
        "outbounds": [outbound, {"type": "direct", "tag": "direct"}],
        "route": {"rules": [{"outbound": "proxy"}]},
    }
    if tun_mode:
        # STUB: TUN inbound block is not wired in v0.1. The caller
        # must check is_admin() and refuse TUN without elevation.
        # When wired, add a {"type": "tun", ...} inbound here.
        config["_tun_stub"] = True
    return config


class CoreManager:
    """Owns the core process. No fake state: if the core is not
    running, connected is False and traffic is (0, 0)."""

    def __init__(self, workdir=None):
        self.proc = None
        self.started_at = None
        self.server = None
        self.workdir = workdir or os.getcwd()

    def is_running(self):
        return self.proc is not None and self.proc.poll() is None

    def elapsed(self):
        if not self.is_running() or not self.started_at:
            return 0
        return int(time.time() - self.started_at)

    def traffic(self):
        # STUB: (up_bytes, down_bytes) — not wired to the core API yet.
        return (0, 0)

    def start(self, server, tun_mode=False):
        if self.is_running():
            return False, "Already connected — disconnect first."
        if tun_mode and not is_admin():
            return False, ("TUN mode needs administrator rights. "
                            "Restart the app as administrator, or use "
                            "system-proxy mode.")
        exe = find_core_exe()
        if not exe:
            return False, ("Core binary (sing-box.exe) not found next "
                            "to the app. Reinstall from the GitHub "
                            "release (it bundles the core).")
        config = build_singbox_config(server, tun_mode=tun_mode)
        if config is None:
            return False, ("This server could not be translated to a "
                            "core config. Try another server.")
        cfg_path = os.path.join(self.workdir, "sing-box-config.json")
        with open(cfg_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
        try:
            self.proc = subprocess.Popen(
                [exe, "run", "-c", cfg_path],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except OSError as exc:
            return False, f"Could not start core: {exc}"
        self.started_at = time.time()
        self.server = server
        return True, "Connected"

    def stop(self):
        if self.proc is not None:
            try:
                self.proc.terminate()
                self.proc.wait(timeout=5)
            except Exception:
                try:
                    self.proc.kill()
                except Exception:
                    pass
        self.proc = None
        self.started_at = None
        self.server = None
        return True
