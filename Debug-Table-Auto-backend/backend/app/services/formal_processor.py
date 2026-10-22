"""Validate v2 requests and assemble formal workbook domain data."""

from __future__ import annotations

import re
from datetime import datetime

from app.config import Settings
from app.db.catalog import CatalogRepository
from app.db.workspace import WorkspaceRepository
from app.domain.workbook import (
    FormalWorkbook,
    LocationRow,
    OperationStepRow,
    ResultRow,
    TestContentRow,
)
from app.exceptions import BusinessError
from app.resource_paths import resolve_catalog_database_path
from app.schemas.excel import ExcelProcessRequest, FormalTestContent, OperationStep
from app.schemas.workspace import ScopeSelection
from app.services.result import XLS_MEDIA_TYPE, ProcessedFile
from app.utils.formal_workbook import build_formal_workbook

FORMAL_FILENAME_SUFFIX = "导入版V1"
ALLOWED_LOCATION_TYPES = frozenset({"全线", "区间", "站点"})
ALLOWED_DIRECTIONS = frozenset({"上行", "下行"})
MAX_BIFF8_DATA_ROWS = 65_533
MAX_CELL_TEXT_LENGTH = 32_767
UNSAFE_FILENAME_PATTERN = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
INTERVAL_DIRECTION_PATTERN = re.compile(r"(?P<interval>[\u4e00-\u9fffA-Za-z0-9]{1,12})区间(?P<direction>上行|下行)")


def _source_values(item: FormalTestContent) -> tuple[str, ...]:
    return tuple(
        value.strip()
        for value in (
            item.equipment_chinese,
            item.generated_content,
            item.equipment_status,
            item.signal_description,
            item.interval_name,
        )
        if value and value.strip()
    )


def _interval_context(item: FormalTestContent) -> tuple[str, str]:
    for value in _source_values(item):
        match = INTERVAL_DIRECTION_PATTERN.search(value)
        if match:
            return match.group("interval"), match.group("direction")
    return "", ""


def _render_rule_text(value: str, interval: str) -> str:
    if not interval:
        return value
    return re.sub(r"xx", lambda _: interval, value, flags=re.IGNORECASE)


def _require_text(value: str, path: list[str | int]) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise BusinessError("必填文本不能为空", "REQUIRED_TEXT_EMPTY", path=path)
    return cleaned


def _build_location(request: ExcelProcessRequest) -> LocationRow:
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
        stations = tuple(
            _require_text(value, ["testLocation", "stations"]) for value in (location.stations or [start_station])
        )
        if stations[0] != start_station:
            raise BusinessError(
                "站点类型的 startStation 必须与 stations 首项一致",
                "STATION_LIST_MISMATCH",
                path=["testLocation", "stations"],
            )
        return LocationRow(location_type, "", start_station, end_station, stations)

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
        return LocationRow(location_type, direction, "", "", ())

    start_station = _require_text(location.start_station, ["testLocation", "startStation"])
    end_station = _require_text(location.end_station, ["testLocation", "endStation"])
    return LocationRow(location_type, direction, start_station, end_station, ())


