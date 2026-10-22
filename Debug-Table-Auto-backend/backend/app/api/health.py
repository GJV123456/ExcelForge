"""Service health endpoint."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Request
from typing_extensions import TypedDict

router = APIRouter(prefix="/api", tags=["health"])


class HealthResponse(TypedDict):
    status: Literal["ok"]
    mode: Literal["formal"]


@router.get("/health")
def health(request: Request) -> HealthResponse:
    return {"status": "ok", "mode": request.app.state.settings.mode}
