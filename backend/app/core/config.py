"""Application configuration utilities."""

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
	"""Runtime settings loaded from environment variables."""

	app_name: str = os.getenv("APP_NAME", "AI Photo Organizer API")
	app_version: str = os.getenv("APP_VERSION", "0.1.0")


settings = Settings()
