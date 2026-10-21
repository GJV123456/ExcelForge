"""Database-backed account, session and password endpoints."""

from __future__ import annotations

import hmac
from typing_extensions import TypedDict

from fastapi import APIRouter, Request

from app.db.auth import AuthRepository, AuthUser
from app.exceptions import BusinessError
from app.schemas.auth import ChangePasswordRequest, LoginRequest, RegisterRequest

router = APIRouter(prefix="/api/auth", tags=["auth"])


class UserInfo(TypedDict):
    username: str
    name: str


class LoginData(TypedDict, total=False):
    token: str
    userInfo: UserInfo
    role: str
    lineId: int | None
    professionId: int | None


class LoginResponse(TypedDict):
    data: LoginData


def _repository(request: Request) -> AuthRepository:
    return request.app.state.auth_repository


def _user_info(user: AuthUser) -> UserInfo:
    return {"username": user["username"], "name": user["displayName"]}


def _login_data(repository: AuthRepository, user: AuthUser, remember: bool) -> LoginData:
    return {
        "token": repository.create_session(user["id"], remember=remember),
        "userInfo": _user_info(user),
        "role": str(user.get("role", "super_admin")),
        "lineId": user.get("lineId"),
        "professionId": user.get("professionId"),
    }


def _migrate_configured_credential(request: Request, repository: AuthRepository) -> None:
    """Migrate an explicitly configured legacy account once, never on every login."""
    settings = request.app.state.settings
    if repository.count_users() or not settings.auth_username or not settings.auth_password:
        return
    repository.create_user(
        settings.auth_username,
        settings.auth_password,
        settings.auth_display_name or settings.auth_username,
    )


def _current_user(request: Request, authorization: str | None) -> AuthUser:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise BusinessError("登录状态已失效，请重新登录", "AUTH_UNAUTHORIZED", status_code=401)
    token = authorization[7:].strip()
    user = _repository(request).get_user_by_token(token)
    if user is None:
        raise BusinessError("登录状态已失效，请重新登录", "AUTH_UNAUTHORIZED", status_code=401)
    return user


@router.post("/register")
def register(payload: RegisterRequest, request: Request) -> LoginResponse:
    repository = _repository(request)
    _migrate_configured_credential(request, repository)
    if not payload.agree:
        raise BusinessError("请先同意隐私条款和服务条款", "AUTH_AGREEMENT_REQUIRED", path=["agree"])
    if not hmac.compare_digest(payload.password, payload.confirm_password):
        raise BusinessError(
            "两次输入的密码不一致", "AUTH_PASSWORD_CONFIRM_MISMATCH", path=["confirmPassword"]
        )
    if repository.count_users():
        raise BusinessError(
            "系统已完成初始化，请联系管理员创建账号", "AUTH_REGISTRATION_CLOSED", status_code=409
        )
    user = repository.create_user(payload.username, payload.password, payload.display_name)
    return {"data": _login_data(repository, user, remember=False)}


@router.post("/login")
def login(payload: LoginRequest, request: Request) -> LoginResponse:
    repository = _repository(request)
    _migrate_configured_credential(request, repository)
    if not payload.agree:
        raise BusinessError("请先同意隐私条款和服务条款", "AUTH_AGREEMENT_REQUIRED", path=["agree"])
    user = repository.authenticate(payload.username, payload.password)
    if user is None:
        raise BusinessError("用户名或密码错误", "AUTH_INVALID_CREDENTIALS", status_code=401)
    return {"data": _login_data(repository, user, remember=payload.remember)}


@router.post("/change-password")
def change_password(payload: ChangePasswordRequest, request: Request) -> dict[str, str]:
    current = _current_user(request, request.headers.get("Authorization"))
    if not hmac.compare_digest(payload.new_password, payload.confirm_password):
        raise BusinessError(
            "两次输入的密码不一致", "AUTH_PASSWORD_CONFIRM_MISMATCH", path=["confirmPassword"]
        )
    _repository(request).change_password(
        current["id"], payload.current_password, payload.new_password
    )
    return {"message": "密码修改成功"}


@router.get("/me")
def me(request: Request) -> dict[str, UserInfo]:
    user = _current_user(request, request.headers.get("Authorization"))
    return {
        "data": {
            **_user_info(user),
            "role": user.get("role", "super_admin"),
            "lineId": user.get("lineId"),
            "professionId": user.get("professionId"),
        }
    }


@router.post("/logout")
def logout(request: Request) -> dict[str, str]:
    authorization = request.headers.get("Authorization")
    if authorization and authorization.lower().startswith("bearer "):
        _repository(request).revoke_session(authorization[7:].strip())
    return {"message": "已退出登录"}
