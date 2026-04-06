"""Run face embedding generation and face clustering."""

from __future__ import annotations

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
    cluster_face_embeddings,
    load_faces_for_embedding,
    persist_face_clusters,
)
from app.services.vision.face_embedder import generate_face_embeddings


def main() -> int:
    db_session = SessionLocal()
    try:
        face_asset_rows = load_faces_for_embedding(db_session)
        embedding_result = generate_face_embeddings(
            face_asset_rows=face_asset_rows,
            model_name=settings.face_embedding_model,
            margin_ratio=settings.face_embedding_crop_margin_ratio,
        )
        clustering_result = cluster_face_embeddings(
            embedding_items=embedding_result.embedding_items,
            similarity_threshold=settings.face_cluster_similarity_threshold,
        )
        persistence_result = persist_face_clusters(db_session, clustering_result)
    finally:
        db_session.close()

    failure_reason_counts: dict[str, int] = {}
    for item in embedding_result.failures:
        failure_reason_counts[item.reason] = failure_reason_counts.get(item.reason, 0) + 1

    output = {
        "embedding_model": settings.face_embedding_model,
        "similarity_metric": "cosine_similarity",
        "similarity_threshold": settings.face_cluster_similarity_threshold,
        "crop_margin_ratio": settings.face_embedding_crop_margin_ratio,
        "faces_in_db": len(face_asset_rows),
        "total_faces_processed": embedding_result.processed_faces,
        "embeddings_generated": embedding_result.embedded_faces,
        "clusters_created": clustering_result.clusters_created,
        "average_cluster_size": clustering_result.average_cluster_size,
        "largest_cluster_size": clustering_result.largest_cluster_size,
        "faces_assigned": persistence_result.faces_assigned,
        "failed": persistence_result.failed,
        "failure_reason_counts": failure_reason_counts,
        "failures": [item.reason for item in embedding_result.failures],
    }

    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
