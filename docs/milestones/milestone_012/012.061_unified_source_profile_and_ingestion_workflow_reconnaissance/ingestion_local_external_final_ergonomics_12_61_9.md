# Ingestion Tab Local/External Final Ergonomics 12.61.9

## 1. Purpose
Milestone 12.61.9 finalizes local/external Ingestion tab ergonomics by making normal Manage status-focused and simplifying Run Intake confirmation settings visibility.

## 2. Manage Drawer Status-Only Behavior
- Row action remains: Manage.
- Edit drawer title is now: Manage Source Profile Status.
- In normal edit mode, Profile Status is the only editable field.
- Allowed status values remain:
  - active
  - inactive
  - archived
  - test
  - deprecated

## 3. Read-Only Source Identity Behavior
In normal edit mode, the following fields are shown read-only and styled as locked identity values:
- Source Label
- Source Type
- Source Root Path
- Cloud Provider (when applicable)
- Acquisition Method (when applicable)
- Account Username (when applicable)
- Managed Staging Path (when applicable)

Create mode remains unchanged and still allows entering source identity/metadata required for profile creation.

## 4. Source Correction Pattern
Manage drawer now includes explicit guidance:
- Source identity is historical after creation.
- If profile identity is wrong, archive/deprecate/test the profile and create a corrected profile.

The non-retroactive warning remains visible:
- profile changes do not rewrite prior provenance records, source paths, intake reports, or asset history.

## 5. Total Limit Behavior
- Total Limit is shown directly in Run Intake confirmation.
- It remains optional.
- Blank means unlimited.
- If provided, it must be a positive integer.

## 6. Batch Size Behavior
- Batch Size is shown directly in Run Intake confirmation.
- Default remains 500.
- It must be a positive integer.

## 7. Per-Run Option Rule
- Total Limit and Batch Size remain per-run controls only.
- They are not saved on Source Profile metadata.
- Defaults continue to reset when opening a new run confirmation:
  - Total Limit blank/null
  - Batch Size 500

## 8. Safety Boundaries
Confirmed unchanged:
- Source Intake execution behavior
- run payload contract
- Source Profile identity lock constraints (type/root path)
- provenance behavior
- unsupported run options
- iCloud/cloud orchestration behavior

## 9. Validation Performed
Frontend:
- npm run build passed in frontend workspace.

Backend regression slice:
- python -m unittest discover -s tests -p "test_admin_source_profiles_api.py" -q passed.
- python -m unittest discover -s tests -p "test_event_admin_api.py" -q passed.

## 10. Limitations
- Normal Ingestion Manage UI intentionally does not expose broad metadata correction workflows.
- Advanced metadata repair remains out of scope for this milestone.
- Report history visibility is still bounded by existing backend recent-report limits.

## 11. Recommended Next Milestone
Recommended next milestone:
- 12.62 iCloud Source Profile Run Planning

Candidate scope:
- plan Ingestion-tab iCloud acquisition + intake orchestration
- auth/session expectations
- managed staging validation
- cleanup timing
- combined acquisition/intake summary
- no implementation yet
