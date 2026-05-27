"""API routes for Visual Enrichment candidate selection and run controls."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.schemas.visual_enrichment import (
    VisualEnrichmentCandidatePreviewRequest,
    VisualEnrichmentCandidatePreviewResponse,
    VisualEnrichmentRunRequest,
    VisualEnrichmentRunResponse,
)
from app.services.vision.visual_enrichment_service import (
    preview_visual_enrichment_candidates,
    run_visual_enrichment_landmark_detection,
)

router = APIRouter(prefix="/api/visual-enrichment", tags=["visual-enrichment"])


@router.post("/candidates/preview", response_model=VisualEnrichmentCandidatePreviewResponse)
def preview_candidates_endpoint(
    payload: VisualEnrichmentCandidatePreviewRequest,
    db: Session = Depends(get_db_session),
) -> VisualEnrichmentCandidatePreviewResponse:
    """Preview candidate assets from the selected Visual Enrichment pool."""
    try:
        return preview_visual_enrichment_candidates(db, payload=payload)
    except ValueError as exc:
        message = str(exc)
        status_code = 404 if "does not exist" in message else 400
        raise HTTPException(status_code=status_code, detail=message) from exc


@router.post("/run-google-vision", response_model=VisualEnrichmentRunResponse)
def run_google_vision_endpoint(
    payload: VisualEnrichmentRunRequest,
    db: Session = Depends(get_db_session),
) -> VisualEnrichmentRunResponse:
    """Run controlled landmark detection on explicit assets from preview."""
    try:
        return run_visual_enrichment_landmark_detection(db, payload=payload)
    except ValueError as exc:
        message = str(exc)
        status_code = 404 if "does not exist" in message else 400
        raise HTTPException(status_code=status_code, detail=message) from exc
