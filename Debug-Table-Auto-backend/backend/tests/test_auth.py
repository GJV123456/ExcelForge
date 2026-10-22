from __future__ import annotations

import sqlite3
from pathlib import Path

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


def _client(tmp_path: Path, **overrides: str | None) -> TestClient:
    return TestClient(
        create_app(
            Settings(
                mode="formal",
                database_path=tmp_path / "catalog.sqlite3",
                auth_username=overrides.get("auth_username"),
                auth_password=overrides.get("auth_password"),
                auth_display_name=overrides.get("auth_display_name"),
            )
        )
    )


def test_login_returns_existing_frontend_response_shape(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        register = client.post(
            "/api/auth/register",
            json={
                "username": "operator",
                "password": "secret123",
                "confirmPassword": "secret123",
                "displayName": "操作员",
                "agree": True,
            },
        )
        assert register.status_code == 200
        response = client.post(
            "/api/auth/login",
            json={
                "username": "operator",
                "password": "secret123",
                "agree": True,
                "remember": False,
            },
        )

    assert response.status_code == 200
    data = response.json()["data"]
    assert isinstance(data["token"], str)
    assert len(data["token"]) >= 32
    assert data["userInfo"] == {"username": "operator", "name": "操作员"}


def test_login_rejects_invalid_credentials(tmp_path: Path) -> None:
    with _client(tmp_path, auth_username="admin", auth_password="123456") as client:
        response = client.post(
            "/api/auth/login",
            json={
                "username": "admin",
                "password": "wrong",
                "agree": True,
                "remember": True,
            },
        )

    assert response.status_code == 401
    assert response.json()["code"] == "AUTH_INVALID_CREDENTIALS"


def test_login_requires_terms_agreement(tmp_path: Path) -> None:
    with _client(tmp_path, auth_username="admin", auth_password="123456") as client:
        response = client.post(
            "/api/auth/login",
            json={
                "username": "admin",
                "password": "123456",
                "agree": False,
                "remember": False,
            },
        )

    assert response.status_code == 400
    assert response.json()["code"] == "AUTH_AGREEMENT_REQUIRED"
    assert response.json()["path"] == ["agree"]


def test_login_has_no_hard_coded_credentials(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        response = client.post(
            "/api/auth/login",
            json={
                "username": "admin",
                "password": "123456",
                "agree": True,
                "remember": False,
            },
        )

    assert response.status_code == 401
    assert response.json()["code"] == "AUTH_INVALID_CREDENTIALS"


def test_registered_user_can_change_password(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        registered = client.post(
            "/api/auth/register",
            json={
                "username": "operator",
                "password": "secret123",
                "confirmPassword": "secret123",
                "displayName": "操作员",
                "agree": True,
            },
        )
        token = registered.json()["data"]["token"]
        changed = client.post(
            "/api/auth/change-password",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "currentPassword": "secret123",
                "newPassword": "newsecret123",
                "confirmPassword": "newsecret123",
            },
        )
        old_session = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        login = client.post(
            "/api/auth/login",
            json={
                "username": "operator",
                "password": "newsecret123",
                "agree": True,
                "remember": False,
            },
        )

    assert changed.status_code == 200
    assert old_session.status_code == 401
    assert login.status_code == 200


def test_registered_account_is_persisted_and_reloaded_from_sqlite(tmp_path: Path) -> None:
    database_path = tmp_path / "catalog.sqlite3"
    with _client(tmp_path) as client:
        registered = client.post(
            "/api/auth/register",
            json={
                "username": "persisted",
                "password": "secret123",
                "confirmPassword": "secret123",
                "displayName": "持久化用户",
                "agree": True,
            },
        )
    assert registered.status_code == 200

    with sqlite3.connect(database_path) as connection:
        row = connection.execute(
            "SELECT password_hash FROM auth_users WHERE username = ?",
            ("persisted",),
        ).fetchone()
    assert row is not None
    assert row[0].startswith("pbkdf2_sha256$")
    assert row[0] != "secret123"

    with _client(tmp_path) as client:
        login = client.post(
            "/api/auth/login",
            json={
                "username": "persisted",
                "password": "secret123",
                "agree": True,
                "remember": False,
            },
        )
    assert login.status_code == 200
