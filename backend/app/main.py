"""FastAPI application entrypoint."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.clusters import router as clusters_router
from app.api.faces import router as faces_router
from app.api.health import router as health_router
from app.api.people import router as people_router
from app.api.photos import router as photos_router
from app.core.config import settings


def create_app() -> FastAPI:
	"""Create and configure the FastAPI application."""
	app = FastAPI(title=settings.app_name, version=settings.app_version)
	review_media_dir = (Path(__file__).resolve().parents[2] / "storage" / "review").resolve()
	if review_media_dir.exists():
		app.mount("/media/review", StaticFiles(directory=str(review_media_dir)), name="review-media")
	vault_media_dir = (Path(__file__).resolve().parents[2] / "storage" / "vault").resolve()
	if vault_media_dir.exists():
		app.mount("/media/assets", StaticFiles(directory=str(vault_media_dir)), name="assets-media")
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
	app.include_router(photos_router)
	return app


app = create_app()
