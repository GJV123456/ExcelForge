"""Application exceptions and public JSON error handlers."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class BusinessError(Exception):
    """A safe, expected error that can be returned to the API client."""

    def __init__(
        self,
        detail: str,
        code: str,
        *,
        path: list[str | int] | None = None,
        status_code: int = 400,
    ) -> None:
        super().__init__(detail)
        self.detail = detail
        self.code = code
        self.path = path
        self.status_code = status_code


def _request_id(request: Request) -> str:
    return str(getattr(request.state, "request_id", "unknown"))


def _error_body(
    *,
    detail: str,
    code: str,
    request_id: str,
    path: list[str | int] | None = None,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "detail": detail,
        "code": code,
        "requestId": request_id,
    }
    if path is not None:
        body["path"] = path
    return body


def register_exception_handlers(app: FastAPI) -> None:
    """Register the JSON error contract on an application."""

    @app.exception_handler(BusinessError)
    async def handle_business_error(request: Request, error: BusinessError) -> JSONResponse:
        return JSONResponse(
            status_code=error.status_code,
            content=_error_body(
                detail=error.detail,
                code=error.code,
                path=error.path,
                request_id=_request_id(request),
            ),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, error: RequestValidationError) -> JSONResponse:
        first_error = error.errors()[0] if error.errors() else {}
        location = list(first_error.get("loc", ()))
        if location and location[0] == "body":
            location = location[1:]
        return JSONResponse(
            status_code=422,
            content=_error_body(
                detail=str(first_error.get("msg", "Request validation failed")),
                code="REQUEST_VALIDATION_ERROR",
                path=location or None,
                request_id=_request_id(request),
            ),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, error: Exception) -> JSONResponse:
        request_id = _request_id(request)
        logger.exception("Unhandled request error request_id=%s", request_id, exc_info=error)
        return JSONResponse(
            status_code=500,
            content=_error_body(
                detail="文件生成失败，请联系管理员并提供请求 ID",
                code="INTERNAL_ERROR",
                request_id=request_id,
            ),
        )
