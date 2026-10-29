"""Windows system-proxy set/unset for system-proxy mode.

The sing-box core listens on a local mixed inbound
(127.0.0.1:2080 — see core.MIXED_PORT). In system-proxy mode the
app must point Windows at that inbound on connect and restore the
user's previous proxy settings exactly on disconnect, or traffic
will NOT actually route through the core despite "Connected" —
and a stale proxy left behind would point at a dead local port.

Mechanism (Windows standard, stdlib only):
- Registry key HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\
  Internet Settings, values ProxyEnable (DWORD), ProxyServer
  (string), ProxyOverride (string).
- After any change, WinINet is told the settings changed via
  InternetSetOptionW (INTERNET_OPTION_SETTINGS_CHANGED = 39 and
  INTERNET_OPTION_REFRESH = 37) so browsers/apps pick it up
  without a logoff.

Crash safety:
- The previous settings are snapshotted in memory AND written to
  a small marker file (workdir/.zixora-proxy-saved.json) before
  anything is changed.
- On a clean disconnect the snapshot is restored and the marker
  is deleted.
- On app start, if a marker exists AND the current proxy still
  points at our local inbound, the marker snapshot is restored
  (this is the crash-recovery path). If the user changed the
  proxy themselves after a crash, the current value will differ
  from ours and we leave it alone.

Non-Windows platforms (e.g. this Linux build VM): every function
is a safe no-op returning (False, "Windows only"). Nothing is
written to any registry, because there is none.

HONEST LIMIT: this module is Windows-only and has NOT been run
on Windows yet — the registry writes and the WinINet notify call
are implemented from the documented API but are untested on a
real Windows machine. The user's PC test is the real gate.
A PAC setup (AutoConfigURL) is deliberately NOT touched: if a
PAC URL is active, Windows may prefer it over the manual proxy,
so the PC test checklist must check that traffic actually flows.
"""

import json
import os
import sys

PROXY_HOST = "127.0.0.1"
PROXY_PORT = 2080  # must match core.MIXED_PORT
PROXY_VALUE = f"{PROXY_HOST}:{PROXY_PORT}"
PROXY_OVERRIDE = "<local>"  # bypass proxy for local addresses

_REG_PATH = (r"Software\Microsoft\Windows\CurrentVersion"
             r"\Internet Settings")
_SNAPSHOT_VALUES = ("ProxyEnable", "ProxyServer", "ProxyOverride")
_MARKER_NAME = ".zixora-proxy-saved.json"


def _is_windows():
    return sys.platform == "win32"


def _notify_changed():
    """Tell WinINet the proxy settings changed. Best-effort."""
    if not _is_windows():
        return
    try:
        import ctypes
        wininet = ctypes.windll.wininet
        # INTERNET_OPTION_SETTINGS_CHANGED = 39, REFRESH = 37
        wininet.InternetSetOptionW(None, 39, None, 0)
        wininet.InternetSetOptionW(None, 37, None, 0)
    except Exception:
        pass


def _read_snapshot():
    """Read current proxy values. Returns {name: value-or-None}
    where None means the value does not exist."""
    if not _is_windows():
        return {}
    import winreg
    snap = {}
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _REG_PATH) as key:
            for name in _SNAPSHOT_VALUES:
                try:
                    value, _type = winreg.QueryValueEx(key, name)
                    snap[name] = value
                except FileNotFoundError:
                    snap[name] = None
    except OSError:
        # Key missing entirely: treat every value as absent.
        snap = {name: None for name in _SNAPSHOT_VALUES}
    return snap


def _write_snapshot(snap):
    """Write a snapshot back exactly: values that existed are set,
    values that were absent are deleted."""
    if not _is_windows():
        return
    import winreg
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _REG_PATH,
                        0, winreg.KEY_SET_VALUE) as key:
        for name in _SNAPSHOT_VALUES:
            value = snap.get(name)
            if value is None:
                try:
                    winreg.DeleteValue(key, name)
                except FileNotFoundError:
                    pass
            elif name == "ProxyEnable":
                winreg.SetValueEx(key, name, 0, winreg.REG_DWORD,
                                  int(value))
            else:
                winreg.SetValueEx(key, name, 0, winreg.REG_SZ,
                                  str(value))


def _marker_path(workdir):
    return os.path.join(workdir or os.getcwd(), _MARKER_NAME)


class SystemProxy:
    """Owns one set/restore cycle. One instance per CoreManager."""

    def __init__(self, workdir=None):
        self.workdir = workdir or os.getcwd()
        self._snapshot = None
        self.active = False

    def set_to_local(self):
        """Point the system proxy at 127.0.0.1:2080, saving the
        previous settings first. Returns (ok, message)."""
        if not _is_windows():
            return False, "System proxy is Windows-only (skipped)."
        if self.active:
            return False, "System proxy already set by this app."
        snap = _read_snapshot()
        try:
            with open(_marker_path(self.workdir), "w",
                      encoding="utf-8") as f:
                json.dump(snap, f)
        except OSError:
            # Marker write failure must not block the set, but the
            # crash-recovery path then relies on memory only.
            pass
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _REG_PATH,
                                0, winreg.KEY_SET_VALUE) as key:
                winreg.SetValueEx(key, "ProxyEnable", 0,
                                  winreg.REG_DWORD, 1)
                winreg.SetValueEx(key, "ProxyServer", 0,
                                  winreg.REG_SZ, PROXY_VALUE)
                winreg.SetValueEx(key, "ProxyOverride", 0,
                                  winreg.REG_SZ, PROXY_OVERRIDE)
        except OSError as exc:
            return False, f"Could not set system proxy: {exc}"
        _notify_changed()
        self._snapshot = snap
        self.active = True
        return True, f"System proxy set to {PROXY_VALUE}"

    def restore(self):
        """Restore the previous settings exactly. Safe to call when
        nothing was set (no-op). Returns (ok, message)."""
        if not _is_windows():
            return True, "System proxy is Windows-only (nothing to restore)."
        if not self.active and self._snapshot is None:
            return True, "System proxy was not set by this app."
        snap = self._snapshot
        if snap is None:
            # No in-memory snapshot (e.g. fresh instance): try marker.
            try:
                with open(_marker_path(self.workdir),
                          encoding="utf-8") as f:
                    snap = json.load(f)
            except (OSError, ValueError):
                return False, ("No previous proxy settings saved; "
                               "not changing the system proxy.")
        try:
            _write_snapshot(snap)
        except OSError as exc:
            return False, f"Could not restore system proxy: {exc}"
        _notify_changed()
        self._snapshot = None
        self.active = False
        try:
            os.remove(_marker_path(self.workdir))
        except OSError:
            pass
        return True, "System proxy restored"

    def restore_stale(self):
        """Crash-recovery: if a marker from a previous run exists
        AND the current proxy still points at our local inbound,
        restore the marker snapshot. Returns True if restored."""
        if not _is_windows():
            return False
        marker = _marker_path(self.workdir)
        if not os.path.isfile(marker):
            return False
        current = _read_snapshot()
        if current.get("ProxyServer") != PROXY_VALUE:
            # User (or another app) changed the proxy since the
            # crash — leave their settings alone, drop the marker.
            try:
                os.remove(marker)
            except OSError:
                pass
            return False
        try:
            with open(marker, encoding="utf-8") as f:
                snap = json.load(f)
            _write_snapshot(snap)
        except (OSError, ValueError):
            return False
        _notify_changed()
        try:
            os.remove(marker)
        except OSError:
            pass
        return True
