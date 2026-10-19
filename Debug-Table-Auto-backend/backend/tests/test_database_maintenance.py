from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from app.db.maintenance import backup_database, check_database, initialize_database
from app.db.catalog import SCHEMA_VERSION


def test_database_init_check_and_consistent_backup(tmp_path: Path) -> None:
    database_path = tmp_path / "catalog.sqlite3"
    backup_path = tmp_path / "backups" / "catalog.sqlite3"

    assert initialize_database(database_path) == SCHEMA_VERSION
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            "INSERT INTO equipment_types(code, name) VALUES (?, ?)",
            ("SMOKE", "烟感"),
        )

    report = check_database(database_path)
    assert report.schema_version == SCHEMA_VERSION
    assert report.integrity == "ok"
    assert report.foreign_key_errors == 0
    assert report.is_healthy

    backup_database(database_path, backup_path)
    with sqlite3.connect(backup_path) as connection:
        assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert connection.execute("SELECT name FROM equipment_types").fetchone()[0] == "烟感"


def test_database_backup_refuses_overwrite_or_source_target(tmp_path: Path) -> None:
    database_path = tmp_path / "catalog.sqlite3"
    initialize_database(database_path)
    existing = tmp_path / "existing.sqlite3"
    existing.write_bytes(b"do not overwrite")

    with pytest.raises(FileExistsError):
        backup_database(database_path, existing)
    with pytest.raises(ValueError):
        backup_database(database_path, database_path)

    assert existing.read_bytes() == b"do not overwrite"

