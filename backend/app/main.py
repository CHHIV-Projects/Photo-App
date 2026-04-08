"""FastAPI application entrypoint."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.clusters import router as clusters_router
from app.api.faces import router as faces_router
from app.api.health import router as health_router
from app.api.people import router as people_router
from app.core.config import settings


def create_app() -> FastAPI:
	"""Create and configure the FastAPI application."""
	app = FastAPI(title=settings.app_name, version=settings.app_version)
	app.add_middleware(
		CORSMiddleware,
		allow_origins=list(settings.frontend_allowed_origins),
		allow_credentials=True,
		allow_methods=["*"],
		allow_headers=["*"],
	)
	app.include_router(health_router)
	app.include_router(clusters_router)
	app.include_router(faces_router)
	app.include_router(people_router)
	return app


app = create_app()
