# zixora VPN for Windows — scaffold (v0.1, NOT a release)

Standalone zixora VPN PC app for **Windows 10/11 only** (first version).
No Mac build, no Android work in this repo.

## What this is

A Python desktop UI (tkinter, standard library — no GUI dependency to
install) wrapped around a real VPN core binary (sing-box for Windows).
This scaffold does **not** rewrite a VPN protocol. The core binary is
downloaded at CI build time and is **never committed** to this repo.

Screens, mirroring the Android app:
- **Home** — big Connect button, live up/down, elapsed time,
  subscription card with days-left (+ traffic bar when the panel sends
  userinfo), provider card
- **Servers** — server list with server addresses **hidden on rows**
  (same redesign rule as Android), tap to select, latency shown only
  if the core reports it
- **Settings** — sublink paste/import, TUN/system-proxy mode toggle,
  auto-connect, support contact

## Brand (only these colours)

- navy `#091f5b`, primary `#334dae`, mid `#6f96d1`,
  light `#d0e4fd`, glass `#e8f2fe`, white `#fafbff`
- **No gold anywhere.**
- Logo: the user's original Z mark exactly as-is
  (`assets/z_logo_clean.png`, 448x250). It is **never redrawn and never
  resized non-uniformly** — the UI scales it preserving aspect ratio
  (see `branding.py:fit_logo`). Do not force it square.

## Support (no tokens in-app)

Support contact shown in Settings: `@ZixoracustomerserviceBot`
(Telegram) + the zixora Facebook Page. No bot token, password, key,
or sublink is committed to this repo. A sublink the user pastes is
stored only in the local per-user config file on their own PC
(`%APPDATA%/ZixoraVPN/config.json`), never in the repo.

## Build locally on Windows

```powershell
# Requires Python 3.11+ and pip. Run from this repo root.
pip install -r requirements.txt
python -m zixora_pc.app
```

To build a distributable folder/exe (needs the core binary first):

```powershell
# 1. Download the sing-box Windows amd64 release zip, extract
#    sing-box.exe next to the spec (see .github/workflows/build-windows.yml
#    for the exact step; pin SINGBOX_VERSION there).
# 2. Then:
pyinstaller zixora-pc.spec
# Output: dist/ZixoraVPN/ZixoraVPN.exe (+ sing-box.exe beside it)
```

## How CI builds it

`.github/workflows/build-windows.yml` runs on `windows-latest`:
Python setup -> `pip install pyinstaller` -> download the pinned
sing-box Windows release -> PyInstaller folder build -> upload the
`dist/ZixoraVPN` folder as a workflow artifact and stage it as a
release asset. **CI does not create a GitHub release by itself** —
a release is created manually from the artifact (the parent process
does this via the browser, same as the Android flow).

## Honest warnings (tell customers this, do not hide it)

- **Admin rights:** TUN mode needs "Run as administrator". Without
  admin, the app falls back to system-proxy mode (browser/apps that
  respect the system proxy only). See `core.py` — TUN wiring is a
  stub in v0.1 (see BUILD-REPORT.md).
- **SmartScreen:** the exe is **not code-signed** (no certificate),
  so Windows SmartScreen will show an "unknown publisher" warning on
  first run. Users must click "More info -> Run anyway". This is
  expected until/unless a code-signing certificate is bought.
- **Antivirus:** a bundled VPN core exe can trigger a false positive
  on some AV products. The exe is the stock sing-box release, nothing
  else is bundled.
- **Simultaneous use:** phone + PC at the same time on one key is
  limited by the panel/server device limit, not by this app. Using
  both at once may disconnect one of them.
- **First-run test is the real QA gate:** a successful CI build is
  NOT "verified". The user must run it on his own PC (connect,
  browse, disconnect, restart, re-select server) before any
  customer distribution — same rule as the Android builds.

## Test checklist (user's PC)

- [ ] App opens, logo undistorted, brand colours only
- [ ] Paste sublink -> server list appears, addresses hidden on rows
- [ ] Connect -> status Connected, elapsed timer runs, traffic moves
- [ ] Browse a site while connected; disconnect -> browsing stops
      going through the VPN (check IP change)
- [ ] Restart app -> sublink + selected server remembered
- [ ] Subscription card shows days-left; traffic bar only if the
      panel sends userinfo (otherwise it is hidden, not faked)
- [ ] Settings -> support contact shows @ZixoracustomerserviceBot
- [ ] Run as admin -> TUN mode selectable; without admin -> clear
      message, system-proxy fallback offered
