from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import xlrd
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.services.excel_processor import MOCK_FILENAME, XLS_MEDIA_TYPE
from app.utils.template_provider import DEFAULT_TEMPLATE_PATH, file_sha256
from app.utils.xls_writer import MOCK_SHEET_NAME, MOCK_WARNING

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "excel_process_request.json"


def _payload() -> dict[str, Any]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def test_valid_payload_returns_openable_mock_xls_without_touching_template(
    client: TestClient,
) -> None:
    template_hash = file_sha256(DEFAULT_TEMPLATE_PATH)

    response = client.post("/api/excel/process", json=_payload())

    assert response.status_code == 200
    assert response.headers["content-type"] == XLS_MEDIA_TYPE
    assert "mock-output.xls" in response.headers["content-disposition"]
    assert "%E8%81%94%E8%B0%83" in response.headers["content-disposition"]
    assert response.content.startswith(bytes.fromhex("D0CF11E0A1B11AE1"))
    assert file_sha256(DEFAULT_TEMPLATE_PATH) == template_hash

    workbook = xlrd.open_workbook(file_contents=response.content)
    assert workbook.sheet_names() == [MOCK_SHEET_NAME]
    sheet = workbook.sheet_by_index(0)
    assert sheet.cell_value(0, 0) == MOCK_WARNING
    assert sheet.cell_value(3, 0) == "站点"
    assert sheet.cell_value(6, 0) == 1
    assert sheet.cell_value(6, 1) == "站厅B端车控室烟感N1L1D01"
    assert sheet.cell_value(17, 0) == 12
    assert sheet.cell_value(17, 1) == "站厅B端男更衣室烟感N1L1D12"


def test_missing_test_location_returns_unified_422(client: TestClient) -> None:
    payload = _payload()
    del payload["testLocation"]

    response = client.post("/api/excel/process", json=payload)

    assert response.status_code == 422
    assert response.json()["code"] == "REQUEST_VALIDATION_ERROR"
    assert response.json()["path"] == ["testLocation"]


def test_test_contents_type_error_returns_422(client: TestClient) -> None:
    payload = _payload()
    payload["testContents"] = {}

    response = client.post("/api/excel/process", json=payload)

    assert response.status_code == 422
    assert response.json()["path"] == ["testContents"]


def test_sort_index_type_error_returns_422(client: TestClient) -> None:
    payload = _payload()
    payload["testContents"][0]["sortIndex"] = "1"

    response = client.post("/api/excel/process", json=payload)

    assert response.status_code == 422
    assert response.json()["path"] == ["testContents", 0, "sortIndex"]


def test_empty_contents_returns_business_error(client: TestClient) -> None:
    payload = _payload()
    payload["testContents"] = []

    response = client.post("/api/excel/process", json=payload)

    assert response.status_code == 400
    assert response.json()["code"] == "NO_TEST_CONTENTS"
    assert response.json()["path"] == ["testContents"]


def test_sort_index_is_validated_without_reordering(client: TestClient) -> None:
    payload = _payload()
    payload["testContents"][1]["sortIndex"] = 1
    original = deepcopy(payload["testContents"])

    response = client.post("/api/excel/process", json=payload)

    assert response.status_code == 400
    assert response.json()["code"] == "SORT_INDEX_NOT_STRICTLY_INCREASING"
    assert response.json()["path"] == ["testContents", 1, "sortIndex"]
    assert payload["testContents"] == original


def test_mock_delay_uses_backend_setting(monkeypatch: Any) -> None:
    observed_delays: list[float] = []
    monkeypatch.setattr("app.services.excel_processor.time.sleep", observed_delays.append)
    app = create_app(Settings(mode="mock", mock_delay_seconds=2))

    with TestClient(app) as client:
        response = client.post("/api/excel/process", json=_payload())

    assert response.status_code == 200
    assert observed_delays == [2]


def test_formal_mode_stays_disabled_without_rules() -> None:
    app = create_app(Settings(mode="formal", mock_delay_seconds=0))

    with TestClient(app) as client:
        response = client.post("/api/excel/process", json=_payload())

    assert response.status_code == 400
    assert response.json()["code"] == "BUSINESS_RULES_NOT_CONFIGURED"
    assert MOCK_FILENAME not in response.text


def test_formula_prefix_is_written_as_safe_text(client: TestClient) -> None:
    payload = _payload()
    payload["testContents"][0]["generatedContent"] = "=1+1"

    response = client.post("/api/excel/process", json=payload)

    assert response.status_code == 200
    workbook = xlrd.open_workbook(file_contents=response.content)
    assert workbook.sheet_by_index(0).cell_value(6, 1) == "'=1+1"


def test_unexpected_error_returns_safe_500(monkeypatch: Any) -> None:
    def raise_unexpected_error(*_args: Any, **_kwargs: Any) -> None:
        raise RuntimeError("internal-secret")

    monkeypatch.setattr("app.api.excel.process_excel_request", raise_unexpected_error)
    app = create_app(Settings(mode="mock", mock_delay_seconds=0))

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post("/api/excel/process", json=_payload())

    assert response.status_code == 500
    assert response.json()["code"] == "INTERNAL_ERROR"
    assert response.json()["requestId"]
    assert "internal-secret" not in response.text
