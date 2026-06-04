# Source Archive / Inactive Lifecycle and Filtering 12.61.2

## 1. Purpose
Milestone 12.61.2 makes source profile lifecycle status operational without deleting sources or mutating provenance.

This milestone is lifecycle metadata only:
- no source deletion
- no provenance rewrite
- no source intake execution changes
- no iCloud acquisition execution changes

## 2. Scope Implemented
Implemented in this milestone:
- added strict single-field source profile lifecycle update endpoint:
  - PATCH /api/admin/source-profiles/{source_id}
  - payload allows profile_status only
- validated profile_status for:
  - active
  - inactive
  - archived
  - test
  - deprecated
- preserved existing read/list status filtering via:
  - GET /api/admin/source-profiles?status=...
- kept default profile list behavior as status=active
- added optional, low-risk reference count metadata to source profile responses:
  - provenance_count
  - ingestion_runs_count
  - source_intake_runs_count
  - icloud_acquisition_runs_count

## 3. API Behavior
### 3.1 List Source Profiles
- endpoint: GET /api/admin/source-profiles
- status filter supports:
  - active
  - inactive
  - archived
  - test
  - deprecated
  - all
- default remains status=active

### 3.2 Update Source Profile Status
- endpoint: PATCH /api/admin/source-profiles/{source_id}
- request body:
  - profile_status: string
- behavior:
  - accepts any valid status to any other valid status
  - updates only profile_status
  - returns updated SourceProfileSummary
- validation:
  - invalid status returns 400
  - missing source returns 404

## 4. Reference Count Notes
Included now because low-risk and cheap enough for admin usage:
- provenance_count and ingestion/source-intake run counts are grouped by ingestion_source_id
- iCloud acquisition runs currently do not store ingestion_source_id; counts are matched by source_label/source_type/source_root_path

Reference counts are additive metadata and do not block status updates.

## 5. Explicit Non-Changes
Confirmed unchanged:
- existing /api/admin/source-intake/* routes and behavior
- existing Source Intake Known Sources behavior
- existing iCloud acquisition matching/execution
- staging cleanup behavior
- provenance rows and references

## 6. Validation Performed
Executed:
- python -m unittest discover -s tests -p "test_admin_source_profiles_api.py" -q
  - result: 7 passed
- python -m unittest discover -s tests -p "test_event_admin_api.py" -q
  - result: 4 passed
- diagnostics on touched files
  - result: no errors

## 7. Assumptions
- lifecycle status is an admin metadata label and remains non-destructive
- status transition restrictions are deferred; any valid-to-valid transition is allowed in 12.61.2
- source-profiles filtering remains isolated from source-intake endpoints in this milestone

## 8. Files Modified
Backend:
- backend/app/schemas/admin.py
- backend/app/services/admin/source_intake_service.py
- backend/app/services/admin/__init__.py
- backend/app/api/admin.py
- backend/tests/test_admin_source_profiles_api.py

Documentation:
- docs/operations/source_archive_inactive_lifecycle_and_filtering_12_61_2.md
