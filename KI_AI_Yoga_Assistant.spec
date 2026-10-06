# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[],
    datas=[('data', 'data'), ('assets', 'assets'), ('database/schema.sql', 'database'), ('templates', 'templates')],
    hiddenimports=['PySide6.QtSvg', 'PySide6.QtCore', 'PySide6.QtWidgets', 'PySide6.QtGui', 'mediapipe', 'cv2', 'pyttsx3', 'pyttsx3.drivers', 'pyttsx3.drivers.sapi5', 'matplotlib', 'flask', 'flask_cors'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='KI_AI_Yoga_Assistant',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='KI_AI_Yoga_Assistant',
)
