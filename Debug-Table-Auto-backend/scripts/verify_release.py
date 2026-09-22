"""Black-box verification for a built DebugTableAuto onedir release."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from http.client import HTTPMessage
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import xlrd

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RELEASE = ROOT / "build" / "release" / "DebugTableAuto"
FIXTURE = ROOT / "backend" / "tests" / "fixtures" / "excel_process_v2_request.json"
LOGIN_PAYLOAD = json.dumps(
    {
        "username": "admin",
        "password": "123456",
        "agree": True,
        "remember": False,
    },
    ensure_ascii=False,
).encode("utf-8")


def _request(url: str, payload: bytes | None = None) -> tuple[int, bytes, HTTPMessage]:
    request = Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json; charset=utf-8"} if payload else {},
        method="POST" if payload else "GET",
    )
    with urlopen(request, timeout=5) as response:  # noqa: S310 - loopback verification only
        return response.status, response.read(), response.headers


def main() -> None:
    release = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else DEFAULT_RELEASE
    executable = release / ("DebugTableAuto.exe" if sys.platform == "win32" else "DebugTableAuto")
    if not executable.is_file():
        raise SystemExit(f"Executable is missing: {executable}")
    environment = os.environ.copy()
    for variable in (
        "EXCELFORGE_AUTH_USERNAME",
        "EXCELFORGE_AUTH_PASSWORD",
        "EXCELFORGE_AUTH_DISPLAY_NAME",
    ):
        environment.pop(variable, None)
    process = subprocess.Popen(
        [
            str(executable),
            "--host",
            "127.0.0.1",
            "--port",
            "8030",
            "--mode",
            "formal",
            "--no-browser",
        ],
        cwd=release,
        env=environment,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        for _ in range(40):
            try:
                status, body, _ = _request("http://127.0.0.1:8030/api/health")
                if status == 200 and json.loads(body)["mode"] == "formal":
                    break
            except (HTTPError, URLError, TimeoutError):
                time.sleep(0.25)
        else:
            raise SystemExit("Release did not become healthy")

        page_status, page, _ = _request("http://127.0.0.1:8030/")
        login_status, login_body, _ = _request(
            "http://127.0.0.1:8030/api/auth/login",
            LOGIN_PAYLOAD,
        )
        status, workbook_bytes, headers = _request(
            "http://127.0.0.1:8030/api/v2/excel/process",
            FIXTURE.read_bytes(),
        )
        workbook = xlrd.open_workbook(file_contents=workbook_bytes)
        login_data = json.loads(login_body)["data"]
        generation_id = headers["X-Generation-ID"]
        generation_status, generation_body, _ = _request(
            f"http://127.0.0.1:8030/api/generations/{generation_id}"
        )
        generation = json.loads(generation_body)["data"]
        assert page_status == 200 and b'<div id="app"></div>' in page
        assert login_status == 200
        assert login_data["userInfo"] == {"username": "admin", "name": "管理员"}
        assert len(login_data["token"]) >= 32
        assert status == 200 and headers.get_content_type() == "application/vnd.ms-excel"
        assert generation_status == 200
        assert generation["id"] == generation_id
        assert generation["counts"] == {
            "testContents": 2,
            "operationSteps": 3,
            "resultOutputs": 9,
            "disciplines": 11,
        }
        assert workbook.sheet_names() == [
            "测试地点",
            "测试内容",
            "操作步骤",
            "结果输出",
            "参数公式",
        ]
        assert workbook.sheet_by_name("测试地点").row_values(2) == [
            "站点",
            "",
            "角江路站",
            "角江路站",
        ]
        print(f"verified={executable}")
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()


if __name__ == "__main__":
    main()
