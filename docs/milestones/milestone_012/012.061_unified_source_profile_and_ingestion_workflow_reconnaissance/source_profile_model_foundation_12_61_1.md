# Source Profile Model Foundation 12.61.1

## 1. Purpose
Milestone 12.61.1 introduces additive Source Profile foundation fields and a parallel read-only API surface.

This milestone is compatibility-first:
- existing Source Intake routes remain unchanged
- existing iCloud acquisition behavior remains unchanged
- no source deletion or hiding behavior was introduced

## 2. Scope Implemented
Implemented in this milestone:
- added additive profile fields to ingestion source model:
  - profile_status (default active)
  - cloud_provider
  - acquisition_method
  - managed_staging_path
- extended idempotent ingestion context schema helper to:
  - create new columns when missing
  - backfill NULL profile_status to active
  - enforce profile_status NOT NULL + default active
- added parallel read-only endpoint:
  - GET /api/admin/source-profiles
  - supports query params:
    - status (default active; supports active/inactive/archived/test/deprecated/all)
    - include_username (default false)
- added account username masking in source profile responses by default
- kept existing source-intake visibility routes and payloads intact

## 3. Data Model Changes
Ingestion source profile fields are now part of the ORM model and schema evolution path:
- profile_status: lifecycle status for profile-level routing and UI filtering
- cloud_provider: provider taxonomy placeholder (for example icloud)
- acquisition_method: acquisition strategy descriptor (for example icloudpd)
- managed_staging_path: durable managed staging location pointer

These are additive only; existing rows and workflows are preserved.

## 4. API Contract
New endpoint:
- GET /api/admin/source-profiles

Response model:
- generated_at
- profiles[] where each profile includes:
  - source identity and path fields
  - profile fields listed above
  - account_username_masked (always returned when username exists)
  - account_username (only when include_username=true)
  - first_seen_at
  - last_run_at

Invalid status values return HTTP 400 with a validation detail message.

## 5. Compatibility and Safety
Confirmed unchanged:
- no Source Intake execution flow changes
- no iCloud acquisition matching/execution changes
- no credential write-path additions
- no source mutation beyond additive schema backfill/defaulting

## 6. Validation Performed
Executed:
- python -m unittest discover -s tests -p "test_admin_source_profiles_api.py" -q
  - result: 3 passed
- python -m unittest discover -s tests -p "test_event_admin_api.py" -q
  - result: 4 passed
- diagnostics on all touched files
  - result: no errors

## 7. Assumptions
- profile_status default active is the desired baseline for all existing sources.
- source profile endpoint is intentionally parallel to source-intake endpoints and does not replace them in this milestone.
- masked username is the default safe response behavior; raw username remains opt-in for admin workflows.

## 8. Files Modified
Backend:
- backend/app/models/ingestion_source.py
- backend/app/services/ingestion/ingestion_context_schema.py
- backend/app/schemas/admin.py
- backend/app/services/admin/source_intake_service.py
- backend/app/services/admin/__init__.py
- backend/app/api/admin.py
- backend/tests/test_admin_source_profiles_api.py

Documentation:
- docs/operations/source_profile_model_foundation_12_61_1.md
