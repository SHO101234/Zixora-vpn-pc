"""Local config for zixora PC.

Stored ONLY on the user's own PC, never in the repo:
  Windows: %APPDATA%/ZixoraVPN/config.json
  Other:   ~/.config/zixoravpn/config.json

Contents: sublink (user-pasted), selected server id, settings
toggles. No passwords, tokens, or keys are ever written here by
this app — the sublink itself is the user's own credential and
stays on their machine.
"""

import json
import os
from pathlib import Path


def config_path():
    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(appdata) / "ZixoraVPN" / "config.json"
    return Path.home() / ".config" / "zixoravpn" / "config.json"


DEFAULTS = {
    "sublink": "",
    "selected_server": "",
    "tun_mode": False,
    "auto_connect": False,
}


def load():
    cfg = dict(DEFAULTS)
    try:
        with open(config_path(), encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            for key in DEFAULTS:
                if key in data:
                    cfg[key] = data[key]
    except (OSError, ValueError):
        pass
    return cfg


def save(cfg):
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    # Keep only known keys; never persist anything else.
    clean = {key: cfg.get(key, DEFAULTS[key]) for key in DEFAULTS}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(clean, f, indent=2)
    return path
