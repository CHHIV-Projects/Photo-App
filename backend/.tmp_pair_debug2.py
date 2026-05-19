from sqlalchemy import select
from app.db.session import SessionLocal
from app.models.asset import Asset

s = SessionLocal()
rows = s.execute(
    select(
        Asset.original_filename,
        Asset.captured_at,
        Asset.capture_time_trust,
        Asset.exif_datetime_original,
        Asset.exif_create_date,
        Asset.modified_timestamp_utc,
        Asset.source_type,
    ).where(Asset.original_filename.in_(["IMG_5653.HEIC", "IMG_5653_HEVC.MOV"]))
).all()
for r in rows:
    print(r)
s.close()
