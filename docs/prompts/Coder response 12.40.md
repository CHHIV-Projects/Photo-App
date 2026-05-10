# Coder Response — Milestone 12.40: Video Metadata Trust Handling

## Scope

Stop classifying `.mov` / `.mp4` / `.m4v` files as low-trust merely because image EXIF fields are absent. Use QuickTime/container dates instead, and express the result using the existing `high / low / unknown` trust vocabulary.

---

## Approved Design Decisions (from milestone Q&A)

| Question | Decision |
|---|---|
| Trust vocabulary | Keep `high / low / unknown` — no new `medium` value |
| Still-date fallback for video | Deferred — not implemented in 12.40 |
| Schema changes | None — use existing `asset_metadata_observations` table as-is |
| Low-trust fallback source | Filesystem `modified_timestamp_utc` |

---

## QuickTime Date Field Priority

When extracting a container date for video assets the following fields are tried in order:

**Primary (prefers timezone-aware values):**
1. `QuickTime:CreationDate`
2. `Keys:CreationDate`
3. `com.apple.quicktime.creationdate`

**Secondary (UTC-encoded, no timezone):**
4. `QuickTime:CreateDate`
5. `QuickTime:MediaCreateDate`
6. `QuickTime:TrackCreateDate`

**Fallback:**
7. Filesystem `modified_timestamp_utc` → assigned `capture_time_trust = low`

Timezone-aware values are normalized to naive UTC before storage (columns are `DateTime(timezone=False)` except `captured_at` which is `timezone=True`).

---

## Trust Classification Logic (video-aware early return)

Added to the top of `classify_asset_capture_type()` in `metadata_normalizer.py`:

| Condition | `capture_type` | `capture_time_trust` |
|---|---|---|
| Video AND has valid container date | `digital` | `high` |
| Video AND no container date, has `modified_timestamp_utc` | `digital` | `low` |
| Video AND neither | `unknown` | `unknown` |

This early return fires before the existing scan/image-EXIF branch, preventing MOV/MP4 from falling into low-trust due to absent image EXIF fields.

---

## Files Modified

### Code changes

| File | What changed |
|---|---|
| `backend/app/services/metadata/exif_extractor.py` | Added `VIDEO_EXTENSIONS`, `VIDEO_PRIMARY_DATE_FIELDS`, `VIDEO_SECONDARY_DATE_FIELDS`, `_first_metadata_value()`, `_extract_video_dates()`. Extended `_parse_datetime()` with timezone-aware format handling. Extended `_extract_single_metadata()` to read QuickTime fields for video assets. |
| `backend/app/services/metadata/exif_persistence.py` | Now also persists `gps_latitude` and `gps_longitude` (was silently dropped). |
| `backend/app/services/metadata/metadata_normalizer.py` | Added `VIDEO_EXTENSIONS`, `_is_video_asset()`. Added video-aware early return at top of `classify_asset_capture_type()`. |
| `backend/app/services/metadata/canonicalization_service.py` | Added `VIDEO_EXTENSIONS`, `OBSERVATION_EXTENSIONS`, video date field lists, `_first_metadata_value()`, `_extract_video_dates()`, `_supports_metadata_observation()`. Extended `_parse_datetime()` with timezone-aware handling. Extended `_extract_observation_from_metadata()` and `_extract_dimensions()` for QuickTime fields. Updated all batch/backfill functions to use `_supports_metadata_observation()` (covers images + video). |

### Script changes

| File | What changed |
|---|---|
| `backend/scripts/run_metadata_canonicalization_backfill.py` | Added 8 explicit model registry imports to prevent SQLAlchemy FK resolution errors when run as a standalone script. Updated docstring to mention video coverage. |

### New tests

| File | Tests |
|---|---|
| `backend/tests/test_video_metadata_handling.py` | 4 new unit tests (see below) |

---

## Test Results

### New video tests — 4 / 4 passing

