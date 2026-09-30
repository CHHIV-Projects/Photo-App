"""Bounded local diagnostics for the console-free packaged Helper."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import re

from .credential_store import default_state_directory


_PROTECTED_VALUE = re.compile(
    r"(?i)\b(credential|token|secret|password|pairing(?:_code)?)\s*[=:]\s*[^\s,;]+"
)


def redact_message(value: str) -> str:
    return _PROTECTED_VALUE.sub(lambda match: f"{match.group(1)}=[REDACTED]", value)


class _RedactingFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        rendered = super().format(record)
        return redact_message(rendered)


def configure_file_logging(state_directory: Path | None = None) -> logging.Logger:
    root = state_directory or default_state_directory()
    log_dir = root / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("photo_organizer_windows_helper")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()
    handler = RotatingFileHandler(
        log_dir / "helper.log",
        maxBytes=512 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    handler.setFormatter(_RedactingFormatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(handler)
    return logger
