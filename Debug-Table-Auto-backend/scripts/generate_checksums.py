"""Generate a deterministic SHA256SUMS.txt for release assets."""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    asset_directory = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd()
    if not asset_directory.is_dir():
        raise SystemExit(f"Asset directory does not exist: {asset_directory}")
    checksum_file = asset_directory / "SHA256SUMS.txt"
    assets = sorted(
        path
        for path in asset_directory.iterdir()
        if path.is_file() and path.name != checksum_file.name
    )
    if not assets:
        raise SystemExit(f"No release assets found in {asset_directory}")
    lines = [f"{_sha256(path)}  {path.name}" for path in assets]
    checksum_file.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(checksum_file)


if __name__ == "__main__":
    main()
