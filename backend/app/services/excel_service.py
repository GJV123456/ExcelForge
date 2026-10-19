from __future__ import annotations

import re
from io import BytesIO
from pathlib import Path
from typing import Any, Sequence

import xlrd
from xlrd.book import Book
from xlutils.filter import XLRDReader, XLWTWriter, process

from app.schemas.excel import ExcelProcessRequest, TestContent


TEMPLATE_PATH = Path(__file__).resolve().parents[3] / "data" / "raw" / "联调测试表导入模版.xls"
INTERVAL_FIBER_PATTERN = re.compile(
    r"(?P<interval>[\u4e00-\u9fffA-Za-z0-9]+)区间(?P<direction>上行|下行)"
    r"(?:感温光纤报警反馈|感温光纤报警|感温光纤)?"
)


def _interval_alarm(content: str) -> tuple[str, str] | None:
    match = INTERVAL_FIBER_PATTERN.search(content)
    if not match:
        return None
    return match.group("interval"), match.group("direction")


def _fiber_steps(item: TestContent) -> list[dict[str, Any]]:
    content = item.generatedContent.strip()
    if "感温光纤综合故障" in content or "感温光纤主机故障" in content:
        subject = "感温光纤主机故障"
        return [{
            "description": "现场测试人员模拟触发感温光纤主机故障",
            "ratioChange": "否",
            "results": [
                {"description": "现场：感温光纤主机故障指示灯亮", "discipline": "自动化"},
                {"description": "FAS主机：收到感温光纤主机故障报警信息", "discipline": "自动化"},
                {"description": "FAS图文图文工作站：收到感温光纤主机故障报文", "discipline": "自动化"},
                {"description": "综合监控：收到感温光纤主机故障报警、事件、位置正确", "discipline": "自动化"},
            ],
        }]

    interval = _interval_alarm(content)
    if interval:
        interval_name, direction = interval
        location = f"{interval_name}{direction}区间"
        subject = f"{location}感温光纤主机火警"
        return [{
            "description": f"现场测试人员触发{location}感温光纤主机火警",
            "ratioChange": "否",
            "results": [
                {"description": f"现场：{subject}指示灯亮", "discipline": "自动化"},
                {"description": f"FAS主机：收到{subject}报警信息", "discipline": "自动化"},
                {"description": f"FAS图文工作站：收到{subject}报文", "discipline": "自动化"},
                {"description": f"综合监控：收到{location}感温光纤主机通道报警、事件、位置正确", "discipline": "自动化"},
            ],
        }]

    # 其他设备类型仍按测试内容生成一条可追溯的默认记录，避免新增设备类型
    # 因为没有专门目录规则而让整份导入文件无法生成。感温光纤则走上面的
    # 专用文本规则，确保区间名称和上下行方向被写入每一层输出。
    label = item.equipmentStatus.strip() or content
    return [{
        "description": f"现场测试人员执行{label}",
        "ratioChange": "否",
        "results": [
            {"description": f"系统收到{label}信息", "discipline": "自动化"},
        ],
    }]


def _safe_excel_text(value: str) -> str:
    return f"'{value}" if value.startswith(("=", "+", "-", "@")) else value


def _open_template() -> Book:
    if not TEMPLATE_PATH.is_file():
        raise FileNotFoundError(f"正式导入模板不存在：{TEMPLATE_PATH}")
    return xlrd.open_workbook(str(TEMPLATE_PATH), formatting_info=True)


def _copy_template(template: Book) -> tuple[Any, list[Any]]:
    writer = XLWTWriter()
    process(XLRDReader(template, "template.xls"), writer)
    return writer.output[0][1], writer.style_list


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
    for row_offset, values in enumerate(rows):
        target_row = row_offset + 2
        _set_row_height(source_sheet, target_sheet, 2, target_row)
        row_writer = target_sheet.row(target_row)
        for column in range(source_sheet.ncols):
            style = _row_style(source_sheet, styles, 2, column)
            value = values[column] if column < len(values) else ""
            if isinstance(value, int):
                row_writer.set_cell_number(column, value, style)
            elif value:
                row_writer.set_cell_text(column, _safe_excel_text(value), style)
            else:
                row_writer.set_cell_blank(column, style)

    end_row = len(rows) + 2
    _set_row_height(source_sheet, target_sheet, 3, end_row)
    end_writer = target_sheet.row(end_row)
    for column in range(source_sheet.ncols):
        style = _row_style(source_sheet, styles, 3, column)
        if column == 0:
            end_writer.set_cell_text(column, "end", style)
        else:
            end_writer.set_cell_blank(column, style)

    # The template contains one or more example rows after the end marker.
    # Clear them so a shorter generated table never leaves a second ``end``
    # marker or sample values behind (the formula sheet has exactly this case).
    for stale_row in range(end_row + 1, source_sheet.nrows):
        stale_writer = target_sheet.row(stale_row)
        for column in range(source_sheet.ncols):
            stale_writer.set_cell_blank(column, _row_style(source_sheet, styles, 3, column))
    return end_row


def _formal_rows(payload: ExcelProcessRequest) -> tuple[list[list[str | int]], ...]:
    location = payload.testLocation
    locations = [[location.type, location.direction, location.startStation, location.endStation]]
    contents = [[item.generatedContent.strip()] for item in payload.testContents]
    steps: list[list[str | int]] = []
    results: list[list[str | int]] = []
    next_step_row = 3
    for content_row, item in enumerate(payload.testContents, start=3):
        for step in _fiber_steps(item):
            step_row = next_step_row
            next_step_row += 1
            steps.append([content_row, step["description"], step["ratioChange"]])
            for result in step["results"]:
                results.append([step_row, result["description"], result["discipline"], ""])
    return locations, contents, steps, results, []


def build_workbook(payload: ExcelProcessRequest) -> bytes:
    source = _open_template()
    workbook, styles = _copy_template(source)
    rows = _formal_rows(payload)
    sheet_names = ("测试地点", "测试内容", "操作步骤", "结果输出", "参数公式")
    for index, (sheet_name, values) in enumerate(zip(sheet_names, rows)):
        source_sheet = source.sheet_by_name(sheet_name)
        target_sheet = workbook.get_sheet(index)
        _write_table(source_sheet, target_sheet, styles, values)

    output = BytesIO()
    workbook.save(output)
    return output.getvalue()
