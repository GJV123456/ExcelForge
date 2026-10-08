from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "excel_process_v2_request.json"


def _payload() -> dict[str, object]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _client(database_path: Path) -> TestClient:
    return TestClient(create_app(Settings(mode="formal", database_path=database_path)))


def test_successful_v2_generation_records_nested_row_mappings(tmp_path: Path) -> None:
    database_path = tmp_path / "catalog.sqlite3"
    with _client(database_path) as client:
        response = client.post(
            "/api/v2/excel/process",
            json=_payload(),
            headers={"X-Request-ID": "generation-test-request"},
        )
        generation_id = response.headers["X-Generation-ID"]
        list_response = client.get("/api/generations")
        filtered_response = client.get("/api/generations", params={"integrationCode": "T19"})
        detail_response = client.get(f"/api/generations/{generation_id}")
        download_response = client.get(f"/api/generations/{generation_id}/download")

    assert response.status_code == 200
    assert len(generation_id) == 36
    assert list_response.status_code == 200
    assert detail_response.status_code == 200
    assert download_response.status_code == 200
    assert download_response.content == response.content
    assert "attachment" in download_response.headers["content-disposition"]
    assert list_response.json()["meta"] == {"count": 1}
    summary = list_response.json()["data"][0]
    assert summary["id"] == generation_id
    assert summary["integrationCode"] == "T19"
    assert summary["requestId"] == "generation-test-request"
    assert summary["outputSha256"] == hashlib.sha256(response.content).hexdigest().upper()
    assert summary["counts"] == {
        "testContents": 2,
        "operationSteps": 3,
        "resultOutputs": 9,
        "disciplines": 11,
    }
    assert filtered_response.json()["meta"] == {"count": 1}

    detail = detail_response.json()["data"]
    assert [item["excelRowNumber"] for item in detail["testContents"]] == [3, 4]
    assert [
        step["excelRowNumber"]
        for content in detail["testContents"]
        for step in content["operationSteps"]
    ] == [3, 4, 5]
    assert [
        result["excelRowNumber"]
        for content in detail["testContents"]
        for step in content["operationSteps"]
        for result in step["results"]
    ] == list(range(3, 12))
    assert detail["testContents"][0]["operationSteps"][0]["results"][1][
        "responsibleDisciplines"
    ] == [
        {"sequenceIndex": 1, "name": "FAS"},
        {"sequenceIndex": 2, "name": "综合监控"},
    ]

    with sqlite3.connect(database_path) as connection:
        assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []


def test_failed_v2_generation_does_not_create_history(tmp_path: Path) -> None:
    database_path = tmp_path / "catalog.sqlite3"
    payload = _payload()
    payload["testLocation"]["endStation"] = "其他站"  # type: ignore[index]

    with _client(database_path) as client:
        failed = client.post("/api/v2/excel/process", json=payload)
        history = client.get("/api/generations")

    assert failed.status_code == 400
    assert history.json() == {"data": [], "meta": {"count": 0}}


def test_generation_history_validates_paging_and_missing_id(tmp_path: Path) -> None:
    with _client(tmp_path / "catalog.sqlite3") as client:
        invalid_limit = client.get("/api/generations", params={"limit": 0})
        missing = client.get("/api/generations/00000000-0000-0000-0000-000000000000")

    assert invalid_limit.status_code == 422
    assert missing.status_code == 404
    assert missing.json()["code"] == "GENERATION_NOT_FOUND"
