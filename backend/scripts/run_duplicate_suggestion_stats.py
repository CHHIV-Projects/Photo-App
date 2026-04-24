"""Report duplicate suggestion confidence and distance distribution."""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

from sqlalchemy import select

CURRENT_FILE = Path(__file__).resolve()
BACKEND_ROOT = CURRENT_FILE.parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.db.session import SessionLocal
from app.models.asset import Asset
from app.models.duplicate_rejection import DuplicateRejection
from app.services.duplicates.lineage import IMAGE_EXTENSIONS
from app.services.duplicates.suggestion_service import (
    MAX_SUGGESTION_DISTANCE,
    confidence_bucket_for_distance,
)


def _canonical_pair(sha_a: str, sha_b: str) -> tuple[str, str]:
    return (sha_a, sha_b) if sha_a <= sha_b else (sha_b, sha_a)


def _hamming_distance_int(hash_a: int, hash_b: int) -> int:
    return (hash_a ^ hash_b).bit_count()


def main() -> int:
    db = SessionLocal()
    try:
        assets = list(
            db.scalars(
                select(Asset)
                .where(Asset.phash.is_not(None), Asset.extension.in_(sorted(IMAGE_EXTENSIONS)))
                .order_by(Asset.sha256.asc())
            ).all()
        )

        rejected_pairs = {
            _canonical_pair(row.asset_sha256_a, row.asset_sha256_b)
            for row in db.scalars(select(DuplicateRejection)).all()
        }

        confidence_counts: Counter[str] = Counter()
        distance_counts: Counter[int] = Counter()
        excluded_same_group = 0
        excluded_rejected = 0

        for idx, left in enumerate(assets):
            try:
                left_hash = int(left.phash or "", 16)
            except ValueError:
                continue

            for right in assets[idx + 1 :]:
                if (
                    left.duplicate_group_id is not None
                    and right.duplicate_group_id is not None
                    and left.duplicate_group_id == right.duplicate_group_id
                ):
                    excluded_same_group += 1
                    continue

                pair = _canonical_pair(left.sha256, right.sha256)
                if pair in rejected_pairs:
                    excluded_rejected += 1
                    continue

                try:
                    right_hash = int(right.phash or "", 16)
                except ValueError:
                    continue

                distance = _hamming_distance_int(left_hash, right_hash)
                if distance > MAX_SUGGESTION_DISTANCE:
                    continue

                confidence = confidence_bucket_for_distance(distance)
                if confidence is None:
                    continue

                confidence_counts[confidence] += 1
                distance_counts[distance] += 1

        payload = {
            "assets_with_phash": len(assets),
            "rejected_pairs": len(rejected_pairs),
            "excluded_same_group_pairs": excluded_same_group,
            "excluded_rejected_pairs": excluded_rejected,
            "confidence_counts": {
                "high": int(confidence_counts.get("high", 0)),
                "medium": int(confidence_counts.get("medium", 0)),
                "low": int(confidence_counts.get("low", 0)),
            },
            "distance_counts": {str(distance): int(count) for distance, count in sorted(distance_counts.items())},
            "total_suggestions": int(sum(confidence_counts.values())),
        }
        print(json.dumps(payload, indent=2))
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
