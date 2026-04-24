"""FastAPI application entrypoint."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.albums import router as albums_router
from app.api.clusters import router as clusters_router
from app.api.duplicates import router as duplicates_router
from app.api.events import router as events_router
from app.api.faces import router as faces_router
from app.api.health import router as health_router
from app.api.people import router as people_router
from app.api.photos import router as photos_router
from app.api.places import router as places_router
from app.api.search import router as search_router
from app.api.timeline import router as timeline_router
from app.core.config import settings
from app.db.session import SessionLocal
from app.services.albums.album_schema import ensure_album_schema
from app.services.duplicates.adjudication_schema import ensure_duplicate_adjudication_schema
from app.services.ingestion.ingestion_context_schema import ensure_ingestion_context_schema
from app.services.metadata.metadata_canonicalization_schema import ensure_metadata_canonicalization_schema
from app.services.duplicates.suggestion_schema import ensure_duplicate_suggestion_schema
from app.services.places.place_schema import ensure_place_schema
from app.services.photos.display_adjustment_schema import ensure_display_adjustment_schema
from app.services.vision.face_incremental_schema import ensure_face_incremental_schema


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
	app.include_router(albums_router)
	app.include_router(clusters_router)
	app.include_router(duplicates_router)
	app.include_router(events_router)
	app.include_router(faces_router)
	app.include_router(people_router)
	app.include_router(photos_router)
	app.include_router(places_router)
	app.include_router(search_router)
	app.include_router(timeline_router)

	@app.on_event("startup")
	def _sync_face_incremental_schema() -> None:
		db_session = SessionLocal()
		try:
			ensure_album_schema(db_session)
			ensure_ingestion_context_schema(db_session)
			ensure_metadata_canonicalization_schema(db_session)
			ensure_duplicate_adjudication_schema(db_session)
			ensure_duplicate_suggestion_schema(db_session)
			ensure_place_schema(db_session)
			ensure_display_adjustment_schema(db_session)
			ensure_face_incremental_schema(db_session)
		finally:
			db_session.close()

	return app


app = create_app()