def _catalog_steps(item: FormalTestContent, repository: CatalogRepository) -> list[dict[str, object]]:
    """Resolve the fixed operation/result hierarchy stored in SQLite.

    Resolve rules by equipment type first, then subtype, then status/action.
    Subtype-as-equipment-type lookup is retained only as a compatibility
    fallback when the broad equipment type has no catalog entries.
    """
    equipment_type = item.equipment_type.strip()
    equipment_subtype = item.equipment_subtype.strip()
    equipment_status = item.equipment_status.strip()
    source_values = _source_values(item)
    inferred_fiber = any("感温光纤" in value for value in source_values)
    # Keep the catalog hierarchy authoritative: broad equipment type first.
    candidates = repository.list_test_contents(equipment_type=equipment_type)
    if not candidates and equipment_subtype:
        # Older catalogs sometimes store a subtype as the equipment type.
        candidates = repository.list_test_contents(equipment_type=equipment_subtype)
    if not candidates and inferred_fiber:
        candidates = repository.list_test_contents(equipment_type="感温光纤")

    if equipment_subtype and candidates:
        subtype_candidates = [
            candidate
            for candidate in candidates
            if str(candidate.get("equipmentSubtype", "")).strip().casefold() == equipment_subtype.casefold()
        ]
        if subtype_candidates:
            candidates = subtype_candidates
        else:
            generic_candidates = [
                candidate for candidate in candidates if not str(candidate.get("equipmentSubtype", "")).strip()
            ]
            if generic_candidates:
                candidates = generic_candidates
            elif any(str(candidate.get("equipmentSubtype", "")).strip() for candidate in candidates):
                # Do not fall through to another subtype under the same broad
                # equipment type. That can turn an unsupported ASD reset into an
                # unrelated 400V cutoff rule, for example.
                raise BusinessError(
                    f"设备类型“{equipment_type}”下未配置子类型“{equipment_subtype}”的规则",
                    "CATALOG_RULE_NOT_FOUND",
                )
    if not candidates:
        raise BusinessError(
            (f"未找到设备类型“{item.equipment_subtype or item.equipment_type}”对应的操作步骤和输出结果"),
            "CATALOG_RULE_NOT_FOUND",
        )
    interval, direction = _interval_context(item)
    # Status is the most specific selector. Many catalog entries intentionally
    # share a generic title such as "监视模块", which also appears in the input
    # text; matching that title first would always select the first status rule.
    selected = next(
        (
            candidate
            for candidate in candidates
            if equipment_status
            and str(candidate.get("equipmentStatus", "")).strip().casefold() == equipment_status.casefold()
        ),
        None,
    )
    # Manual fire-damper workbooks from older revisions omit the signal/status
    # column.  Keep those rows on the legacy status-less rule while explicit
    # “动作状态”/“动作反馈” rows use the cloned status-specific rules above.
    if selected is None and not equipment_status and equipment_subtype == "手动防火阀":
        selected = next(
            (candidate for candidate in candidates if not str(candidate.get("equipmentStatus", "")).strip()),
            None,
        )
    if selected is None and direction:
        selected = next(
            (
                candidate
                for candidate in candidates
                if direction in str(candidate["content"]) or direction in str(candidate.get("equipmentStatus", ""))
            ),
            None,
        )
    if selected is None:
        status_matches = [
            candidate
            for candidate in candidates
            if (status := str(candidate.get("equipmentStatus", "")).strip())
            and any(status.casefold() in value.casefold() for value in source_values)
        ]
        if status_matches:
            longest_status = max(len(str(candidate.get("equipmentStatus", "")).strip()) for candidate in status_matches)
            best_matches = [
                candidate
                for candidate in status_matches
                if len(str(candidate.get("equipmentStatus", "")).strip()) == longest_status
            ]
            if len(best_matches) == 1:
                selected = best_matches[0]
    if selected is None and inferred_fiber and not direction:
        selected = next(
            (
                candidate
                for candidate in candidates
                if "综合故障" in str(candidate.get("equipmentStatus", "")) or "综合故障" in str(candidate["content"])
            ),
            None,
        )
    if selected is None:
        content_matches = [
            candidate
            for candidate in candidates
            if (content := str(candidate.get("content", "")).strip())
            and content != equipment_type
            and any(content in value for value in source_values)
        ]
        if content_matches:
            longest_content = max(len(str(candidate["content"]).strip()) for candidate in content_matches)
            best_matches = [
                candidate for candidate in content_matches if len(str(candidate["content"]).strip()) == longest_content
            ]
            if len(best_matches) == 1:
                selected = best_matches[0]
    if selected is None and len(candidates) == 1:
        selected = candidates[0]
    if selected is None:
        selector = f" / {equipment_subtype}" if equipment_subtype else ""
        if equipment_status:
            selector += f" / {equipment_status}"
        raise BusinessError(
            f"未找到设备类型“{equipment_type}{selector}”对应的操作步骤和输出结果",
            "CATALOG_RULE_NOT_FOUND",
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
                    "description": _render_rule_text(result["description"], interval),
                    "responsibleDisciplines": disciplines,
                }
            )
        if not results:
            raise BusinessError("目录规则未配置结果输出", "CATALOG_RULE_INCOMPLETE")
        steps.append(
            {
                "description": _render_rule_text(step["description"], interval),
                "ratioChange": step["ratioChange"],
                "results": results,
            }
        )
    if not steps:
        raise BusinessError("目录规则未配置操作步骤", "CATALOG_RULE_INCOMPLETE")
    return steps


