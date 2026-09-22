from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


def _client(tmp_path: Path, **overrides: str | None) -> TestClient:
    return TestClient(
        create_app(
            Settings(
                mode="mock",
                database_path=tmp_path / "catalog.sqlite3",
                auth_username=overrides.get("auth_username"),
                auth_password=overrides.get("auth_password"),
                auth_display_name=overrides.get("auth_display_name"),
            )
        )
    )


def test_login_returns_existing_frontend_response_shape(tmp_path: Path) -> None:
    with _client(
        tmp_path,
        auth_username="admin",
        auth_password="123456",
        auth_display_name="管理员",
    ) as client:
        response = client.post(
            "/api/auth/login",
            json={
                "username": "admin",
                "password": "123456",
                "agree": True,
                "remember": False,
            },
        )

    assert response.status_code == 200
    data = response.json()["data"]
    assert isinstance(data["token"], str)
    assert len(data["token"]) >= 32
    assert data["userInfo"] == {"username": "admin", "name": "管理员"}


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

    assert response.status_code == 503
    assert response.json()["code"] == "AUTH_NOT_CONFIGURED"
