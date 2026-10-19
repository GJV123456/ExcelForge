"""Environment-backed application settings."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

ApplicationMode = Literal["formal"]


def _template_path_from_environment() -> Path | None:
    value = os.getenv("EXCELFORGE_TEMPLATE_PATH", "").strip()
    return Path(value) if value else None


def _frontend_dist_from_environment() -> Path | None:
    value = os.getenv("EXCELFORGE_FRONTEND_DIST", "").strip()
    return Path(value) if value else None


def _database_path_from_environment() -> Path | None:
    value = os.getenv("EXCELFORGE_DATABASE_PATH", "").strip()
    return Path(value) if value else None


def _optional_text_from_environment(name: str) -> str | None:
    value = os.getenv(name, "").strip()
    return value or None


@dataclass(frozen=True, slots=True)
class Settings:
    """Runtime settings with production-safe defaults."""

    mode: ApplicationMode = "formal"
    template_path: Path | None = None
    frontend_dist_path: Path | None = None
    database_path: Path | None = None
    auth_username: str | None = None
    auth_password: str | None = None
    auth_display_name: str | None = None

    @classmethod
    def from_environment(cls) -> Settings:
        return cls(
            mode="formal",
            template_path=_template_path_from_environment(),
            frontend_dist_path=_frontend_dist_from_environment(),
            database_path=_database_path_from_environment(),
            auth_username=_optional_text_from_environment("EXCELFORGE_AUTH_USERNAME"),
            auth_password=_optional_text_from_environment("EXCELFORGE_AUTH_PASSWORD"),
            auth_display_name=_optional_text_from_environment("EXCELFORGE_AUTH_DISPLAY_NAME"),
        )


def apply_packaged_defaults(settings: Settings, *, is_frozen: bool) -> Settings:
    """Keep packaged builds database-first; explicit env credentials may migrate once."""
    return settings
