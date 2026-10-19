"""FastAPI application factory."""

from __future__ import annotations

from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse

from app.api.auth import router as auth_router
from app.api.catalog import router as catalog_router
from app.api.health import router as health_router
from app.api.generation import router as generation_router
from app.api.excel import router as excel_router
from app.config import Settings
from app.db.catalog import CatalogRepository
from app.db.auth import AuthRepository
from app.db.generation import GenerationRepository
from app.exceptions import register_exception_handlers
from app.resource_paths import (
    resolve_catalog_database_path,
    resolve_database_path,
    resolve_frontend_dist_path,
)


def _register_frontend(application: FastAPI, settings: Settings) -> None:
    frontend_dist = resolve_frontend_dist_path(settings.frontend_dist_path)
    index_file = frontend_dist / "index.html"
    if not index_file.is_file():
        return

    @application.get("/{full_path:path}", include_in_schema=False)
    def serve_frontend(full_path: str) -> FileResponse:
        if full_path == "api" or full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not Found")
        candidate = (frontend_dist / full_path).resolve()
        try:
            candidate.relative_to(frontend_dist.resolve())
        except ValueError as error:
            raise HTTPException(status_code=404, detail="Not Found") from error
        if candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(index_file)


def create_app(settings: Settings | None = None) -> FastAPI:
    application = FastAPI(title="ExcelForge API", version="1.0.0")
    application.state.settings = settings or Settings.from_environment()
    application.state.catalog_database_path = resolve_database_path(
        application.state.settings.database_path
    )
    application.state.auth_repository = AuthRepository(
        resolve_database_path(application.state.settings.database_path)
    )
    application.state.generation_repository = GenerationRepository(
        resolve_database_path(application.state.settings.database_path)
    )

    def catalog_repository_for(integration_code: str = "T19") -> CatalogRepository:
        return CatalogRepository(
            resolve_catalog_database_path(
                application.state.settings.database_path, integration_code
            ),
            integration_code,
        )

    application.state.catalog_repository_for = catalog_repository_for

    @application.middleware("http")
    async def add_request_id(request: Request, call_next):  # type: ignore[no-untyped-def]
        request_id = request.headers.get("X-Request-ID") or str(uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

    register_exception_handlers(application)
    application.include_router(auth_router)
    application.include_router(catalog_router)
    application.include_router(generation_router)
    application.include_router(health_router)
    application.include_router(excel_router)
    _register_frontend(application, application.state.settings)
    return application


app = create_app()

