"""Application configuration utilities."""

from dataclasses import dataclass
import os
from pathlib import Path

from dotenv import load_dotenv


BACKEND_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(dotenv_path=BACKEND_ROOT / ".env", override=True)


DEFAULT_APPROVED_EXTENSIONS = ".jpg,.jpeg,.png,.gif,.bmp,.tif,.tiff,.heic,.mp4,.mov,.avi,.mkv"


@dataclass(frozen=True)
class Settings:
	"""Runtime settings loaded from environment variables."""

	app_name: str = os.getenv("APP_NAME", "AI Photo Organizer API")
	app_version: str = os.getenv("APP_VERSION", "0.1.0")
	postgres_host: str = os.getenv("POSTGRES_HOST", "localhost")
	postgres_port: str = os.getenv("POSTGRES_PORT", "5432")
	postgres_db: str = os.getenv("POSTGRES_DB", "photo_organizer")
	postgres_user: str = os.getenv("POSTGRES_USER", "photo_user")
	postgres_password: str = os.getenv("POSTGRES_PASSWORD", "change_me")

	approved_extensions_csv: str = os.getenv("APPROVED_EXTENSIONS", DEFAULT_APPROVED_EXTENSIONS)
	minimum_file_size_bytes: int = int(os.getenv("MINIMUM_FILE_SIZE_BYTES", str(50 * 1024)))
	drop_zone_path: str = os.getenv("DROP_ZONE_PATH", "../storage/drop_zone")
	vault_path: str = os.getenv("VAULT_PATH", "../storage/vault")
	quarantine_path: str = os.getenv("QUARANTINE_PATH", "../storage/quarantine")
	ingest_batch_size: int = int(os.getenv("INGEST_BATCH_SIZE", "50"))
	ingest_total_limit: int | None = (
		int(os.getenv("INGEST_TOTAL_LIMIT", "").strip())
		if os.getenv("INGEST_TOTAL_LIMIT", "").strip()
		else None
	)
	event_cluster_gap_seconds: int = int(os.getenv("EVENT_CLUSTER_GAP_SECONDS", "14400"))
	duplicate_hamming_threshold: int = int(os.getenv("DUPLICATE_HAMMING_THRESHOLD", "10"))
	duplicate_resolution_band_ratio: float = float(os.getenv("DUPLICATE_RESOLUTION_BAND_RATIO", "0.25"))
	duplicate_capture_window_hours: int = int(os.getenv("DUPLICATE_CAPTURE_WINDOW_HOURS", "24"))
	duplicate_capture_window_enabled: bool = (
		os.getenv("DUPLICATE_CAPTURE_WINDOW_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"}
	)
	face_detector_model_path: str = os.getenv(
		"FACE_MODEL_PATH",
		"app/services/vision/models/face_detection_yunet_2023mar.onnx",
	)
	face_detection_confidence_threshold: float = float(os.getenv("FACE_DETECTION_CONFIDENCE_THRESHOLD", "0.7"))
	face_detection_resize_longest_side: int = int(os.getenv("FACE_DETECTION_RESIZE_LONGEST_SIDE", "1024"))
	face_embedding_model: str = os.getenv("FACE_EMBEDDING_MODEL", "Facenet")
	face_cluster_similarity_threshold: float = float(os.getenv("FACE_CLUSTER_SIMILARITY_THRESHOLD", "0.7"))
	face_cluster_ambiguity_margin: float = float(os.getenv("FACE_CLUSTER_AMBIGUITY_MARGIN", "0.02"))
	person_suggestion_high_threshold: float = float(os.getenv("PERSON_SUGGESTION_HIGH_THRESHOLD", "0.75"))
	person_suggestion_tentative_threshold: float = float(os.getenv("PERSON_SUGGESTION_TENTATIVE_THRESHOLD", "0.60"))
	person_suggestion_ambiguity_margin: float = float(os.getenv("PERSON_SUGGESTION_AMBIGUITY_MARGIN", "0.05"))
	person_suggestion_max_candidates: int = int(os.getenv("PERSON_SUGGESTION_MAX_CANDIDATES", "3"))
	content_tag_min_confidence: float = float(os.getenv("CONTENT_TAG_MIN_CONFIDENCE", "0.25"))
	content_tag_max_per_asset: int = int(os.getenv("CONTENT_TAG_MAX_PER_ASSET", "5"))
	face_embedding_crop_margin_ratio: float = float(os.getenv("FACE_EMBEDDING_CROP_MARGIN_RATIO", "0.1"))
	frontend_allowed_origins_csv: str = os.getenv(
		"FRONTEND_ALLOWED_ORIGINS",
		"http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001,http://127.0.0.1:3001",
	)
	google_maps_api_key: str = os.getenv("GOOGLE_MAPS_API_KEY", "").strip()
	place_geocode_max_calls_per_run: int = int(os.getenv("PLACE_GEOCODE_MAX_CALLS_PER_RUN", "100"))

	@property
	def database_url(self) -> str:
		"""Build the SQLAlchemy connection URL for PostgreSQL."""
		return (
			"postgresql+psycopg2://"
			f"{self.postgres_user}:{self.postgres_password}"
			f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
		)

	@property
	def approved_extensions(self) -> frozenset[str]:
		"""Return approved file extensions as a normalized set."""
		normalized = {
			extension.strip().lower()
			for extension in self.approved_extensions_csv.split(",")
			if extension.strip()
		}
		with_dot = {
			extension if extension.startswith(".") else f".{extension}"
			for extension in normalized
		}
		return frozenset(with_dot)

	@property
	def frontend_allowed_origins(self) -> tuple[str, ...]:
		"""Return allowed frontend origins for local-development CORS."""
		origins = tuple(
			origin.strip()
			for origin in self.frontend_allowed_origins_csv.split(",")
			if origin.strip()
		)
		return origins


settings = Settings()
