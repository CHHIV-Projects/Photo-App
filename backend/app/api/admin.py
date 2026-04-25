"""API routes for Admin summary and foundation views."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.schemas.admin import AdminSummaryResponse
from app.services.admin import build_admin_summary

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/summary", response_model=AdminSummaryResponse)
def get_admin_summary(db: Session = Depends(get_db_session)) -> AdminSummaryResponse:
    """Return read-only system-level counts for Admin workspace cards."""
    return build_admin_summary(db)
