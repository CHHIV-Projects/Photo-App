# Coder Response 12.61.1

## 1. Milestone Title and Date
- Milestone: 12.61.1 Source Profile Model Foundation
- Date: 2026-06-01

## 2. Scope Completed
Completed in this pass:
- added source profile foundation fields to ingestion source model
- implemented additive/idempotent schema evolution for new fields
- backfilled profile_status for existing rows to active and enforced default/non-null
- added parallel read-only admin source profiles endpoint
- added profile status filter and optional username exposure toggle
- added default masked username behavior in profile responses
- preserved existing source-intake and iCloud runtime behavior

## 3. Files Inspected
- backend/app/models/ingestion_source.py
- backend/app/services/ingestion/ingestion_context_schema.py
- backend/app/services/admin/source_intake_service.py
- backend/app/services/admin/__init__.py
- backend/app/schemas/admin.py
- backend/app/api/admin.py
- backend/tests/test_event_admin_api.py

## 4. Files Modified or Added
Modified:
- backend/app/models/ingestion_source.py
- backend/app/services/ingestion/ingestion_context_schema.py
- backend/app/services/admin/source_intake_service.py
- backend/app/services/admin/__init__.py
- backend/app/schemas/admin.py
- backend/app/api/admin.py

Added:
- backend/tests/test_admin_source_profiles_api.py
- docs/operations/source_profile_model_foundation_12_61_1.md
- docs/prompts/Coder response 12.61.1.md

## 5. Data Model Foundation
Added to ingestion source model and schema path:
- profile_status: string, default active, non-null after backfill
- cloud_provider: nullable string
- acquisition_method: nullable string
- managed_staging_path: nullable string

Also ensured account_username is present in idempotent table creation/evolution path for compatibility.

## 6. Idempotent Schema Behavior
Updated ingestion context schema helper to:
- create the new source profile columns when missing
- backfill existing null profile_status rows to active
- enforce profile_status NOT NULL and default active

This keeps rollout additive and safe in existing environments.

## 7. API Additions
Added new endpoint:
- GET /api/admin/source-profiles

Query parameters:
- status: active|inactive|archived|test|deprecated|all (default active)
- include_username: bool (default false)

Response:
- generated_at
- profiles[] with source identity, profile fields, first_seen_at, last_run_at,
  account_username_masked, and optional account_username when include_username=true.

Validation:
- invalid status returns HTTP 400 with detail message.

## 8. Preservation of Existing Behavior
Confirmed unchanged:
- existing /api/admin/source-intake/* routes and schemas
- source intake execution/control behavior
- iCloud acquisition source registration/matching/execution logic
- no source delete/hide behavior introduced

## 9. Validation Performed
Executed tests:
- python -m unittest discover -s tests -p "test_admin_source_profiles_api.py" -q
  - 3 passed
- python -m unittest discover -s tests -p "test_event_admin_api.py" -q
  - 4 passed

Diagnostics:
- no errors on touched backend files and new test file

## 10. Assumptions Summary
- active is the intended default profile_status for existing sources.
- source-profiles is a parallel read-only API for staged adoption and does not replace source-intake in this milestone.
- masked usernames should be default-safe; raw usernames remain explicit opt-in.

## 11. Deviations from Prompt
No intentional behavioral deviations.

Implementation detail worth noting:
- status query parsing is case-insensitive in service logic after normalization.

## 12. Known Limitations
- no write/update endpoint for profile fields yet (read-only surface only).
- no dedicated migration script; schema evolution is handled by existing idempotent helper pathway.
- no frontend wiring to source-profiles endpoint in this milestone.

## 13. Milestone Closeout Checklist
What changed:
- source profile fields + schema default/backfill + read-only source-profiles API + tests.

How to run:
- from backend directory:
  - python -m unittest discover -s tests -p "test_admin_source_profiles_api.py" -q

What passed:
- source profiles API tests: 3/3
- event admin API smoke: 4/4
- diagnostics on touched files: clean
