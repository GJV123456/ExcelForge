from __future__ import annotations

from fastapi import FastAPI

from app.auth_store import AuthStore
from app.api.auth import router as auth_router
from app.api.excel import router as excel_router


def create_app() -> FastAPI:
    app = FastAPI(title="ExcelForge Backend", version="0.1.0")
    app.state.auth_store = AuthStore()
    app.include_router(auth_router)
    app.include_router(excel_router)
    return app


app = create_app()