def _infer_electric_damper_statuses(request: ExcelProcessRequest, contents: list[dict[str, object]]) -> None:
    """Recover the two statuses omitted by the legacy FF2 source sheet.

    The original fire-damper workbook emits two consecutive rows for each
    FF2 device.  It has no signal/status column, so both rows arrive with the
    same FF2 fallback marker.  The catalog rules are intentionally separate:
    first row = field action feedback, second row = FAS close command.
    Explicit status text always wins over this positional compatibility rule.
    """
    occurrences: dict[str, int] = {}
    for index, item in enumerate(request.test_contents):
        subtype = item.equipment_subtype.strip()
        source = " ".join(_source_values(item)).casefold()
        is_electric_damper = subtype == "电动防火阀" or (
            item.equipment_type.strip() == "防火阀" and "ff2" in item.equipment_code.casefold()
        )
        if not is_electric_damper:
            continue
        key = (
            item.equipment_code.strip().casefold()
            or item.equipment_chinese.strip().casefold()
            or item.generated_content.strip().casefold()
        )
        occurrence = occurrences.get(key, 0)
        occurrences[key] = occurrence + 1
        current_status = item.equipment_status.strip()
        if current_status and current_status != "FF2":
            continue
        if "动作状态" in source or "关控制命令" in source:
            continue
        contents[index]["equipmentStatus"] = "动作状态" if occurrence % 2 == 0 else "关控制命令"


def prepare_formal_request(request: ExcelProcessRequest, settings: Settings) -> ExcelProcessRequest:
    """Fill omitted operationSteps from the SQLite rule catalog."""
    request = _resolve_workspace_configs(request, settings)
    if all(content.operation_steps for content in request.test_contents):
        return request
    repository = CatalogRepository(
        resolve_catalog_database_path(settings.database_path, request.integration_code),
        request.integration_code,
    )
    payload = request.model_dump(by_alias=True)
    contents = payload["testContents"]
    assert isinstance(contents, list)
    _infer_electric_damper_statuses(request, contents)
    unmatched_legacy: list[str] = []
    for index, content in enumerate(request.test_contents):
        if content.operation_steps:
            continue
        resolved_content = content
        resolved_status = str(contents[index].get("equipmentStatus", "")).strip()
        if resolved_status != content.equipment_status.strip():
            resolved_content = content.model_copy(update={"equipment_status": resolved_status})
        try:
            steps = _catalog_steps(resolved_content, repository)
        except BusinessError as error:
            if error.code != "CATALOG_RULE_NOT_FOUND":
                raise
            steps = []
        if not steps:
            label = content.equipment_code.strip() or content.equipment_chinese.strip() or f"第 {index + 1} 行"
            unmatched_legacy.append(f"{index + 1}（{label}）")
            continue
        contents[index]["operationSteps"] = steps
    if unmatched_legacy:
        raise BusinessError(
            "以下数据行没有填写联调配置编码，且未匹配到现有 FAS 兼容规则："
            + "、".join(unmatched_legacy)
            + "。请为这些行填写有效编码，或先在原有设备与测试规则中补齐规则。",
            "WORKSPACE_LEGACY_CONFIG_UNMATCHED",
            status_code=422,
        )
    return ExcelProcessRequest.model_validate(payload)


