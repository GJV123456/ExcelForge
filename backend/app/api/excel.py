from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import Response

from app.schemas.excel import ExcelProcessRequest, ExcelProcessV2Request
from app.services.excel_service import build_workbook

router = APIRouter(prefix="/api", tags=["excel"])


@router.post("/excel/process", response_class=Response)
def process_excel(payload: ExcelProcessRequest) -> Response:
    content = build_workbook(payload)
    return Response(
        content=content,
        media_type="application/vnd.ms-excel",
        headers={"Content-Disposition": 'attachment; filename="最终导入表.xls"'},
    )


@router.post("/v2/excel/process", response_class=Response)
def process_excel_v2(payload: ExcelProcessV2Request) -> Response:
    content = build_workbook(payload)
    return Response(
        content=content,
        media_type="application/vnd.ms-excel",
        headers={"Content-Disposition": 'attachment; filename="最终导入表.xls"'},
    )
