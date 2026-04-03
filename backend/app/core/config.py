"""Application configuration utilities."""

from dataclasses import dataclass
import os


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

	@property
	def database_url(self) -> str:
		"""Build the SQLAlchemy connection URL for PostgreSQL."""
		return (
			"postgresql+psycopg2://"
			f"{self.postgres_user}:{self.postgres_password}"
			f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
		)


settings = Settings()
