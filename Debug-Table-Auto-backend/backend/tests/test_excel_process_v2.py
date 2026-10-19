from __future__ import annotations

import json
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

import xlrd
from fastapi.testclient import TestClient

from app.config import Settings
from app.domain.workbook import (
    FormalWorkbook,
    LocationRow,
    OperationStepRow,
    ResultRow,
)
from app.domain.workbook import (
    TestContentRow as WorkbookContentRow,
)
from app.main import create_app
from app.schemas.excel_v2 import ExcelProcessV2Request
from app.services.formal_processor import process_formal_request
from app.utils.template_provider import (
    DEFAULT_TEMPLATE_PATH,
    EXPECTED_SHEET_NAMES,
    file_sha256,
)
from app.utils.xls_writer import build_formal_workbook

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "excel_process_v2_request.json"


def _payload() -> dict[str, Any]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


@contextmanager
def _formal_client() -> Iterator[TestClient]:
    with TemporaryDirectory() as directory:
        database_path = Path(directory) / "test.sqlite3"
        with TestClient(
            create_app(
                Settings(
                    mode="formal",
                    mock_delay_seconds=0,
                    database_path=database_path,
                )
            )
        ) as client:
            yield client


def test_v2_generates_deterministic_five_sheet_workbook() -> None:
    source_hash = file_sha256(DEFAULT_TEMPLATE_PATH)
    with _formal_client() as client:
        response = client.post("/api/v2/excel/process", json=_payload())

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/vnd.ms-excel"
    disposition = response.headers["content-disposition"]
    assert "T19-" in disposition
    assert "_202" in disposition
    assert "%E5%AF%BC%E5%85%A5%E7%89%88V1.xls" in disposition
    assert response.content.startswith(bytes.fromhex("D0CF11E0A1B11AE1"))
    assert file_sha256(DEFAULT_TEMPLATE_PATH) == source_hash

    workbook = xlrd.open_workbook(file_contents=response.content, formatting_info=True)
    assert tuple(workbook.sheet_names()) == EXPECTED_SHEET_NAMES

    location = workbook.sheet_by_name("测试地点")
    assert location.row_values(2) == ["站点", "", "角江路站", "角江路站"]
    assert location.cell_value(3, 0) == "end"

    contents = workbook.sheet_by_name("测试内容")
    assert contents.col_values(0, 2, 5) == ["内容A", "内容B", "end"]

    steps = workbook.sheet_by_name("操作步骤")
    assert steps.row_values(2) == [3.0, "步骤A1", "否"]
    assert steps.row_values(3) == [3.0, "步骤A2", "否"]
    assert steps.row_values(4) == [4.0, "步骤B1", "否"]
    assert steps.cell_value(5, 0) == "end"

    results = workbook.sheet_by_name("结果输出")
    assert results.col_values(0, 2, 11) == [3.0, 3.0, 3.0, 3.0, 4.0, 4.0, 4.0, 5.0, 5.0]
    assert results.cell_value(3, 2) == "FAS,综合监控"
    assert results.col_values(3, 2, 11) == [""] * 9
    assert results.cell_value(11, 0) == "end"

    formulas = workbook.sheet_by_name("参数公式")
    assert formulas.row_values(2) == ["end", "", "", "", ""]
    assert sum(formulas.cell_value(row, 0) == "end" for row in range(formulas.nrows)) == 1


def test_v2_rejects_test_style_field() -> None:
    payload = _payload()
    payload["testContents"][0]["operationSteps"][0]["results"][0]["testStyle"] = 1

    with _formal_client() as client:
        response = client.post("/api/v2/excel/process", json=payload)

    assert response.status_code == 422
    assert response.json()["path"][-1] == "testStyle"


def test_v2_requires_formal_mode() -> None:
    with TestClient(create_app(Settings(mode="mock", mock_delay_seconds=0))) as client:
        response = client.post("/api/v2/excel/process", json=_payload())

    assert response.status_code == 400
    assert response.json()["code"] == "FORMAL_MODE_DISABLED"


def test_v2_rejects_undefined_location_values() -> None:
    payload = _payload()
    payload["testLocation"]["type"] = "停车场"

    with _formal_client() as client:
        response = client.post("/api/v2/excel/process", json=payload)

    assert response.status_code == 400
    assert response.json()["code"] == "INVALID_LOCATION_TYPE"


