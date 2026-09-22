from pathlib import Path

project_root = Path(SPECPATH).parent
backend_root = project_root / "backend"
frontend_dist = backend_root / "app" / "frontend_dist"

analysis = Analysis(
    [str(backend_root / "app" / "__main__.py")],
    pathex=[str(backend_root)],
    binaries=[],
    datas=[(str(frontend_dist), "frontend_dist")],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pytest", "mypy", "ruff"],
    noarchive=False,
)
pyz = PYZ(analysis.pure)
exe = EXE(
    pyz,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="DebugTableAuto",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
)
collect = COLLECT(
    exe,
    analysis.binaries,
    analysis.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="DebugTableAuto",
)
