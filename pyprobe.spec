# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for PyProbe.

Build with:
    pyinstaller pyprobe.spec

Produces: dist/pyprobe/  (one-dir bundle)
"""

import sys
from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

# Dynamically collect all pyprobe submodules so new plugins/themes
# are picked up automatically.
hiddenimports = collect_submodules('pyprobe')

# Platform-specific binary name
exe_name = 'pyprobe'

a = Analysis(
    ['pyprobe/__main__.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'unittest',
        'pytest',
        'pytest_qt',
        'pytest_xdist',
        'pytest_forked',
        'test',
        'pyplan',
    ],
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
    name=exe_name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='pyprobe',
)