def test_v2_requires_matching_station_endpoints() -> None:
    missing = _payload()
    mismatch = _payload()
    missing["testLocation"]["endStation"] = ""
    mismatch["testLocation"]["endStation"] = "其他站"

    with _formal_client() as client:
        missing_response = client.post("/api/v2/excel/process", json=missing)
        mismatch_response = client.post("/api/v2/excel/process", json=mismatch)

    assert missing_response.status_code == 400
    assert missing_response.json()["code"] == "REQUIRED_TEXT_EMPTY"
    assert mismatch_response.status_code == 400
    assert mismatch_response.json()["code"] == "STATION_ENDPOINTS_MISMATCH"


def test_v2_validates_sort_order_without_reordering() -> None:
    payload = _payload()
    payload["testContents"][1]["sortIndex"] = 1
    original = deepcopy(payload)

    with _formal_client() as client:
        response = client.post("/api/v2/excel/process", json=payload)

    assert response.status_code == 400
    assert response.json()["code"] == "SORT_INDEX_NOT_STRICTLY_INCREASING"
    assert payload == original


def test_v2_keeps_formula_prefix_as_text() -> None:
    payload = _payload()
    payload["testContents"][0]["operationSteps"][0]["description"] = "=1+1"

    with _formal_client() as client:
        response = client.post("/api/v2/excel/process", json=payload)

    workbook = xlrd.open_workbook(file_contents=response.content)
    cell = workbook.sheet_by_name("操作步骤").cell(2, 1)
    assert cell.ctype == xlrd.XL_CELL_TEXT
    assert cell.value == "=1+1"


def test_v2_parallel_generation_does_not_mix_requests() -> None:
    first = _payload()
    second = _payload()
    first["testContents"][0]["generatedContent"] = "并发甲"
    second["testContents"][0]["generatedContent"] = "并发乙"
    settings = Settings(mode="formal", mock_delay_seconds=0)

    def generate(payload: dict[str, Any]) -> bytes:
        request = ExcelProcessV2Request.model_validate(payload)
        return process_formal_request(request, settings).content

    with ThreadPoolExecutor(max_workers=2) as executor:
        outputs = list(executor.map(generate, (first, second)))

    values = [
        xlrd.open_workbook(file_contents=content).sheet_by_name("测试内容").cell_value(2, 0)
        for content in outputs
    ]
    assert values == ["并发甲", "并发乙"]


def test_v2_filename_contains_station_timestamp_and_unique_types() -> None:
    payload = _payload()
    payload["testContents"][0]["equipmentType"] = "烟感"
    payload["testContents"][1]["equipmentType"] = "温感"
    request = ExcelProcessV2Request.model_validate(payload)

    result = process_formal_request(
        request,
        Settings(mode="formal", mock_delay_seconds=0),
        generated_at=datetime(2026, 8, 12, 9, 8, 7),
    )

    assert result.filename == "T19-角江路站-01-FAS设备信息监视-烟感和温感_20260812_导入版V1.xls"


def test_v2_filename_uses_canonical_source_filename_and_refreshes_date() -> None:
    payload = _payload()
    payload["sourceFilename"] = (
        "T19-角江路站-03-FAS设备信息监视-吸气式主机_20251231_导入版V1.xls"
    )
    request = ExcelProcessV2Request.model_validate(payload)

    result = process_formal_request(
        request,
        Settings(mode="formal", mock_delay_seconds=0),
        generated_at=datetime(2026, 10, 19, 9, 8, 7),
    )

    assert result.filename == "T19-角江路站-03-FAS设备信息监视-吸气式主机_20261019_导入版V1.xls"


def test_v2_filename_uses_station_telephone_subtype_even_when_source_name_conflicts() -> None:
    payload = _payload()
    payload["sourceFilename"] = (
        "T19-角江路站-24-FAS设备信息监视-区间-消防电话和插孔电话_20251231_导入版V1.xls"
    )
    for item in payload["testContents"]:
        item["equipmentType"] = "特殊模块"
        item["equipmentSubtype"] = "站内电话"

    request = ExcelProcessV2Request.model_validate(payload)
    result = process_formal_request(
        request,
        Settings(mode="formal", mock_delay_seconds=0),
        generated_at=datetime(2026, 10, 19, 9, 8, 7),
    )

    assert result.filename == (
        "T19-角江路站-24-FAS设备信息监视-站内-消防电话和插孔电话_20261019_导入版V1.xls"
    )


