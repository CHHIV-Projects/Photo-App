"""Run face embedding generation and face clustering."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

CURRENT_FILE = Path(__file__).resolve()
BACKEND_ROOT = CURRENT_FILE.parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import settings
from app.db.session import SessionLocal
from app.services.vision.face_clusterer import (
    assign_faces_incrementally,
    cluster_face_embeddings,
    load_faces_for_embedding,
    persist_face_clusters,
)
from app.services.vision.face_embedder import (
    generate_face_embeddings,
    load_faces_missing_embeddings,
    persist_generated_embeddings,
)
from app.services.vision.face_incremental_schema import ensure_face_incremental_schema


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run face embedding and clustering.")
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Run destructive global embedding+clustering rebuild.",
    )
    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    db_session = SessionLocal()
    try:
        schema_summary = ensure_face_incremental_schema(db_session)
        if args.rebuild:
            face_asset_rows = load_faces_for_embedding(db_session)
        else:
            face_asset_rows = load_faces_missing_embeddings(db_session)

        embedding_result = generate_face_embeddings(
            face_asset_rows=face_asset_rows,
            model_name=settings.face_embedding_model,
            margin_ratio=settings.face_embedding_crop_margin_ratio,
        )
        embeddings_persisted = persist_generated_embeddings(db_session, embedding_result.embedding_items)

        if args.rebuild:
            clustering_result = cluster_face_embeddings(
                embedding_items=embedding_result.embedding_items,
                similarity_threshold=settings.face_cluster_similarity_threshold,
            )
            persistence_result = persist_face_clusters(db_session, clustering_result)
            assignment_summary = None
        else:
            assignment_summary = assign_faces_incrementally(
                db_session,
                similarity_threshold=settings.face_cluster_similarity_threshold,
                ambiguity_margin=settings.face_cluster_ambiguity_margin,
            )
            clustering_result = None
            persistence_result = None
    finally:
        db_session.close()

    failure_reason_counts: dict[str, int] = {}
    for item in embedding_result.failures:
        failure_reason_counts[item.reason] = failure_reason_counts.get(item.reason, 0) + 1

    output = {
        "mode": "rebuild" if args.rebuild else "incremental",
        "embedding_model": settings.face_embedding_model,
        "similarity_metric": "cosine_similarity",
        "similarity_threshold": settings.face_cluster_similarity_threshold,
        "ambiguity_margin": settings.face_cluster_ambiguity_margin,
        "crop_margin_ratio": settings.face_embedding_crop_margin_ratio,
        "schema_added_columns": len(schema_summary.added_columns),
        "faces_input": len(face_asset_rows),
        "total_faces_processed": embedding_result.processed_faces,
        "embeddings_generated": embedding_result.embedded_faces,
        "embeddings_persisted": embeddings_persisted,
        "clusters_created": clustering_result.clusters_created if clustering_result else 0,
        "average_cluster_size": clustering_result.average_cluster_size if clustering_result else 0.0,
        "largest_cluster_size": clustering_result.largest_cluster_size if clustering_result else 0,
        "faces_assigned": persistence_result.faces_assigned if persistence_result else (assignment_summary.faces_considered if assignment_summary else 0),
        "assigned_to_existing_clusters": assignment_summary.assigned_to_existing_clusters if assignment_summary else 0,
        "new_clusters_created": assignment_summary.new_clusters_created if assignment_summary else 0,
        "invalid_embeddings_skipped": assignment_summary.invalid_embeddings_skipped if assignment_summary else 0,
        "failed": persistence_result.failed if persistence_result else (assignment_summary.failed if assignment_summary else 1),
        "failure_reason_counts": failure_reason_counts,
        "failures": [item.reason for item in embedding_result.failures],
    }

    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
