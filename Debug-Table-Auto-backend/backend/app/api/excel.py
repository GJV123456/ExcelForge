"""Health and Excel processing HTTP routes."""

from __future__ import annotations

from typing import Literal
from urllib.parse import quote

from fastapi import APIRouter, Request, Response
from typing_extensions import TypedDict

from app.schemas.excel import ExcelProcessRequest
from app.services.excel_processor import process_excel_request

router = APIRouter(prefix="/api")


class HealthResponse(TypedDict):
    status: Literal["ok"]
    mode: Literal["mock", "formal"]


@router.get("/health")
def health(request: Request) -> HealthResponse:
    return {"status": "ok", "mode": request.app.state.settings.mode}


def _content_disposition(filename: str) -> str:
    encoded_filename = quote(filename, safe="")
    return f"attachment; filename=\"mock-output.xls\"; filename*=UTF-8''{encoded_filename}"


@router.post("/excel/process", response_class=Response)
def process_excel(payload: ExcelProcessRequest, request: Request) -> Response:
    result = process_excel_request(payload, request.app.state.settings)
    return Response(
        content=result.content,
        media_type=result.media_type,
        headers={"Content-Disposition": _content_disposition(result.filename)},
    )
