# PyInstaller one-folder package for the reviewed Windows Helper source tree.
from pathlib import Path

spec_dir = Path(SPECPATH).resolve()
project_root = spec_dir.parents[1]
helper_root = project_root / "windows_helper"
backend_app = project_root / "backend" / "app"

a = Analysis(
    [str(helper_root / "packaging" / "packaged_entry.py")],
    pathex=[str(helper_root / "src"), str(backend_app)],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="PhotoOrganizerWindowsHelper",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="PhotoOrganizerWindowsHelper",
)
