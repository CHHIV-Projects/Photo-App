# Run Options Visibility and Source Profile Edit Clarification 12.61.8.1

## 1. Purpose
Milestone 12.61.8.1 improves run-option clarity in the Ingestion tab and clarifies Source Profile lifecycle management wording without changing ingestion execution behavior.

## 2. Total Limit Behavior
- Total Limit is visible in run confirmation via a summary line even when Advanced is collapsed.
- Total Limit input remains optional in Advanced options.
- Blank Total Limit means unlimited.
- Total Limit accepts only positive integers when provided.
- Invalid Total Limit is blocked client-side before run start.

## 3. Batch Size Behavior
- Batch Size is visible in run confirmation via the same summary line.
- Batch Size input remains in Advanced options.
- Default Batch Size is 500.
- Batch Size accepts only positive integers.
- Invalid Batch Size is blocked client-side before run start.

## 4. Per-Run Option Rule
- Total Limit and Batch Size are per-run controls only.
- The confirmation dialog explicitly states these options are not saved to Source Profile metadata.
- Opening a new run confirmation resets defaults (Total Limit blank, Batch Size 500).

## 5. Default Values
- Total Limit default: blank/null (interpreted as unlimited).
- Batch Size default: 500.
- Collapsed summary default text: Options: Total Limit = unlimited, Batch Size = 500.

## 6. Validation Behavior
- Total Limit validation: blank or positive integer.
- Batch Size validation: positive integer.
- If invalid, run start is blocked and Advanced options are shown for correction.
- Field-level validation messages are shown inline.

## 7. Source Profile Status/Edit Clarification
- Row action label changed from Edit to Manage.
- Edit drawer title changed to lifecycle/status-first wording: Manage Source Profile Status and Metadata.
- Existing behavior preserved:
  - profile_status remains editable.
  - source_type remains locked after creation.
  - source_root_path remains locked after creation.

## 8. Provenance Non-Retroactive Rule
- Main Ingestion page includes short note: Source Profile status changes are non-destructive and do not rewrite prior provenance.
- Manage drawer includes full non-retroactive warning:
  - profile changes do not rewrite prior provenance records, source paths, intake reports, or asset history.
  - recommended correction pattern is archive/deprecate/test and create a corrected profile.

## 9. Safety Boundaries
Confirmed unchanged:
- Source Intake execution semantics
- backend payload contract fields
- Drop Zone behavior
- Vault behavior
- provenance behavior
- unsupported run options
- source profile identity locks (type/path)

## 10. Validation Performed
Frontend:
- npm run build passed in frontend workspace.

Backend regression slice:
- python -m unittest discover -s tests -p "test_admin_source_profiles_api.py" -q passed.
- python -m unittest discover -s tests -p "test_event_admin_api.py" -q passed.

## 11. Limitations
- Run option summary reflects current input values and does not persist across separate run dialogs.
- Source profile historical reporting remains bounded by existing backend report-history limits.
- This milestone does not introduce provenance repair workflows.

## 12. Recommended Next Milestone
Recommended next milestone:
- 12.61.9 Ingestion Tab Local/External Final Ergonomics

Potential scope:
- table density and spacing polish
- counter wording/readability tuning
- source status copy refinements
- report summary scanability improvements
