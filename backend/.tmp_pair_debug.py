from sqlalchemy import select, or_
from app.db.session import SessionLocal
from app.models.asset import Asset
from app.models.provenance import Provenance
from app.models.live_photo_pair import LivePhotoPair

s = SessionLocal()
rows = s.execute(
    select(
        Asset.sha256,
        Asset.original_filename,
        Asset.extension,
        Asset.captured_at,
        Asset.capture_time_trust,
        Asset.visibility_status,
        Provenance.ingestion_source_id,
        Provenance.source_relative_path,
        Provenance.source_path,
    )
    .join(Provenance, Provenance.asset_sha256 == Asset.sha256)
    .where(Asset.original_filename.in_(["IMG_5653.HEIC", "IMG_5653_HEVC.MOV"]))
).all()
print("ASSET_ROWS", len(rows))
for row in rows:
    print(row)

sha_list = [row[0] for row in rows]
pair_rows = s.execute(
    select(
        LivePhotoPair.id,
        LivePhotoPair.still_asset_sha256,
        LivePhotoPair.motion_asset_sha256,
        LivePhotoPair.ingestion_source_id,
        LivePhotoPair.source_relative_dir,
        LivePhotoPair.source_basename,
    ).where(
        or_(
            LivePhotoPair.still_asset_sha256.in_(sha_list),
            LivePhotoPair.motion_asset_sha256.in_(sha_list),
        )
    )
).all()
print("PAIR_ROWS", len(pair_rows))
for row in pair_rows:
    print(row)

s.close()
