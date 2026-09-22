"""Validate v2 requests and assemble formal workbook domain data."""

from __future__ import annotations

import re
from datetime import datetime

from app.config import Settings
from app.db.catalog import CatalogRepository
from app.domain.workbook import (
    FormalWorkbook,
    LocationRow,
    OperationStepRow,
    ResultRow,
    TestContentRow,
)
from app.exceptions import BusinessError
from app.resource_paths import resolve_database_path
from app.schemas.excel_v2 import ExcelProcessV2Request, V2TestContent
from app.services.excel_processor import XLS_MEDIA_TYPE, ProcessedFile
from app.utils.xls_writer import build_formal_workbook

FORMAL_FILENAME_PREFIX = "最终导入表"
ALLOWED_LOCATION_TYPES = frozenset({"全线", "区间", "站点"})
ALLOWED_DIRECTIONS = frozenset({"上行", "下行"})
MAX_BIFF8_DATA_ROWS = 65_533
MAX_CELL_TEXT_LENGTH = 32_767
UNSAFE_FILENAME_PATTERN = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def _require_text(value: str, path: list[str | int]) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise BusinessError("必填文本不能为空", "REQUIRED_TEXT_EMPTY", path=path)
    return cleaned


def _build_location(request: ExcelProcessV2Request) -> LocationRow:
    location = request.test_location
    location_type = _require_text(location.location_type, ["testLocation", "type"])
    if location_type not in ALLOWED_LOCATION_TYPES:
        raise BusinessError(
            "正式文件的地点类型只能是全线、区间或站点",
            "INVALID_LOCATION_TYPE",
            path=["testLocation", "type"],
        )

    if location_type == "站点":
        start_station = _require_text(location.start_station, ["testLocation", "startStation"])
        end_station = _require_text(location.end_station, ["testLocation", "endStation"])
        if start_station != end_station:
            raise BusinessError(
                "地点类型为站点时，开始站点和结束站点必须相同",
                "STATION_ENDPOINTS_MISMATCH",
                path=["testLocation", "endStation"],
            )
        if location.stations:
            stations = tuple(
                _require_text(value, ["testLocation", "stations"]) for value in location.stations
            )
            if stations[0] != start_station:
                raise BusinessError(
                    "站点类型的 startStation 必须与 stations 首项一致",
                    "STATION_LIST_MISMATCH",
                    path=["testLocation", "stations"],
                )
        return LocationRow(location_type, "", start_station, end_station)

    direction = location.direction.strip()
    if direction and direction not in ALLOWED_DIRECTIONS:
        raise BusinessError(
            "正式文件的行车方向只能是上行或下行",
            "INVALID_DIRECTION",
            path=["testLocation", "direction"],
        )
    if location_type == "全线":
        if location.start_station.strip() or location.end_station.strip():
            raise BusinessError(
                "地点类型为全线时开始站点和结束站点必须为空",
                "LINE_LOCATION_STATIONS_NOT_ALLOWED",
                path=["testLocation"],
            )
        return LocationRow(location_type, direction, "", "")

    start_station = _require_text(location.start_station, ["testLocation", "startStation"])
    end_station = _require_text(location.end_station, ["testLocation", "endStation"])
    return LocationRow(location_type, direction, start_station, end_station)


def _catalog_steps(item: V2TestContent, repository: CatalogRepository) -> list[dict[str, object]]:
    """Resolve the fixed operation/result hierarchy stored in SQLite.

    Rules are normally keyed by equipment type.  A captured subtype is tried
    first so deployments that use subtypes as catalog equipment types work as
    well; the broad equipment type is the compatibility fallback.
    """
    exact = repository.find_test_content_rule(
        item.equipment_type.strip(),
        item.equipment_subtype.strip(),
        item.equipment_status.strip(),
    )
    if exact is not None:
        candidates = [exact]
    else:
        keys = [item.equipment_subtype.strip(), item.equipment_type.strip()]
        candidates = []
        for key in keys:
            if key:
                candidates = repository.list_test_contents(equipment_type=key)
                if candidates:
                    break
    if not candidates:
        raise BusinessError(
            (
                f"未找到设备类型“{item.equipment_subtype or item.equipment_type}”"
                "对应的操作步骤和输出结果"
            ),
            "CATALOG_RULE_NOT_FOUND",
        )
    source_values = tuple(
        value
        for value in (
            item.equipment_chinese.strip(),
            item.generated_content.strip(),
            item.equipment_status.strip(),
            item.signal_description.strip(),
        )
        if value
    )
    selected = next(
        (
            candidate
            for candidate in candidates
            if any(str(candidate["content"]) in value for value in source_values)
        ),
        candidates[0],
    )
    steps: list[dict[str, object]] = []
    selected_steps = selected["operationSteps"]
    for step in selected_steps:
        results: list[dict[str, object]] = []
        for result in step["results"]:
            disciplines = [entry["name"] for entry in result["responsibleDisciplines"]]
            if not disciplines:
                raise BusinessError(
                    "目录规则的结果输出未配置责任专业",
                    "CATALOG_RULE_INCOMPLETE",
                )
            results.append(
                {
                    "description": result["description"],
                    "responsibleDisciplines": disciplines,
                }
            )
        if not results:
            raise BusinessError("目录规则未配置结果输出", "CATALOG_RULE_INCOMPLETE")
        steps.append(
            {
                "description": step["description"],
                "ratioChange": step["ratioChange"],
                "results": results,
            }
        )
    if not steps:
        raise BusinessError("目录规则未配置操作步骤", "CATALOG_RULE_INCOMPLETE")
    return steps


