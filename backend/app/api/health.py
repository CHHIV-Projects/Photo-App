"""Health check API routes.

Intended for startup readiness checks, not high-frequency monitoring.
No secrets, passwords, or connection strings are exposed in the response.
"""

from pathlib import Path

import psycopg2
import redis as redis_lib
from fastapi import APIRouter

from app.core.config import BACKEND_ROOT, RUNTIME_PROFILE, settings

router = APIRouter(tags=["health"])


def _check_database() -> str:
	"""Attempt a minimal PostgreSQL connection. Returns 'ok' or 'unreachable'."""
	try:
		conn = psycopg2.connect(
			host=settings.postgres_host,
			port=int(settings.postgres_port),
			dbname=settings.postgres_db,
			user=settings.postgres_user,
			password=settings.postgres_password,
			connect_timeout=3,
		)
		conn.close()
		return "ok"
	except Exception:
		return "unreachable"


def _check_redis() -> str:
	"""Attempt a minimal Redis PING. Returns 'ok' or 'unreachable'."""
	try:
		r = redis_lib.Redis(
			host=settings.redis_host,
			port=settings.redis_port,
			socket_connect_timeout=3,
			socket_timeout=3,
		)
		r.ping()
		return "ok"
	except Exception:
		return "unreachable"


def _check_storage() -> dict:
	"""Check vault path configuration and reachability."""
	raw = settings.vault_path
	configured = bool(raw)
	if configured:
		vault = Path(raw)
		if not vault.is_absolute():
			vault = (BACKEND_ROOT / vault).resolve()
		reachable = vault.exists()
	else:
		reachable = False
	return {"vault_path_configured": configured, "vault_path_reachable": reachable}


@router.get("/health")
def health_check() -> dict:
	"""Return service health including runtime profile, DB, Redis, and vault readiness."""
	db_status = _check_database()
	redis_status = _check_redis()
	storage_status = _check_storage()

	overall = "ok" if db_status == "ok" and redis_status == "ok" else "degraded"
	return {
		"status": overall,
		"runtime_profile": RUNTIME_PROFILE,
		"database": db_status,
		"redis": redis_status,
		"storage": storage_status,
	}
