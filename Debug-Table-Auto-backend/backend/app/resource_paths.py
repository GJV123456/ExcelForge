"""Resolve source and packaged runtime resources without changing process cwd."""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

TEMPLATE_FILENAME = "联调测试表导入模版.xls"
DATABASE_FILENAME = "excelforge.sqlite3"
SOURCE_ROOT = Path(__file__).resolve().parents[2]
SOURCE_TEMPLATE_PATH = SOURCE_ROOT / "data" / "raw" / TEMPLATE_FILENAME
SOURCE_FRONTEND_DIST_PATH = SOURCE_ROOT / "backend" / "app" / "frontend_dist"
SOURCE_DATABASE_PATH = SOURCE_ROOT / "backend" / "data" / DATABASE_FILENAME


def executable_root() -> Path:
    """Return the directory containing the packaged executable."""
    return Path(sys.executable).resolve().parent


def default_template_path() -> Path:
    """Use an external sibling template when frozen, otherwise the repository copy."""
    if getattr(sys, "frozen", False):
        return executable_root() / TEMPLATE_FILENAME
    return SOURCE_TEMPLATE_PATH


def resolve_template_path(configured_path: Path | None = None) -> Path:
    """Resolve an explicit template override or the runtime-specific default."""
    return configured_path.expanduser().resolve() if configured_path else default_template_path()


def default_frontend_dist_path() -> Path:
    """Return the bundled frontend directory for source or frozen execution."""
    if getattr(sys, "frozen", False):
        bundle_root = Path(getattr(sys, "_MEIPASS", executable_root()))
        return bundle_root / "frontend_dist"
    return SOURCE_FRONTEND_DIST_PATH


def resolve_frontend_dist_path(configured_path: Path | None = None) -> Path:
    """Resolve an explicit static frontend directory or the runtime default."""
    if configured_path:
        return configured_path.expanduser().resolve()
    return default_frontend_dist_path()


def default_database_path() -> Path:
    """Return a writable source or packaged SQLite database path."""
    if not getattr(sys, "frozen", False):
        return SOURCE_DATABASE_PATH
    if sys.platform.startswith("linux"):
        xdg_data_home = os.getenv("XDG_DATA_HOME", "").strip()
        data_home = Path(xdg_data_home) if xdg_data_home else Path.home() / ".local" / "share"
        return data_home / "debug-table-auto" / DATABASE_FILENAME
    return executable_root() / DATABASE_FILENAME


def resolve_database_path(configured_path: Path | None = None) -> Path:
    """Resolve an explicit database override or the runtime-specific default."""
    return configured_path.expanduser().resolve() if configured_path else default_database_path()


def resolve_catalog_database_path(configured_path: Path | None, integration_code: str = "T19") -> Path:
    """Resolve an isolated catalog database for one integration project.

    T19 keeps using the configured legacy database so its existing catalog is
    preserved. Other projects get sibling SQLite files, keeping IDs and rules
    isolated while reusing the exact same application logic.
    """
    code = integration_code.strip().upper()
    if not re.fullmatch(r"[A-Z0-9][A-Z0-9_-]{0,31}", code):
        raise ValueError("Invalid integration code")
    base_path = resolve_database_path(configured_path)
    if code == "T19":
        return base_path
    return base_path.with_name(f"{base_path.stem}.{code}{base_path.suffix}")
