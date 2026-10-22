"""Read-only access and validation for the BIFF8 import template."""

from __future__ import annotations

import hashlib
from pathlib import Path

import xlrd
from xlrd.book import Book

from app.resource_paths import SOURCE_TEMPLATE_PATH, resolve_template_path

EXPECTED_TEMPLATE_SHA256 = "C1F0515E2F04A79E6365EC3CC05D9315B59D5AF0D9723E92F610A6E8C308A0D4"
EXPECTED_SHEET_NAMES = ("测试地点", "测试内容", "操作步骤", "结果输出", "参数公式")
DEFAULT_TEMPLATE_PATH = SOURCE_TEMPLATE_PATH


class TemplateValidationError(RuntimeError):
    """Raised when the configured workbook is not the approved template."""


def file_sha256(path: Path) -> str:
    """Return an uppercase SHA-256 digest without modifying the file."""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def open_template(path: Path | None = None) -> Book:
    """Open a fresh formatting-aware copy of the approved template."""
    template_path = resolve_template_path(path)
    if not template_path.is_file():
        raise TemplateValidationError(f"Template file does not exist: {template_path}")

    actual_hash = file_sha256(template_path)
    if actual_hash != EXPECTED_TEMPLATE_SHA256:
        raise TemplateValidationError(
            f"Template SHA-256 mismatch: expected {EXPECTED_TEMPLATE_SHA256}, got {actual_hash}"
        )

    workbook = xlrd.open_workbook(
        file_contents=template_path.read_bytes(),
        formatting_info=True,
        on_demand=False,
    )
    validate_template_structure(workbook)
    return workbook


def validate_template_structure(workbook: Book) -> None:
    """Validate the fixed five-sheet contract needed by all writer modes."""
    if tuple(workbook.sheet_names()) != EXPECTED_SHEET_NAMES:
        raise TemplateValidationError(f"Unexpected sheet names or order: {workbook.sheet_names()}")

    for sheet in workbook.sheets():
        if sheet.nrows < 4:
            raise TemplateValidationError(f"Sheet {sheet.name!r} has fewer than four rows")
        if sheet.cell_value(3, 0) != "end":
            raise TemplateValidationError(f"Sheet {sheet.name!r} does not have end at A4")
