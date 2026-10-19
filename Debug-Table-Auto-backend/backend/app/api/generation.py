"""Read-only API for successful formal generation history."""

from __future__ import annotations

from urllib.parse import quote

from typing import Annotated

from fastapi import APIRouter, Path, Query, Request, Response

from app.db.generation import GenerationRepository
from app.exceptions import BusinessError
from app.schemas.generation import GenerationDetailResponse, GenerationListResponse

router = APIRouter(prefix="/api/generations", tags=["generations"])


def _repository(request: Request) -> GenerationRepository:
    return request.app.state.generation_repository


@router.get("")
def list_generations(
    request: Request,
    limit: Annotated[int, Query(ge=1, le=20)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    integration_code: Annotated[str | None, Query(alias="integrationCode", min_length=1, max_length=32)] = None,
) -> GenerationListResponse:
    data = _repository(request).list_generations(
        limit=limit, offset=offset, integration_code=integration_code
    )
    return {"data": data, "meta": {"count": len(data)}}


@router.get("/{generation_id}")
def get_generation(
    generation_id: Annotated[str, Path(min_length=36, max_length=36)],
    request: Request,
    integration_code: Annotated[str | None, Query(alias="integrationCode", min_length=1, max_length=32)] = None,
) -> GenerationDetailResponse:
    data = _repository(request).get_generation(generation_id, integration_code)
    if data is None:
        raise BusinessError(
            "生成记录不存在",
            "GENERATION_NOT_FOUND",
            status_code=404,
        )
    return {"data": data}


@router.get("/{generation_id}/download", response_class=Response)
def download_generation(
    generation_id: Annotated[str, Path(min_length=36, max_length=36)],
    request: Request,
    integration_code: Annotated[str | None, Query(alias="integrationCode", min_length=1, max_length=32)] = None,
) -> Response:
    result = _repository(request).get_output(generation_id, integration_code)
    if result is None:
        raise BusinessError(
            "生成文件不存在或历史记录没有保存文件内容",
            "GENERATION_FILE_NOT_FOUND",
            status_code=404,
        )
    filename, content = result
    encoded_filename = quote(filename, safe="")
    return Response(
        content=content,
        media_type="application/vnd.ms-excel",
        headers={
            "Content-Disposition": (
                f"attachment; filename=\"formal-output.xls\"; "
                f"filename*=UTF-8''{encoded_filename}"
            )
        },
    )
