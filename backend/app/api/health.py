"""Health check API routes."""

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check() -> dict[str, str]:
	"""Return a basic service status response."""
	return {"status": "ok"}