def test_v2_writes_all_selected_stations_to_test_location_sheet() -> None:
    payload = _payload()
    payload["testLocation"]["stations"] = ["角江路站", "软件园站", "洪湾站"]
    request = ExcelProcessV2Request.model_validate(payload)

    result = process_formal_request(
        request,
        Settings(mode="formal", mock_delay_seconds=0),
        generated_at=datetime(2026, 10, 19, 9, 8, 7),
    )
    workbook = xlrd.open_workbook(file_contents=result.content)
    location = workbook.sheet_by_name("测试地点")

    assert location.row_values(2) == ["站点", "", "角江路站", "角江路站"]
    assert location.row_values(3) == ["站点", "", "软件园站", "软件园站"]
    assert location.row_values(4) == ["站点", "", "洪湾站", "洪湾站"]
    assert location.cell_value(5, 0) == "end"


def test_v2_rejects_whitespace_only_text_and_discipline_delimiters() -> None:
    whitespace_payload = _payload()
    whitespace_payload["testContents"][0]["operationSteps"][0]["description"] = "   "
    comma_payload = _payload()
    comma_payload["testContents"][0]["operationSteps"][0]["results"][0][
        "responsibleDisciplines"
    ] = ["FAS,综合监控"]

    with _formal_client() as client:
        whitespace_response = client.post("/api/v2/excel/process", json=whitespace_payload)
        comma_response = client.post("/api/v2/excel/process", json=comma_payload)

    assert whitespace_response.status_code == 422
    assert comma_response.status_code == 400
    assert comma_response.json()["code"] == "INVALID_DISCIPLINE_NAME"


def test_v2_generates_400v_cutoff_rows() -> None:
    operation_steps = [
        {
            "description": "执行切非测试",
            "ratioChange": "否",
            "results": [
                {"description": "系统显示切非状态", "responsibleDisciplines": ["FAS"]}
            ],
        }
    ]
    payload = {
        "integrationCode": "T19",
        "testLocation": {
            "type": "站点",
            "direction": "",
            "startStation": "A站",
            "endStation": "A站",
        },
        "testContents": [
            {
                "sortIndex": index,
                "generatedContent": f"{equipment_chinese}{equipment_type}{code}{suffix}",
                "equipmentCode": code,
                "equipmentType": equipment_type,
                "equipmentChinese": equipment_chinese,
                "additionalCode": suffix,
                "equipmentSubtype": "400V切非",
                "equipmentStatus": "切非反馈" if equipment_type == "监视模块" else "切非",
                "operationSteps": operation_steps,
            }
            for index, (code, equipment_type, equipment_chinese, suffix) in enumerate(
                (
                    ("P111-10", "监视模块", "B端供电房间双切箱切非反馈", "_N1L09-M01_MK-1"),
                    ("P111-10", "控制模块", "B端供电房间双切箱切非", "_N1L09-M02_MK-1"),
                    ("P210-10", "监视模块", "B端供电房间双切箱切非反馈", "_N1L09-M03_MK-1"),
                    ("P210-10", "控制模块", "B端供电房间双切箱切非", "_N1L09-M04_MK-1"),
                    ("P108-10", "监视模块", "A端区间工作照明切非反馈", "_N1L09-M05_MK-1"),
                    ("P108-10", "控制模块", "A端区间工作照明切非", "_N1L09-M06_MK-1"),
                    ("P207-10", "监视模块", "A端区间工作照明切非反馈", "_N1L09-M07_MK-1"),
                ),
                start=1,
            )
        ],
    }
    with _formal_client() as client:
        response = client.post("/api/v2/excel/process", json=payload)

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/vnd.ms-excel"


def test_writer_rejects_biff8_row_overflow_before_copying_template() -> None:
    result = ResultRow(description="结果", responsible_disciplines=("FAS",))
    step = OperationStepRow(description="步骤", ratio_change="否", results=(result,))
    content = WorkbookContentRow(1, "内容", "编码", "类型", (step,))
    workbook = FormalWorkbook(
        location=LocationRow("站点", "", "角江路站", ""),
        test_contents=(content,) * 65_534,
    )

    try:
        build_formal_workbook(workbook)
    except ValueError as error:
        assert str(error) == "BIFF8 row limit exceeded"
    else:
        raise AssertionError("row overflow must be rejected")