| Test | What it validates |
|---|---|
| `test_mov_extraction_uses_quicktime_creation_date` | QuickTime date extracted over image EXIF fields |
| `test_video_normalization_marks_container_date_as_high_trust` | iPhone MOV with container date → `high` / `digital` |
| `test_video_normalization_uses_filesystem_fallback_as_low_trust` | MP4 without any container dates → `low` / `digital` |
| `test_video_observation_extraction_uses_quicktime_fields` | Observation extraction picks up QuickTime make/model/dimensions |

### Image regression — 7 / 7 passing

`backend/tests/test_metadata_canonicalization_service.py` — no regressions.

---

## Backfill Results

Targeted video-only pass run after code changes (all existing `.mov` / `.mp4` / `.m4v` assets):

| Metric | Count |
|---|---|
| Video assets found | 74 |
| ExifTool extraction succeeded | 71 |
| ExifTool extraction failed (no source file) | 3 |
| EXIF rows updated in DB | 71 |
| Normalization rows updated | 74 |
| `capture_time_trust = high` | 71 |
| `capture_time_trust = low` | 3 |
| `capture_time_trust = unknown` | 0 |

The 3 low-trust assets (`IMG_1003.MOV`, `IMG_1004.MP4`, `IMG_1234.MOV`) are test/placeholder files with no source file on disk and no container date — filesystem timestamp used as intended fallback.

### Representative validated assets (pre-backfill targeted pass)

| Filename | `exif_datetime_original` | `capture_time_trust` | `camera_make` | `camera_model` |
|---|---|---|---|---|
| `IMG_5637_HEVC.MOV` | 2026-05-08 19:21:06 | high | Apple | iPhone 14 Plus |
| `IMG_5638.MOV` | 2026-05-08 19:21:14 | high | Apple | iPhone 14 Plus |
| `2012-08-08_18-17-41_593.mp4` | 2012-08-09 00:18:17 | high | — | — |

---

## How to Run

**Re-run video backfill (if needed):**
```powershell
# From backend/
& "../../.venv/Scripts/python.exe" -c "
import sys; sys.path.insert(0,'.')
import app.models.asset, app.models.duplicate_group, app.models.event
import app.models.ingestion_run, app.models.ingestion_source
import app.models.place, app.models.provenance
from sqlalchemy import func, select
from app.db.session import SessionLocal
from app.models.asset import Asset
from app.services.metadata.exif_extractor import extract_exif_for_assets, VIDEO_EXTENSIONS
from app.services.metadata.exif_persistence import persist_exif_updates
from app.services.metadata.metadata_normalizer import normalize_assets, persist_normalized_metadata
db = SessionLocal()
assets = list(db.scalars(select(Asset).where(func.lower(Asset.extension).in_(VIDEO_EXTENSIONS))).all())
extraction = extract_exif_for_assets(assets)
persist_exif_updates(db, extraction.extracted)
db.expire_all()
refreshed = list(db.scalars(select(Asset).where(func.lower(Asset.extension).in_(VIDEO_EXTENSIONS))).all())
norm = normalize_assets(refreshed)
persist_normalized_metadata(db, norm.updated_records)
print('done')
db.close()
"
```

**Run tests:**
```powershell
# From backend/
& "../../.venv/Scripts/python.exe" -m pytest tests/test_video_metadata_handling.py tests/test_metadata_canonicalization_service.py -v
```

---

## Deferrals

| Item | Reason deferred |
|---|---|
| Still-date fallback (use `exif_datetime_original` from paired JPEG when video has no container date) | Complex pairing logic; deferred to a future milestone |
| Trust vocabulary expansion (e.g., `medium`) | Not needed for current use cases; keep `high / low / unknown` |
| Legacy video formats (`.avi`, `.wmv`, `.3gp`) | Not in current library; add to `VIDEO_EXTENSIONS` when needed |
| `recompute_canonical_metadata_for_assets()` video support | Currently image-only; video canonicalization path is a separate future task |
