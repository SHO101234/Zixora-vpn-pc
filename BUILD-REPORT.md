# BUILD REPORT — zixora VPN for Windows (scaffold v0.1)

Date: 2026-10-29. Status: **SCAFFOLD ONLY — not a release, not
tested on Windows, not pushed anywhere, no GitHub release created.**
The parent agent owns pushing and any release; this report is the
handoff for that step.

## Files created (~/workspace/zixora-pc-app/)

- `README.md` — build instructions (local + CI), honest
  admin/SmartScreen warnings, user's-PC test checklist
- `requirements.txt` — build-time only: pyinstaller (runtime is
  tkinter from the Python standard library, no GUI dependency)
- `run.py` — PyInstaller entry point
- `zixora-pc.spec` — PyInstaller folder build (NOT onefile, so
  sing-box.exe stays beside the app exe and can be launched)
- `.github/workflows/build-windows.yml` — windows-latest: Python
  3.12, pip install pyinstaller, download pinned sing-box Windows
  amd64 release at build time, PyInstaller build, stage core exe,
  upload `dist/ZixoraVPN` as a workflow artifact. No release step.
- `zixora_pc/__init__.py`
- `zixora_pc/branding.py` — palette ONLY (navy #091f5b, primary
  #334dae, mid #6f96d1, light #d0e4fd, glass #e8f2fe, white
  #fafbff; no gold); `fit_logo()` preserves aspect ratio
- `zixora_pc/subscription.py` — subscription-userinfo parsing,
  days-left, traffic usage, byte formatting; returns None when
  the panel sends nothing (never faked)
- `zixora_pc/config.py` — local-only config
  (%APPDATA%/ZixoraVPN/config.json on Windows): sublink, selected
  server, tun/auto toggles. No tokens/keys/passwords written.
- `zixora_pc/core.py` — sublink fetch + parse (vless/vmess/trojan/
  ss), sing-box config builder, core process start/stop,
  elapsed time, admin check, core-exe lookup, system-proxy
  set on connect / restore on disconnect in system-proxy mode
  (TUN mode skips the proxy step, as TUN routes traffic itself)
- `zixora_pc/sysproxy.py` — NEW (2026-10-29, stub-3 fix):
  Windows system-proxy set/unset for system-proxy mode, stdlib
  only (winreg + WinINet notify). See "System-proxy — implemented
  (Windows-only, PC test still required)" below.
- `zixora_pc/app.py` — tkinter UI: Home (big Connect, status,
  up/down + elapsed, subscription card), Servers (names + protocol
  ONLY, addresses never shown), Settings (sublink paste/fetch,
  TUN + auto toggles, support @ZixoracustomerserviceBot)
- `assets/z_logo_clean.png` — user's original Z mark copied as-is
  (448x250, 50 KB). Never redrawn; UI scales it preserving ratio.

## Verified in this VM (2026-10-29)

- All Python files compile (`py_compile` pass).
- Unit-style checks pass: userinfo parse/traffic/days-left,
  logo aspect-ratio preservation, sublink base64 parse
  (vless + trojan names/protocols), empty-body handling.
- Secrets scan: no committed token, key, password, or sublink.
  Grep hits for the word "password" are only runtime field names
  for user-supplied link data, not values.
- tkinter imports on this VM. **The GUI was NOT run end-to-end
  here (headless Linux VM, no display) and the app has NEVER run
  on Windows yet.**

## Implemented vs stubbed — honest list

IMPLEMENTED:
- Brand palette + aspect-preserving logo
- Sublink fetch + parse, server list (addresses hidden)
- Subscription card logic (days-left, traffic bar, hidden when absent)
- Local config load/save, Settings toggles, support contact display
- Core process start/stop with generated sing-box config
  (vless/trojan/ss full, vmess basic), elapsed timer, admin check
- System-proxy set/unset (Windows-only, see section below)
- CI workflow + PyInstaller spec + README + test checklist

STUBBED / NOT YET WIRED (do not claim otherwise):
1. **Live up/down traffic** — `CoreManager.traffic()` returns
   (0, 0). Not wired to any sing-box stats/Clash API yet. The UI
   shows 0, never invented numbers.
2. **TUN mode** — intent + admin check only; the TUN inbound
   block in the sing-box config is marked `_tun_stub`. Working
   path in v0.1 is system-proxy mode (mixed inbound 127.0.0.1:2080
   + system-proxy set/unset, implemented 2026-10-29 — see below).
3. **Latency/ping on server rows** — not implemented (no field).
4. **Sing-box version pin** — workflow pins SINGBOX_VERSION
   1.12.0; this version string was NOT verified against a live
   release list in this task. Verify it exists before the first
   CI run and fix the pin if needed.
5. **Auto-connect on start, icon file (.ico)** — not implemented
   (auto-connect toggle is saved but not acted on at startup).
6. **No Windows test at all** — first run on the user's PC is the
   real QA gate (README checklist).

## System-proxy — implemented 2026-10-29 (Windows-only, PC test still required)

Stub 3 from the original report is now implemented in local
files only (NOT pushed, NOT released):

- New module `zixora_pc/sysproxy.py` (`SystemProxy` class):
  on connect in system-proxy mode it snapshots the current
  ProxyEnable / ProxyServer / ProxyOverride values (including
  which values were absent) to memory AND to a marker file
  (workdir `.zixora-proxy-saved.json`), then sets ProxyEnable=1,
  ProxyServer=`127.0.0.1:2080`, ProxyOverride=`<local>`, and
  notifies WinINet (InternetSetOptionW 39 + 37).
- `CoreManager.start()` (system-proxy mode, Windows only):
  if the proxy set fails, the core is stopped again and connect
  FAILS — it never reports "Connected" without routing. TUN mode
  skips the proxy step entirely.
- `CoreManager.stop()` always attempts proxy restore FIRST, even
  if stopping the core fails; `App` window-close (`WM_DELETE_WINDOW`)
  calls `stop()` before destroying the window.
- Crash recovery: on next start, `CoreManager` calls
  `restore_stale()` — if a marker exists AND the current proxy
  still points at `127.0.0.1:2080`, the saved settings are
  restored. If the user changed the proxy since the crash, their
  settings are left alone and the marker is dropped.
- On non-Windows platforms all sysproxy functions are safe
  no-ops (verified on this Linux VM: set returns "Windows-only",
  restore is a no-op, stale-restore is False).

NOT verified (honest): the winreg writes and WinINet notify call
have NEVER run on Windows — they are implemented from the
documented API only. A PAC setup (AutoConfigURL) is deliberately
not touched, so if a PAC URL is active Windows may prefer it over
the manual proxy. Remaining stubs after this change: live traffic
(0), TUN inbound, latency, auto-connect, .ico icon.

## PC test checklist — system proxy (user's PC, the real gate)

1. Before connect: note the current proxy state (Windows
   Settings → Network → Proxy; and, if the user had a proxy
   before, what it was).
2. Paste sublink, pick a server, press CONNECT (system-proxy
   mode, NOT TUN). App must show Connected.
3. Check Windows Proxy settings: manual proxy ON, address
   `127.0.0.1`, port `2080`. Open a website — it must load
   THROUGH the VPN (e.g. check IP/location changes vs before).
   Note: the app's own up/down counters still show 0 (traffic
   stub) — judge by the website/IP, not by the counters.