def _resolve_workspace_configs(request: ExcelProcessRequest, settings: Settings) -> ExcelProcessRequest:
    """Resolve the explicit 联调配置编码 before legacy catalog matching.

    The legacy FAS keyword matcher remains the fallback when the new column is
    empty.  A non-empty but invalid explicit code is always an error so a typo
    cannot silently select an unrelated legacy rule.
    """
    codes = [item.integration_config_code.strip() for item in request.test_contents]
    if not any(codes):
        return request
    if not (request.line_id and request.profession_id and request.project_id):
        raise BusinessError(
            "使用联调配置编码时必须先选择线路、专业和联调项目",
            "WORKSPACE_SCOPE_REQUIRED",
        )
    repository = WorkspaceRepository(resolve_catalog_database_path(settings.database_path, "T19"))
    selection = ScopeSelection(
        lineId=request.line_id,
        professionId=request.profession_id,
        projectId=request.project_id,
    )
    resolved_contents = list(request.test_contents)
    for index, code in enumerate(codes):
        if not code:
            continue
        config = repository.resolve_config(selection, code)
        if config is None:
            raise BusinessError(
                f"第 {index + 1} 行的联调配置编码“{code}”不存在、未发布或已停用",
                "WORKSPACE_CONFIG_UNMATCHED",
                path=["testContents", index, "integrationConfigCode"],
            )
        steps = []
        for step in config["steps"]:
            results = []
            for result in step["results"]:
                disciplines = result.get("responsibleDisciplines") or ["自动化"]
                results.append({"description": result["description"], "responsibleDisciplines": disciplines})
            if not results:
                raise BusinessError("联调配置未配置输出结果", "WORKSPACE_CONFIG_INCOMPLETE")
            steps.append(
                {
                    "description": step["description"],
                    "ratioChange": step["ratioChange"],
                    "results": results,
                }
            )
        if not steps:
            raise BusinessError("联调配置未配置操作步骤", "WORKSPACE_CONFIG_INCOMPLETE")
        resolved_contents[index] = request.test_contents[index].model_copy(
            update={"operation_steps": [OperationStep.model_validate(step) for step in steps]}
        )
    # Rows with a blank code may still be resolved by the legacy matcher below.
    # Revalidating the whole request here would reject their temporarily empty
    # operationSteps and turn a useful row-specific 422 into an internal error.
    return request.model_copy(update={"test_contents": resolved_contents})


def _validate_sort_indexes(request: ExcelProcessRequest) -> None:
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


def _build_workbook(request: ExcelProcessRequest) -> FormalWorkbook:
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


_CANONICAL_FILENAME_PATTERN = re.compile(
    r"^(?P<project>[^-]+)-(?P<station>.+?)-(?P<number>\d{2})-"
    r"(?P<function>.+?)-(?P<device>.+?)_(?:\d{8})(?:\d{6})?_导入版V1$"
)

_FILENAME_PROFILES: tuple[tuple[str, str, str, tuple[str, ...]], ...] = (
    ("01", "FAS设备信息监视", "烟感和温感", ("烟感和温感", "烟感", "温感")),
    ("02", "FAS设备信息监视", "区间手消报", ("区间手消报",)),
    ("02", "FAS设备信息监视", "手报和消火栓", ("手报和消火栓",)),
    ("03", "FAS设备信息监视", "吸气式主机", ("吸气式主机", "ASD")),
    ("04", "FAS设备信息监视", "感温电缆", ("感温电缆",)),
    ("05", "FAS设备信息监视", "感温光纤", ("感温光纤",)),
    ("06", "外部接口测试", "AFC", ("AFC",)),
    ("07", "外部接口测试", "EPS", ("EPS",)),
    ("08", "外部接口测试", "垂梯", ("垂直电梯", "垂梯")),
    ("09", "外部接口测试", "电动防火阀", ("电动防火阀",)),
    ("09", "外部接口测试", "手动防火阀", ("手动防火阀",)),
    ("10", "外部接口测试", "防火卷帘", ("防火卷帘",)),
    ("11", "外部接口测试", "专用消防风机", ("专用消防风机", "排烟机", "加压送风机")),
    ("12", "外部接口测试", "风机连锁风阀", ("风机连锁风阀", "风阀")),
    ("13", "外部接口测试", "400V切非", ("400V切非", "切非")),
    ("14", "外部接口测试", "声光报警器", ("声光报警器", "声光")),
    ("15", "外部接口测试", "消防泵", ("消防泵",)),
    ("16", "外部接口测试", "PA", ("广播交替模块", "PA")),
    ("17", "外部接口测试", "防火门", ("防火门",)),
    ("18", "外部接口测试", "门禁释放", ("门禁释放", "门禁")),
    (
        "19",
        "外部接口测试",
        "电气火灾、消防电源、应急疏散",
        ("电气火灾、消防电源、应急疏散", "电气火灾"),
    ),
    ("20", "气灭房间功能测试", "", ("气灭房间功能测试", "气灭房间", "气灭测试")),
    ("22", "外部接口测试", "消火栓点灯", ("消火栓按钮点灯", "消火栓点灯")),
    ("23", "FAS设备信息监视", "主机手自动、人工确认等", ("主机手自动", "人工确认", "人工确定按钮")),
    ("24", "FAS设备信息监视", "区间-消防电话和插孔电话", ("区间-消防电话和插孔电话", "区间电话")),
    ("24", "FAS设备信息监视", "站内-消防电话和插孔电话", ("站内-消防电话和插孔电话", "站内电话")),
)