def prepare_formal_request(
    request: ExcelProcessV2Request, settings: Settings
) -> ExcelProcessV2Request:
    """Fill omitted operationSteps from the SQLite rule catalog."""
    if all(content.operation_steps for content in request.test_contents):
        return request
    repository = CatalogRepository(resolve_database_path(settings.database_path))
    payload = request.model_dump(by_alias=True)
    contents = payload["testContents"]
    assert isinstance(contents, list)
    for index, content in enumerate(request.test_contents):
        if content.operation_steps:
            continue
        contents[index]["operationSteps"] = _catalog_steps(content, repository)
    return ExcelProcessV2Request.model_validate(payload)


def _validate_sort_indexes(request: ExcelProcessV2Request) -> None:
    previous = 0
    for index, content in enumerate(request.test_contents):
        if content.sort_index <= previous:
            raise BusinessError(
                "sortIndex 必须按请求数组顺序严格递增且不得重复",
                "SORT_INDEX_NOT_STRICTLY_INCREASING",
                path=["testContents", index, "sortIndex"],
            )
        previous = content.sort_index


def _validate_workbook_limits(workbook: FormalWorkbook) -> None:
    step_count = 0
    result_count = 0
    for content_index, content in enumerate(workbook.test_contents):
        step_count += len(content.operation_steps)
        for step_index, step in enumerate(content.operation_steps):
            result_count += len(step.results)
            for result_index, result in enumerate(step.results):
                if any("," in name or "，" in name for name in result.responsible_disciplines):
                    raise BusinessError(
                        "责任专业名称内不能包含逗号",
                        "INVALID_DISCIPLINE_NAME",
                        path=[
                            "testContents",
                            content_index,
                            "operationSteps",
                            step_index,
                            "results",
                            result_index,
                            "responsibleDisciplines",
                        ],
                    )
                if len(",".join(result.responsible_disciplines)) > MAX_CELL_TEXT_LENGTH:
                    raise BusinessError(
                        "责任专业合并后超过 BIFF8 单元格文本上限",
                        "BIFF8_TEXT_LIMIT_EXCEEDED",
                        path=[
                            "testContents",
                            content_index,
                            "operationSteps",
                            step_index,
                            "results",
                            result_index,
                            "responsibleDisciplines",
                        ],
                    )

    row_counts = (len(workbook.test_contents), step_count, result_count)
    if any(count > MAX_BIFF8_DATA_ROWS for count in row_counts):
        raise BusinessError(
            "生成内容超过 BIFF8 工作表行数上限",
            "BIFF8_ROW_LIMIT_EXCEEDED",
        )


def _build_workbook(request: ExcelProcessV2Request) -> FormalWorkbook:
    _validate_sort_indexes(request)
    contents = tuple(
        TestContentRow(
            sort_index=content.sort_index,
            generated_content=content.generated_content,
            equipment_code=content.equipment_code,
            equipment_type=content.equipment_type,
            operation_steps=tuple(
                OperationStepRow(
                    description=step.description,
                    ratio_change=step.ratio_change,
                    results=tuple(
                        ResultRow(
                            description=result.description,
                            responsible_disciplines=tuple(result.responsible_disciplines),
                        )
                        for result in step.results
                    ),
                )
                for step in content.operation_steps
            ),
        )
        for content in request.test_contents
    )
    workbook = FormalWorkbook(location=_build_location(request), test_contents=contents)
    _validate_workbook_limits(workbook)
    return workbook


def _filename_component(value: str) -> str:
    cleaned = UNSAFE_FILENAME_PATTERN.sub("-", value.strip())
    cleaned = re.sub(r"\s+", "", cleaned).strip(". ")
    return cleaned or "未命名"


def _formal_filename(workbook: FormalWorkbook, generated_at: datetime) -> str:
    location = workbook.location.start_station or workbook.location.location_type
    equipment_types = tuple(
        dict.fromkeys(
            content.equipment_type.strip()
            for content in workbook.test_contents
            if content.equipment_type.strip()
        )
    )
    components = [
        FORMAL_FILENAME_PREFIX,
        _filename_component(location),
        *(_filename_component(value) for value in equipment_types),
        generated_at.strftime("%Y%m%d%H%M%S"),
    ]
    return "_".join(components) + ".xls"


def process_formal_request(
    request: ExcelProcessV2Request,
    settings: Settings,
    *,
    generated_at: datetime | None = None,
) -> ProcessedFile:
    """Generate a formal file only through the explicit v2 contract."""
    if settings.mode != "formal":
        raise BusinessError("当前服务未启用正式生成模式", "FORMAL_MODE_DISABLED")
    request = prepare_formal_request(request, settings)
    workbook = _build_workbook(request)
    content = build_formal_workbook(workbook, settings.template_path)
    filename = _formal_filename(workbook, generated_at or datetime.now().astimezone())
    return ProcessedFile(content=content, filename=filename, media_type=XLS_MEDIA_TYPE)
