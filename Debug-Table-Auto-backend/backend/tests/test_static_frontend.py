from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


def test_static_frontend_and_spa_fallback_do_not_shadow_api(tmp_path: Path) -> None:
    frontend = tmp_path / "frontend_dist"
    assets = frontend / "assets"
    assets.mkdir(parents=True)
    (frontend / "index.html").write_text('<div id="app"></div>', encoding="utf-8")
    (assets / "app.js").write_text("window.ready=true", encoding="utf-8")
    app = create_app(Settings(frontend_dist_path=frontend))

    with TestClient(app) as client:
        root = client.get("/")
        login = client.get("/login")
        asset = client.get("/assets/app.js")
        health = client.get("/api/health")
        missing_api = client.get("/api/not-found")

    assert root.status_code == 200 and 'id="app"' in root.text
    assert login.status_code == 200 and login.text == root.text
    assert asset.status_code == 200 and asset.text == "window.ready=true"
    assert health.status_code == 200 and health.json()["status"] == "ok"
    assert missing_api.status_code == 404
    assert missing_api.headers["content-type"].startswith("application/json")

