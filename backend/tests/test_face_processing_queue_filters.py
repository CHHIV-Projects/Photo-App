"""Regression tests for face-processing actionable queue counts."""

from __future__ import annotations

import unittest
from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.models.duplicate_group import DuplicateGroup
from app.models.event import Event
from app.models.face import Face
from app.models.face_cluster import FaceCluster
from app.models.person import Person
from app.models.place import Place
from app.services.face.face_processing_service import _count_pending
from app.services.vision.face_detector import load_assets_for_incremental_face_detection


class FaceProcessingQueueFilterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite:///:memory:", future=True)
        for table in (
            Place.__table__,
            Event.__table__,
            DuplicateGroup.__table__,
            Person.__table__,
            FaceCluster.__table__,
            Asset.__table__,
            Face.__table__,
        ):
            table.create(bind=self.engine)
        self.session = Session(self.engine)

    def tearDown(self) -> None:
        self.session.close()
        self.engine.dispose()

    def _asset(
        self,
        sha256: str,
        extension: str,
        face_detection_completed_at: datetime | None = None,
    ) -> Asset:
        return Asset(
            sha256=sha256,
            vault_path=f"C:/vault/{sha256}{extension}",
            original_filename=f"{sha256}{extension}",
            original_source_path=f"C:/source/{sha256}{extension}",
            extension=extension,
            size_bytes=123,
            modified_timestamp_utc=datetime(2026, 7, 5, 12, 0, 0, tzinfo=timezone.utc),
            face_detection_completed_at=face_detection_completed_at,
        )

    def test_pending_counts_match_actionable_face_processing_queues(self) -> None:
        completed_at = datetime(2026, 7, 5, 13, 0, 0, tzinfo=timezone.utc)
        self.session.add_all(
            [
                self._asset("image-pending", ".JPG"),
                self._asset("video-pending", ".mov"),
                self._asset("image-complete", ".jpg", face_detection_completed_at=completed_at),
                FaceCluster(id=1),
                Face(
                    asset_sha256="image-pending",
                    bbox_x=0,
                    bbox_y=0,
                    bbox_width=10,
                    bbox_height=10,
                    confidence_score=0.9,
                    embedding_json="[0.1]",
                    is_manually_unassigned=False,
                ),
                Face(
                    asset_sha256="image-pending",
                    bbox_x=1,
                    bbox_y=1,
                    bbox_width=10,
                    bbox_height=10,
                    confidence_score=0.9,
                    embedding_json="[0.2]",
                    is_manually_unassigned=True,
                ),
                Face(
                    asset_sha256="image-pending",
                    bbox_x=2,
                    bbox_y=2,
                    bbox_width=10,
                    bbox_height=10,
                    confidence_score=0.9,
                    embedding_json=None,
                    is_manually_unassigned=False,
                ),
            ]
        )
        self.session.commit()

        pending_detection, pending_embedding, pending_clustering = _count_pending(self.session)
        detection_queue = load_assets_for_incremental_face_detection(self.session)

        self.assertEqual(pending_detection, 1)
        self.assertEqual([asset.sha256 for asset in detection_queue], ["image-pending"])
        self.assertEqual(pending_embedding, 1)
        self.assertEqual(pending_clustering, 1)


if __name__ == "__main__":
    unittest.main()
