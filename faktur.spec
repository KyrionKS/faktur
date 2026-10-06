# -*- mode: python ; coding: utf-8 -*-
"""Bauanleitung für PyInstaller.

Eine Spec-Datei ist Python. Das ist kein Zufall: sie wird ausgeführt, und
alles, was sich nicht ausdrücken lässt, wäre in einer Konfigurationsdatei
nicht möglich.

Der Aufbau, auf den es hier ankommt:

``datas``
    Die ``app.tcss`` muss ausdrücklich mit ins Paket. Textual sucht sie
    neben dem Modul, und ein Packer nimmt nur mit, was hier steht. Ohne
    diesen Eintrag baut der Bauvorgang ohne eine einzige Meldung, das
    Programm startet — und stirbt beim ersten Bild, weil es die Datei
    nicht findet.

``excludes``
    Werkzeuge, die zur Laufzeit nichts zu tun haben. Sie würden das Paket
    nur aufblähen.
"""

import sys
from pathlib import Path

# SPECPATH ist das Verzeichnis, in dem diese Datei liegt, also der
# Projektordner. Nicht noch einen hochgehen.
WURZEL = Path(SPECPATH)
ICON = WURZEL / "build" / "Faktur.icns"

#: Module, die zur Laufzeit nichts zu tun haben.
WEG = [
    "pytest",
    "_pytest",
    "ruff",
    "tkinter",
    "PIL.ImageQt",
    "unittest",
    "pydoc_data",
    "lib2to3",
    "distutils",
]

block_cipher = None

a = Analysis(
    [str(WURZEL / "start.py")],
    pathex=[str(WURZEL)],
    binaries=[],
    # Das Stylesheet ist eine Datei, kein Modul, und kommt sonst nicht mit.
    datas=[(str(WURZEL / "faktur" / "app.tcss"), "faktur")],
    hiddenimports=["faktur.screens.dokumente", "faktur.screens.kunden"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=WEG,
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
    name="Faktur",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    # Ohne das öffnet sich auf macOS kein Fenster, wenn man das Programm
    # doppelklickt. Diese App ist ein Menü im Terminal und braucht eines.
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ICON) if ICON.is_file() else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="Faktur",
)

if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="Faktur.app",
        icon=str(ICON) if ICON.is_file() else None,
        bundle_identifier="de.newair.faktur",
        info_plist={
            "CFBundleName": "Faktur",
            "CFBundleDisplayName": "Faktur",
            "CFBundleShortVersionString": "0.3.0",
            "CFBundleVersion": "0.3.0",
            "NSHighResolutionCapable": True,
            # Ohne das startet das Programm auf einem Mac mit deutscher
            # Tastatur nicht, weil der Bildschirmsatz nicht passt.
            "CFBundleDevelopmentRegion": "de",
        },
    )