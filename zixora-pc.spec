# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for zixora VPN for Windows.
# Build on Windows only:  pyinstaller zixora-pc.spec
# The sing-box core binary must sit next to this spec (or in dist
# staging) at build time — CI downloads it; it is never committed.
# Output: dist/ZixoraVPN/ZixoraVPN.exe + sing-box.exe beside it
# (folder build, NOT onefile: the core must stay a separate exe
# that the app can launch).

block_cipher = None

a = Analysis(
    ['run.py'],
    pathex=[],
    binaries=[],
    datas=[('assets/z_logo_clean.png', 'assets')],
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ZixoraVPN',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ZixoraVPN',
)
