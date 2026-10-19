"""Low-level BIFF8 workbook copying primitives."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any

import xlrd
import xlwt
from xlrd.book import Book
from xlutils.copy import copy as copy_workbook
from xlutils.filter import XLRDReader, XLWTWriter, process

from app.domain.workbook import FormalWorkbook
from app.utils.template_provider import open_template, validate_template_structure

MOCK_SHEET_NAME = "联调占位"
MOCK_WARNING = "联调占位文件，不可导入正式系统"


@dataclass(frozen=True, slots=True)
class MockWorkbookRow:
    sort_index: int
    generated_content: str
    equipment_code: str
    equipment_type: str


def _safe_excel_text(value: str) -> str:
    if value.startswith(("=", "+", "-", "@")):
        return f"'{value}"
    return value


def build_mock_workbook(
    location: tuple[str, str, str, str], rows: Sequence[MockWorkbookRow]
) -> bytes:
    """Build a visibly non-production BIFF8 file for transport testing."""
    workbook = xlwt.Workbook(encoding="utf-8")
    sheet = workbook.add_sheet(MOCK_SHEET_NAME)

    warning_style = xlwt.easyxf("font: bold on, colour red;")
    header_style = xlwt.easyxf("font: bold on; pattern: pattern solid, fore_colour gray25;")
    sheet.write(0, 0, MOCK_WARNING, warning_style)

    location_headers = ("地点类型", "行车方向", "开始站点", "结束站点")
    for column, header in enumerate(location_headers):
        sheet.write(2, column, header, header_style)
        sheet.write(3, column, _safe_excel_text(location[column]))

    content_headers = ("sortIndex", "generatedContent", "equipmentCode", "equipmentType")
    for column, header in enumerate(content_headers):
        sheet.write(5, column, header, header_style)

    for row_number, row in enumerate(rows, start=6):
        sheet.write(row_number, 0, row.sort_index)
        sheet.write(row_number, 1, _safe_excel_text(row.generated_content))
        sheet.write(row_number, 2, _safe_excel_text(row.equipment_code))
        sheet.write(row_number, 3, _safe_excel_text(row.equipment_type))

    output = BytesIO()
    workbook.save(output)
    content = output.getvalue()
    reopened = xlrd.open_workbook(file_contents=content)
    if reopened.sheet_names() != [MOCK_SHEET_NAME]:
        raise RuntimeError("Mock workbook self-check failed")
    if reopened.sheet_by_index(0).cell_value(0, 0) != MOCK_WARNING:
        raise RuntimeError("Mock workbook warning marker is missing")
    return content


def copy_template_bytes(template_path: Path | None = None) -> bytes:
    """Round-trip the approved template without writing business data."""
    source = open_template(template_path)
    writable = copy_workbook(source)
    output = BytesIO()
    writable.save(output)
    result = output.getvalue()

    reopened = xlrd.open_workbook(file_contents=result, formatting_info=True)
    validate_template_structure(reopened)
    return result


def open_generated_workbook(content: bytes) -> Book:
    """Reopen generated BIFF8 content for post-write validation."""
    workbook = xlrd.open_workbook(file_contents=content, formatting_info=True)
    validate_template_structure(workbook)
    return workbook


def _copy_template_with_styles(template_path: Path | None = None) -> tuple[Book, Any, list[Any]]:
    source = open_template(template_path)
    writer = XLWTWriter()
    process(XLRDReader(source, "template.xls"), writer)
    return source, writer.output[0][1], writer.style_list


def _row_style(source_sheet: Any, styles: list[Any], source_row: int, column: int) -> Any:
    return styles[source_sheet.cell_xf_index(source_row, column)]


def _set_row_height(source_sheet: Any, target_sheet: Any, source_row: int, row: int) -> None:
    source_info = source_sheet.rowinfo_map.get(source_row)
    if source_info is not None:
        target = target_sheet.row(row)
        target.height = source_info.height
        target.height_mismatch = True


def _write_table(
    source_sheet: Any,
    target_sheet: Any,
    styles: list[Any],
    rows: Sequence[Sequence[str | int]],
) -> int:
    column_count = source_sheet.ncols
    for row_offset, values in enumerate(rows):
        target_row = row_offset + 2
        _set_row_height(source_sheet, target_sheet, 2, target_row)
        row_writer = target_sheet.row(target_row)
        for column in range(column_count):
            style = _row_style(source_sheet, styles, 2, column)
            value = values[column] if column < len(values) else ""
            if isinstance(value, int):
                row_writer.set_cell_number(column, value, style)
            elif value:
                row_writer.set_cell_text(column, value, style)
            else:
                row_writer.set_cell_blank(column, style)

    end_row = len(rows) + 2
    _set_row_height(source_sheet, target_sheet, 3, end_row)
    end_writer = target_sheet.row(end_row)
    for column in range(column_count):
        style = _row_style(source_sheet, styles, 3, column)
        if column == 0:
            end_writer.set_cell_text(column, "end", style)
        else:
            end_writer.set_cell_blank(column, style)

    if end_row < 3:
        stale_writer = target_sheet.row(3)
        for column in range(column_count):
            stale_writer.set_cell_blank(column, _row_style(source_sheet, styles, 3, column))
    return end_row


def _formal_rows(workbook: FormalWorkbook) -> tuple[list[list[str | int]], ...]:
    location_stations = workbook.location.stations
    if location_stations:
        location = [
            [workbook.location.location_type, workbook.location.direction, station, station]
            for station in location_stations
        ]
    else:
        location = [[
            workbook.location.location_type,
            workbook.location.direction,
            workbook.location.start_station,
            workbook.location.end_station,
        ]]
    contents: list[list[str | int]] = [
        [content.generated_content] for content in workbook.test_contents
    ]
    steps: list[list[str | int]] = []
    results: list[list[str | int]] = []
    next_step_excel_row = 3
    for content_offset, content in enumerate(workbook.test_contents):
        content_excel_row = content_offset + 3
        for step in content.operation_steps:
            step_excel_row = next_step_excel_row
            next_step_excel_row += 1
            steps.append([content_excel_row, step.description, step.ratio_change])
            for result in step.results:
                results.append([
                    step_excel_row,
                    result.description,
                    ",".join(result.responsible_disciplines),
                    "",
                ])
    return location, contents, steps, results, []


def _validate_formal_output(content: bytes, expected_end_rows: Sequence[int]) -> None:
    reopened = xlrd.open_workbook(file_contents=content, formatting_info=True)
    expected_names = ["测试地点", "测试内容", "操作步骤", "结果输出", "参数公式"]
    if reopened.sheet_names() != expected_names:
        raise RuntimeError("Formal workbook sheet contract failed")
    for sheet, expected_end_row in zip(reopened.sheets(), expected_end_rows, strict=True):
        end_rows = [
            row for row in range(sheet.nrows) if sheet.cell_value(row, 0) == "end"
        ]
        if end_rows != [expected_end_row]:
            raise RuntimeError(f"Formal workbook end marker failed for {sheet.name}")
    result_sheet = reopened.sheet_by_name("结果输出")
    for row in range(2, expected_end_rows[3]):
        if result_sheet.cell_value(row, 3) != "":
            raise RuntimeError("Formal workbook test style must be empty")
    formula_sheet = reopened.sheet_by_name("参数公式")
    if formula_sheet.cell_value(2, 0) != "end" or any(
        formula_sheet.cell_value(2, column) != "" for column in range(1, 5)
    ):
        raise RuntimeError("Formal workbook formula sheet contract failed")


def build_formal_workbook(
    workbook: FormalWorkbook, template_path: Path | None = None
) -> bytes:
    """Copy the approved template and write the explicit v2 formal model."""
    table_rows = _formal_rows(workbook)
    if any(len(rows) + 2 >= 65_536 for rows in table_rows):
        raise ValueError("BIFF8 row limit exceeded")
    source, writable, styles = _copy_template_with_styles(template_path)
    expected_end_rows: list[int] = []
    for sheet_index, rows in enumerate(table_rows):
        expected_end_rows.append(
            _write_table(
                source.sheet_by_index(sheet_index),
                writable.get_sheet(sheet_index),
                styles,
                rows,
            )
        )
    output = BytesIO()
    writable.save(output)
    content = output.getvalue()
    _validate_formal_output(content, expected_end_rows)
    return content
