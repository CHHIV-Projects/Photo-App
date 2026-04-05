"""Application configuration utilities."""

from dataclasses import dataclass
import os


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
	event_cluster_gap_seconds: int = int(os.getenv("EVENT_CLUSTER_GAP_SECONDS", "14400"))

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


settings = Settings()
