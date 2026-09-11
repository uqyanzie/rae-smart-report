# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller build spec for the RAESmartReport desktop executable.

Bundles the pre-built SPA (``frontend/dist``) and the Lazada SKU-mapping
runtime artifact (``backend/app/data/sku_mapping.json``) so the frozen app
resolves them from ``sys._MEIPASS`` exactly where ``app.core.config`` looks.

Build (after ``npm run build`` in ``frontend/``):
    python -m PyInstaller packaging.spec --noconfirm --clean
"""

from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

ROOT = Path(SPECPATH).resolve()

datas = [
    (str(ROOT / "frontend" / "dist"), "frontend/dist"),
    (str(ROOT / "backend" / "app" / "data" / "sku_mapping.json"), "data"),
]

hiddenimports = [
    "app",
    "pydantic_core",
    "openpyxl",
    "sqlite3",
    "sqlalchemy.sql.default_comparator",
    "sqlalchemy.dialects.sqlite",
    "python_multipart",
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.auto",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.h11_impl",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
]
hiddenimports += collect_submodules("uvicorn")
hiddenimports += collect_submodules("python_multipart")
# Tray/icon support: pystray selects its platform backend via a function-local
# import, so the win32 backend is invisible to static analysis.
hiddenimports += collect_submodules("pystray")
hiddenimports += ["pystray._win32", "PIL.Image", "PIL.ImageDraw"]

a = Analysis(
    [str(ROOT / "backend" / "run.py")],
    pathex=[str(ROOT / "backend")],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="RAE-Smart-Report",
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
