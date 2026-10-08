from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from app.schemas.auth import ChangePasswordRequest, LoginRequest, RegisterRequest

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _store(request: Request):  # type: ignore[no-untyped-def]
    return request.app.state.auth_store


def _password_error(password: str) -> None:
    if len(password) < 8:
        raise HTTPException(status_code=400, detail="密码长度不能少于 8 位")


def _current_user(request: Request) -> dict[str, object]:
    authorization = request.headers.get("Authorization", "")
    if not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="登录状态已失效，请重新登录")
    user = _store(request).user_by_token(authorization[7:].strip())
    if user is None:
        raise HTTPException(status_code=401, detail="登录状态已失效，请重新登录")
    return user


@router.post("/register")
def register(payload: RegisterRequest, request: Request) -> dict[str, object]:
    if not payload.agree:
        raise HTTPException(status_code=400, detail="请先同意隐私条款和服务条款")
    _password_error(payload.password)
    if payload.password != payload.confirmPassword:
        raise HTTPException(status_code=400, detail="两次输入的密码不一致")
    store = _store(request)
    if store.count_users():
        raise HTTPException(status_code=409, detail="系统已完成初始化，请联系管理员创建账号")
    try:
        user = store.create_user(payload.username, payload.password, payload.displayName)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    return {"data": {"token": store.create_session(int(user["id"]), False), "userInfo": {"username": user["username"], "name": user["name"]}}}


@router.post("/login")
def login(payload: LoginRequest, request: Request) -> dict[str, object]:
    if not payload.agree:
        raise HTTPException(status_code=400, detail="请先同意隐私条款和服务条款")
    user = _store(request).authenticate(payload.username, payload.password)
    if user is None:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    token = _store(request).create_session(int(user["id"]), payload.remember)
    return {"data": {"token": token, "userInfo": {"username": user["username"], "name": user["name"]}}}


@router.post("/change-password")
def change_password(payload: ChangePasswordRequest, request: Request) -> dict[str, str]:
    user = _current_user(request)
    _password_error(payload.newPassword)
    if payload.newPassword != payload.confirmPassword:
        raise HTTPException(status_code=400, detail="两次输入的密码不一致")
    if not _store(request).change_password(int(user["id"]), payload.currentPassword, payload.newPassword):
        raise HTTPException(status_code=400, detail="当前密码错误")
    return {"message": "密码修改成功"}


@router.post("/logout")
def logout(request: Request) -> dict[str, str]:
    authorization = request.headers.get("Authorization", "")
    if authorization.lower().startswith("bearer "):
        _store(request).revoke(authorization[7:].strip())
    return {"message": "已退出登录"}
