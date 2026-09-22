from __future__ import annotations

from pathlib import Path
from typing import Any

from app.utils.template_provider import (
    DEFAULT_TEMPLATE_PATH,
    EXPECTED_SHEET_NAMES,
    EXPECTED_TEMPLATE_SHA256,
    file_sha256,
    open_template,
)
from app.utils.xls_writer import copy_template_bytes, open_generated_workbook


def _object_signature(value: Any, fields: tuple[str, ...]) -> tuple[Any, ...]:
    return tuple(getattr(value, field) for field in fields)


def _style_signature(workbook: Any, sheet: Any, row: int, column: int) -> tuple[Any, ...]:
    xf = workbook.xf_list[sheet.cell_xf_index(row, column)]
    font = workbook.font_list[xf.font_index]
    number_format = workbook.format_map.get(xf.format_key)
    return (
        getattr(number_format, "format_str", "General"),
        _object_signature(
            xf.alignment,
            (
                "hor_align",
                "vert_align",
                "text_wrapped",
                "rotation",
                "shrink_to_fit",
                "indent_level",
                "text_direction",
            ),
        ),
        _object_signature(
            xf.background,
            ("fill_pattern", "pattern_colour_index", "background_colour_index"),
        ),
        _object_signature(
            xf.border,
            (
                "left_line_style",
                "right_line_style",
                "top_line_style",
                "bottom_line_style",
                "left_colour_index",
                "right_colour_index",
                "top_colour_index",
                "bottom_colour_index",
            ),
        ),
        _object_signature(xf.protection, ("cell_locked", "formula_hidden")),
        _object_signature(
            font,
            (
                "name",
                "height",
                "bold",
                "italic",
                "underlined",
                "colour_index",
                "weight",
                "escapement",
                "family",
                "character_set",
            ),
        ),
    )


def _row_height(sheet: Any, row: int) -> int | None:
    info = sheet.rowinfo_map.get(row)
    return info.height if info is not None else None


def _column_width(sheet: Any, column: int) -> int | None:
    info = sheet.colinfo_map.get(column)
    return info.width if info is not None else None


def test_approved_template_hash_and_structure() -> None:
    assert file_sha256(DEFAULT_TEMPLATE_PATH) == EXPECTED_TEMPLATE_SHA256
    workbook = open_template()
    assert tuple(workbook.sheet_names()) == EXPECTED_SHEET_NAMES


def test_template_roundtrip_preserves_fixed_contract(tmp_path: Path) -> None:
    source_hash = file_sha256(DEFAULT_TEMPLATE_PATH)
    source = open_template()

    content = copy_template_bytes()
    copied_path = tmp_path / "template-roundtrip.xls"
    copied_path.write_bytes(content)
    reopened = open_generated_workbook(content)

    assert content
    assert tuple(reopened.sheet_names()) == EXPECTED_SHEET_NAMES
    assert file_sha256(DEFAULT_TEMPLATE_PATH) == source_hash

    for source_sheet, reopened_sheet in zip(source.sheets(), reopened.sheets(), strict=True):
        assert reopened_sheet.nrows == source_sheet.nrows
        assert reopened_sheet.ncols == source_sheet.ncols
        assert reopened_sheet.merged_cells == source_sheet.merged_cells

        for row in range(source_sheet.nrows):
            assert reopened_sheet.row_values(row) == source_sheet.row_values(row)
            assert _row_height(reopened_sheet, row) == _row_height(source_sheet, row)
            for column in range(source_sheet.ncols):
                assert _style_signature(reopened, reopened_sheet, row, column) == _style_signature(
                    source, source_sheet, row, column
                )

        for column in range(source_sheet.ncols):
            assert _column_width(reopened_sheet, column) == _column_width(source_sheet, column)
