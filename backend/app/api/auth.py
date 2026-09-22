from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login")
def login(payload: dict) -> dict:
    return {"data": {"token": "mock-token", "userInfo": {"username": payload.get("username", ""), "name": "管理员"}}}

