"""Package the Linux onedir application as an amd64 Debian package."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RELEASE_ROOT = ROOT / "build" / "release"
APP_DIR = RELEASE_ROOT / "DebugTableAuto"
PACKAGE_ROOT = ROOT / "build" / "debian-package"
INSTALL_ROOT = PACKAGE_ROOT / "opt" / "debug-table-auto"


def _write_package_file(path: Path, content: str, *, executable: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")
    path.chmod(0o755 if executable else 0o644)


def main() -> None:
    if sys.platform != "linux":
        raise SystemExit("Debian packages must be built on Linux")
    if not (APP_DIR / "DebugTableAuto").is_file():
        raise SystemExit(f"Linux executable is missing: {APP_DIR / 'DebugTableAuto'}")
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    package_root = PACKAGE_ROOT.resolve()
    if package_root.parent != (ROOT / "build").resolve():
        raise SystemExit(f"Unsafe Debian staging path: {package_root}")
    if package_root.exists():
        shutil.rmtree(package_root)
    shutil.copytree(APP_DIR, INSTALL_ROOT)

    _write_package_file(
        PACKAGE_ROOT / "DEBIAN" / "control",
        "\n".join(
            (
                "Package: debug-table-auto",
                f"Version: {version}",
                "Section: utils",
                "Priority: optional",
                "Architecture: amd64",
                "Maintainer: BG2FOU",
                "Depends: libc6",
                "Description: Subway joint debugging table generation tool",
                "",
            )
        ),
    )
    _write_package_file(
        PACKAGE_ROOT / "usr" / "bin" / "debug-table-auto",
        "#!/bin/sh\nexec /opt/debug-table-auto/DebugTableAuto \"$@\"\n",
        executable=True,
    )
    output = RELEASE_ROOT / f"Debug-Table-Auto-{version}-linux-x64.deb"
    subprocess.run(
        ["dpkg-deb", "--build", "--root-owner-group", str(PACKAGE_ROOT), str(output)],
        cwd=ROOT,
        check=True,
    )
    print(f"deb={output}")


if __name__ == "__main__":
    main()