4. Press DISCONNECT. Windows Proxy settings must be back to
   exactly what they were before step 2 (OFF if they were OFF,
   or the previous proxy if one was set). Open a website again
   — it must load normally WITHOUT the VPN.
5. Close the app window while connected (instead of
   Disconnect): on next launch, the proxy must already be
   restored (crash-recovery path) — check Proxy settings before
   connecting again.
6. If step 3 loads nothing, or step 4 leaves the proxy at
   127.0.0.1:2080, STOP and report it — do not hand the build
   to customers.

## Exact next step to get a first CI test build

1. Parent pushes `~/workspace/zixora-pc-app/` to a GitHub repo
   (suggested: a new repo, e.g. SHO101234/Zixora-vpn-pc, or a
   `pc/` branch — parent's call; do NOT push into the Android
   repo's main by accident).
2. Verify SINGBOX_VERSION 1.12.0 exists at
   github.com/SagerNet/sing-box/releases; fix the pin if not.
3. Trigger the workflow (push to main or workflow_dispatch).
4. Download the `ZixoraVPN-windows` artifact; run it on the
   user's PC as admin + non-admin and work through the README
   test checklist. Fix stubs 1–3 and 5 before any customer build.
5. Only then create a GitHub release manually from the tested
   artifact (CI deliberately has no release step).
