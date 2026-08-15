"""Route-isolated ASGI application for the Windows Helper ingress."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.windows_helper import router as windows_helper_router
from app.db.session import SessionLocal
from app.services.windows_helper.schema import ensure_windows_helper_schema
from app.services.source_acquisition.schema import ensure_source_acquisition_schema


def create_helper_app() -> FastAPI:
    app = FastAPI(
        title="Photo Organizer Windows Helper API",
        version="1",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.include_router(windows_helper_router)

    @app.exception_handler(RequestValidationError)
    async def _redacted_validation_error(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        del request, exc
        return JSONResponse(
            status_code=422,
            content={"detail": {"code": "invalid_request", "message": "Request validation failed."}},
        )

    @app.on_event("startup")
    def _sync_helper_schema() -> None:
        db = SessionLocal()
        try:
            ensure_windows_helper_schema(db)
            ensure_source_acquisition_schema(db)
        finally:
            db.close()

    return app


app = create_helper_app()
