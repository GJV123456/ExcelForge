"""Formal Excel processing route."""

from __future__ import annotations

from datetime import datetime
from urllib.parse import quote

from fastapi import APIRouter, Request, Response

from app.schemas.excel import ExcelProcessRequest
from app.services.formal_processor import prepare_formal_request, process_formal_request

router = APIRouter(prefix="/api", tags=["excel"])


@router.post("/excel/process", response_class=Response)
def process_excel(payload: ExcelProcessRequest, request: Request) -> Response:
    generated_at = datetime.now().astimezone()
    settings = request.app.state.settings
    if payload.project_id:
        engine_code = request.app.state.workspace_repository.project_engine_code(payload.project_id)
        if engine_code:
            payload = payload.model_copy(update={"integration_code": engine_code})
    resolved_payload = prepare_formal_request(payload, settings)
    result = process_formal_request(
        resolved_payload,
        settings,
        generated_at=generated_at,
    )
    generation_id = request.app.state.generation_repository.record_success(
        resolved_payload,
        request_id=str(request.state.request_id),
        generated_at=generated_at,
        filename=result.filename,
        output=result.content,
    )
    filename = quote(result.filename, safe="")
    return Response(
        content=result.content,
        media_type=result.media_type,
        headers={
            "Content-Disposition": (
                f"attachment; filename=\"formal-output.xls\"; filename*=UTF-8''{filename}"
            ),
            "X-Generation-ID": generation_id,
        },
    )