def _filename_source_text(request: ExcelProcessRequest) -> str:
    return " ".join(
        value.strip()
        for value in (
            request.source_filename,
            *(content.generated_content for content in request.test_contents),
            *(content.equipment_chinese for content in request.test_contents),
            *(content.equipment_subtype for content in request.test_contents),
            *(content.equipment_type for content in request.test_contents),
        )
        if value and value.strip()
    )


def _filename_profile(request: ExcelProcessRequest) -> tuple[str, str, str]:
    # The classified subtype is the most reliable signal for telephone
    # workbooks. Other rows or the uploaded workbook's old canonical filename
    # can mention both station and interval terminology.
    classified_subtypes = {
        content.equipment_subtype.strip()
        for content in request.test_contents
        if content.equipment_subtype.strip() in {"区间电话", "站内电话"}
    }
    if len(classified_subtypes) == 1:
        subtype = next(iter(classified_subtypes))
        if subtype == "站内电话":
            return "24", "FAS设备信息监视", "站内-消防电话和插孔电话"
        return "24", "FAS设备信息监视", "区间-消防电话和插孔电话"

    source_stem = re.sub(r"\.[^.\\/]+$", "", request.source_filename.strip())
    canonical = _CANONICAL_FILENAME_PATTERN.match(source_stem)
    if canonical:
        device = re.sub(r"^(?:设计新增|新增)-", "", canonical.group("device"))
        return (
            canonical.group("number"),
            canonical.group("function"),
            device,
        )

    source_text = _filename_source_text(request)
    for number, function, device, keywords in _FILENAME_PROFILES:
        if any(keyword.casefold() in source_text.casefold() for keyword in keywords):
            return number, function, device
    equipment_types = tuple(
        dict.fromkeys(
            content.equipment_subtype.strip() or content.equipment_type.strip()
            for content in request.test_contents
            if (content.equipment_subtype.strip() or content.equipment_type.strip())
        )
    )
    device = "和".join(equipment_types) if equipment_types else "未命名"
    function = "FAS设备信息监视" if "监视模块" in source_text else "外部接口测试"
    return "00", function, device


def _formal_filename(request: ExcelProcessRequest, workbook: FormalWorkbook, generated_at: datetime) -> str:
    station = (
        workbook.location.stations[0]
        if workbook.location.stations
        else (workbook.location.start_station or workbook.location.location_type)
    )
    number, function, device = _filename_profile(request)
    components = [
        _filename_component(request.integration_code),
        _filename_component(station),
        number,
        _filename_component(function),
        _filename_component(device),
    ]
    return "-".join(components) + f"_{generated_at.strftime('%Y%m%d')}_{FORMAL_FILENAME_SUFFIX}.xls"


def process_formal_request(
    request: ExcelProcessRequest,
    settings: Settings,
    *,
    generated_at: datetime | None = None,
) -> ProcessedFile:
    """Generate a formal file only through the explicit v2 contract."""
    request = prepare_formal_request(request, settings)
    workbook = _build_workbook(request)
    content = build_formal_workbook(workbook, settings.template_path)
    filename = _formal_filename(request, workbook, generated_at or datetime.now().astimezone())
    return ProcessedFile(content=content, filename=filename, media_type=XLS_MEDIA_TYPE)
