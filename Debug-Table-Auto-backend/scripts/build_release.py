"""Build a self-contained onedir release with an external sibling template."""

from __future__ import annotations

import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRONTEND_DIST = ROOT / "frontend" / "dist"
FRONTEND_STAGING = ROOT / "backend" / "app" / "frontend_dist"
TEMPLATE = ROOT / "data" / "raw" / "联调测试表导入模版.xls"
RELEASE_ROOT = ROOT / "build" / "release"
APP_DIR = RELEASE_ROOT / "DebugTableAuto"


def _require_file(path: Path) -> None:
    if not path.is_file():
        raise SystemExit(f"Required file is missing: {path}")


def main() -> None:
    _require_file(FRONTEND_DIST / "index.html")
    _require_file(TEMPLATE)
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    if not version:
        raise SystemExit("VERSION is empty")

    staging = FRONTEND_STAGING.resolve()
    if staging.parent != (ROOT / "backend" / "app").resolve():
        raise SystemExit(f"Unsafe frontend staging path: {staging}")
    if staging.exists():
        shutil.rmtree(staging)
    shutil.copytree(FRONTEND_DIST, FRONTEND_STAGING)

    subprocess.run(
        [
            sys.executable,
            "-m",
            "PyInstaller",
            "--noconfirm",
            "--clean",
            "--distpath",
            str(RELEASE_ROOT),
            "--workpath",
            str(ROOT / "build" / "pyinstaller"),
            str(ROOT / "packaging" / "debug_table_auto.spec"),
        ],
        cwd=ROOT,
        check=True,
    )

    for source in (TEMPLATE, ROOT / "README.md", ROOT / "LICENSE"):
        _require_file(source)
        shutil.copy2(source, APP_DIR / source.name)

    system = platform.system().lower()
    machine = platform.machine().lower()
    architecture = "x64" if machine in {"amd64", "x86_64"} else machine
    print(f"release_dir={APP_DIR}")
    if system == "windows":
        archive_name = f"Debug-Table-Auto-{version}-{system}-{architecture}"
        archive = shutil.make_archive(
            str(RELEASE_ROOT / archive_name), "zip", APP_DIR.parent, APP_DIR.name
        )
        print(f"archive={archive}")
    elif system == "linux":
        subprocess.run([sys.executable, str(ROOT / "scripts" / "build_deb.py")], check=True)
    else:
        raise SystemExit(f"Unsupported release platform: {system}")


if __name__ == "__main__":
    main()
