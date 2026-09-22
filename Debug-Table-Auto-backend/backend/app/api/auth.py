"""Compatibility login endpoint for the existing frontend."""

from __future__ import annotations

import hmac
import secrets

from fastapi import APIRouter, Request
from typing_extensions import TypedDict

from app.exceptions import BusinessError
from app.schemas.auth import LoginRequest

router = APIRouter(prefix="/api/auth", tags=["auth"])


class UserInfo(TypedDict):
    username: str
    name: str


class LoginData(TypedDict):
    token: str
    userInfo: UserInfo


class LoginResponse(TypedDict):
    data: LoginData


@router.post("/login")
def login(payload: LoginRequest, request: Request) -> LoginResponse:
    settings = request.app.state.settings
    if settings.auth_username is None or settings.auth_password is None:
        raise BusinessError(
            "登录凭据尚未配置",
            "AUTH_NOT_CONFIGURED",
            status_code=503,
        )
    if not payload.agree:
        raise BusinessError(
            "请先同意隐私条款和服务条款",
            "AUTH_AGREEMENT_REQUIRED",
            path=["agree"],
        )
    username_matches = hmac.compare_digest(payload.username, settings.auth_username)
    password_matches = hmac.compare_digest(payload.password, settings.auth_password)
    if not username_matches or not password_matches:
        raise BusinessError(
            "用户名或密码错误",
            "AUTH_INVALID_CREDENTIALS",
            status_code=401,
        )
    display_name = settings.auth_display_name or settings.auth_username
    return {
        "data": {
            "token": secrets.token_urlsafe(32),
            "userInfo": {"username": settings.auth_username, "name": display_name},
        }
    }
