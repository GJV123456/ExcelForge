from __future__ import annotations

import sys
from pathlib import Path

from app.resource_paths import (
    DATABASE_FILENAME,
    TEMPLATE_FILENAME,
    default_database_path,
    default_frontend_dist_path,
    default_template_path,
    resolve_database_path,
    resolve_template_path,
)


def test_source_default_template_is_repository_copy() -> None:
    assert default_template_path().name == TEMPLATE_FILENAME
    assert default_template_path().parts[-3:] == ("data", "raw", TEMPLATE_FILENAME)
    assert default_database_path().parts[-3:] == ("backend", "data", DATABASE_FILENAME)


def test_packaged_default_template_is_next_to_executable(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    executable = Path("C:/release/DebugTableAuto/DebugTableAuto.exe")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(executable))

    assert default_template_path() == executable.parent / TEMPLATE_FILENAME
    assert default_frontend_dist_path() == executable.parent / "frontend_dist"
    assert default_database_path() == executable.parent / DATABASE_FILENAME


def test_explicit_template_path_overrides_runtime_default(tmp_path: Path) -> None:
    configured = tmp_path / TEMPLATE_FILENAME
    assert resolve_template_path(configured) == configured.resolve()

    configured_database = tmp_path / DATABASE_FILENAME
    assert resolve_database_path(configured_database) == configured_database.resolve()


def test_packaged_linux_database_uses_xdg_data_home(monkeypatch, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))

    assert default_database_path() == tmp_path / "debug-table-auto" / DATABASE_FILENAME

