"""Validation and mode selection for Excel processing requests."""

from __future__ import annotations

import time
from dataclasses import dataclass

from app.config import Settings
from app.exceptions import BusinessError
from app.schemas.excel import ExcelProcessRequest
from app.utils.xls_writer import MockWorkbookRow, build_mock_workbook

XLS_MEDIA_TYPE = "application/vnd.ms-excel"
MOCK_FILENAME = "联调占位文件_不可导入.xls"
MAX_CELL_TEXT_LENGTH = 32_767


@dataclass(frozen=True, slots=True)
class ProcessedFile:
    content: bytes
    filename: str
    media_type: str


def _validate_required_text(value: str, path: list[str | int]) -> None:
    if not value.strip():
        raise BusinessError("必填文本不能为空", "REQUIRED_TEXT_EMPTY", path=path)
    if len(value) > MAX_CELL_TEXT_LENGTH:
        raise BusinessError("单元格文本超过 BIFF8 长度限制", "CELL_TEXT_TOO_LONG", path=path)


def _validate_request(request: ExcelProcessRequest) -> None:
    location = request.test_location
    location_values: tuple[tuple[str, list[str | int]], ...] = (
        (location.location_type, ["testLocation", "type"]),
        (location.direction, ["testLocation", "direction"]),
        (location.start_station, ["testLocation", "startStation"]),
        (location.end_station, ["testLocation", "endStation"]),
    )
    for value, path in location_values:
        _validate_required_text(value, path)

    if not request.test_contents:
        raise BusinessError(
            "没有可提交的测试内容",
            "NO_TEST_CONTENTS",
            path=["testContents"],
        )

    previous_sort_index = 0
    for index, item in enumerate(request.test_contents):
        if item.sort_index <= previous_sort_index:
            raise BusinessError(
                "sortIndex 必须按请求数组顺序严格递增且不得重复",
                "SORT_INDEX_NOT_STRICTLY_INCREASING",
                path=["testContents", index, "sortIndex"],
            )
        previous_sort_index = item.sort_index
        _validate_required_text(
            item.generated_content,
            ["testContents", index, "generatedContent"],
        )
        for value, field_name in (
            (item.equipment_code, "equipmentCode"),
            (item.equipment_type, "equipmentType"),
        ):
            if len(value) > MAX_CELL_TEXT_LENGTH:
                raise BusinessError(
                    "单元格文本超过 BIFF8 长度限制",
                    "CELL_TEXT_TOO_LONG",
                    path=["testContents", index, field_name],
                )


def process_excel_request(request: ExcelProcessRequest, settings: Settings) -> ProcessedFile:
    """Validate a v1 request and execute the explicitly selected mode."""
    _validate_request(request)
    if settings.mode == "formal":
        raise BusinessError(
            "正式业务规则尚未配置，禁止生成正式文件",
            "BUSINESS_RULES_NOT_CONFIGURED",
        )

    if settings.mock_delay_seconds:
        time.sleep(settings.mock_delay_seconds)

    location = request.test_location
    rows = [
        MockWorkbookRow(
            sort_index=item.sort_index,
            generated_content=item.generated_content,
            equipment_code=item.equipment_code,
            equipment_type=item.equipment_type,
        )
        for item in request.test_contents
    ]
    content = build_mock_workbook(
        (
            location.location_type,
            location.direction,
            location.start_station,
            location.end_station,
        ),
        rows,
    )
    return ProcessedFile(content=content, filename=MOCK_FILENAME, media_type=XLS_MEDIA_TYPE)
