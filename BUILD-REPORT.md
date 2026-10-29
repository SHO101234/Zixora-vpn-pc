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
  elapsed time, admin check, core-exe lookup
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
- CI workflow + PyInstaller spec + README + test checklist

STUBBED / NOT YET WIRED (do not claim otherwise):
1. **Live up/down traffic** — `CoreManager.traffic()` returns
   (0, 0). Not wired to any sing-box stats/Clash API yet. The UI
   shows 0, never invented numbers.
2. **TUN mode** — intent + admin check only; the TUN inbound
   block in the sing-box config is marked `_tun_stub`. Working
   path in v0.1 is system-proxy mode (mixed inbound 127.0.0.1:2080).
   NOTE: the generated config does not yet set the Windows system
   proxy on connect / unset it on disconnect — that step must be
   added before customers use it, or traffic will not actually
   route through the core despite "Connected".
3. **Latency/ping on server rows** — not implemented (no field).
4. **Sing-box version pin** — workflow pins SINGBOX_VERSION
   1.12.0; this version string was NOT verified against a live
   release list in this task. Verify it exists before the first
   CI run and fix the pin if needed.
5. **System-proxy set/unset, auto-connect on start, icon file
   (.ico)** — not implemented (auto-connect toggle is saved but
   not acted on at startup).
6. **No Windows test at all** — first run on the user's PC is the
   real QA gate (README checklist).

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
