"""Command-line maintenance for the ExcelForge SQLite database."""

from __future__ import annotations

import argparse
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path

from app.config import Settings
from app.db.catalog import SCHEMA_VERSION, CatalogRepository
from app.resource_paths import resolve_database_path


@dataclass(frozen=True, slots=True)
class IntegrityReport:
    schema_version: int
    integrity: str
    foreign_key_errors: int

    @property
    def is_healthy(self) -> bool:
        return (
            self.schema_version == SCHEMA_VERSION
            and self.integrity == "ok"
            and not self.foreign_key_errors
        )


def initialize_database(database_path: Path) -> int:
    repository = CatalogRepository(database_path.resolve())
    repository.ensure_schema()
    return SCHEMA_VERSION


def check_database(database_path: Path) -> IntegrityReport:
    repository = CatalogRepository(database_path.resolve())
    repository.ensure_schema()
    with closing(repository._connect()) as connection, connection:
        integrity_rows = connection.execute("PRAGMA integrity_check").fetchall()
        integrity = "; ".join(str(row[0]) for row in integrity_rows)
        foreign_key_errors = len(connection.execute("PRAGMA foreign_key_check").fetchall())
        row = connection.execute("SELECT MAX(version) FROM schema_migrations").fetchone()
        schema_version = int(row[0] or 0)
    return IntegrityReport(schema_version, integrity, foreign_key_errors)


def backup_database(database_path: Path, output_path: Path) -> None:
    source_path = database_path.expanduser().resolve()
    destination_path = output_path.expanduser().resolve()
    if source_path == destination_path:
        raise ValueError("Backup output must differ from the source database")
    if destination_path.exists():
        raise FileExistsError(f"Backup output already exists: {destination_path}")
    initialize_database(source_path)
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with (
            closing(sqlite3.connect(source_path, timeout=5)) as source,
            closing(sqlite3.connect(destination_path, timeout=5)) as destination,
        ):
            source.execute("PRAGMA busy_timeout = 5000")
            source.backup(destination)
    except Exception:
        destination_path.unlink(missing_ok=True)
        raise


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ExcelForge SQLite maintenance")
    parser.add_argument("--database", type=Path, help="SQLite path; defaults to runtime config")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("init", help="Create or upgrade the schema")
    subparsers.add_parser("check", help="Run schema, integrity and foreign-key checks")
    backup = subparsers.add_parser("backup", help="Create a consistent SQLite backup")
    backup.add_argument("--output", type=Path, required=True)
    return parser


def main() -> None:
    arguments = _parser().parse_args()
    configured_path = arguments.database or Settings.from_environment().database_path
    database_path = resolve_database_path(configured_path)
    if arguments.command == "init":
        version = initialize_database(database_path)
        print(f"database={database_path}")
        print(f"schema_version={version}")
        return
    if arguments.command == "check":
        report = check_database(database_path)
        print(f"database={database_path}")
        print(f"schema_version={report.schema_version}")
        print(f"integrity={report.integrity}")
        print(f"foreign_key_errors={report.foreign_key_errors}")
        if not report.is_healthy:
            raise SystemExit(1)
        return
    backup_database(database_path, arguments.output)
    print(f"database={database_path}")
    print(f"backup={arguments.output.expanduser().resolve()}")


if __name__ == "__main__":
    main()
