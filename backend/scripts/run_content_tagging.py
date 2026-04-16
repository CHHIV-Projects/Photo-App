"""Run incremental content tagging on vault images.

Usage
-----
    python backend/scripts/run_content_tagging.py
    python backend/scripts/run_content_tagging.py --rebuild
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from sqlalchemy import delete

CURRENT_FILE = Path(__file__).resolve()
BACKEND_ROOT = CURRENT_FILE.parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.asset_content_tag import AssetContentTag
from app.services.content.content_tag_schema import ensure_content_tag_schema
from app.services.content.content_tagger import (
    ensure_content_tag_runtime_available,
    load_assets_for_content_tagging,
    persist_content_tags,
    run_content_tagging,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run content tagging on vault images.")
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Delete all existing content tags and re-tag every canonical asset.",
    )
    return parser


def main() -> int:
    args = _build_parser().parse_args()

    vault_root = Path(settings.vault_path).resolve()

    db = SessionLocal()
    try:
        schema = ensure_content_tag_schema(db)
        if schema.created_tables:
            print(f"[schema] Created tables: {schema.created_tables}")
        if schema.created_indexes:
            print(f"[schema] Created indexes: {schema.created_indexes}")

        if args.rebuild:
            db.execute(delete(AssetContentTag))
            db.commit()
            print("[rebuild] Cleared all existing content tags.")
            from sqlalchemy import select
            from app.models.asset import Asset
            assets = list(db.scalars(select(Asset).where(Asset.is_canonical.is_(True))).all())
        else:
            assets = load_assets_for_content_tagging(db)

        print(f"[run] Assets to tag: {len(assets)}")
        if not assets:
            print("[run] Nothing to do.")
            return 0

        try:
            ensure_content_tag_runtime_available()
        except RuntimeError as exc:
            print(f"[error] {exc}")
            return 1

        outcome = run_content_tagging(
            assets,
            vault_root,
            min_confidence=settings.content_tag_min_confidence,
            max_per_asset=settings.content_tag_max_per_asset,
        )

        written = persist_content_tags(db, outcome.tagged)

        print(f"[done] Tagged: {len(outcome.tagged)}  |  Written rows: {written}  |  Failures: {len(outcome.failures)}")
        for sha256, reason in outcome.failures:
            print(f"  [fail] {sha256[:12]}… — {reason}")

        return 0 if not outcome.failures else 1

    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
