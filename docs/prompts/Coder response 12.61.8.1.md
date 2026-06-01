# Coder Response 12.61.8.1

## 1. Milestone Title and Date
- Milestone: 12.61.8.1 Run Options Visibility and Source Profile Edit Clarification
- Date: 2026-06-01

## 2. Scope Completed
Completed in this pass:
- added always-visible run option summary line in Run Intake confirmation
- kept Advanced options collapsed by default
- added run option helper text for Total Limit and Batch Size
- added per-run-only clarification text
- added client-side inline validation for Total Limit and Batch Size
- renamed row action button from Edit to Manage
- updated edit drawer wording to lifecycle/status-first framing
- added provenance non-retroactive notes in both main page and Manage drawer

## 3. Files Inspected
- frontend/src/components/IngestionView.tsx
- frontend/src/components/ingestion-view.module.css
- docs/prompts/14_milestone_12.61.8.1_run_options_visiblity_source_profile_edit_clarification.md
- docs/operations/run_intake_from_ingestion_local_external_12_61_7.md
- docs/operations/ingestion_run_status_report_polish_12_61_8.md

## 4. Files Modified or Added
Modified:
- frontend/src/components/IngestionView.tsx
- frontend/src/components/ingestion-view.module.css

Added:
- docs/operations/run_options_visibility_source_profile_edit_clarification_12_61_8_1.md
- docs/prompts/Coder response 12.61.8.1.md

## 5. Run Option Visibility Behavior
Implemented:
- run confirmation now shows:
  - Run Intake Options
  - Options: Total Limit = <value/unlimited>, Batch Size = <value>
- summary is visible even when Advanced remains collapsed
- Advanced remains collapsed by default

## 6. Total Limit Behavior
Implemented:
- default remains blank/null (interpreted as unlimited)
- Total Limit is shown in the visible summary line
- Total Limit field remains in Advanced options
- helper text explains eligible unknown selection behavior
- validation enforces blank or positive integer
- invalid values block run start

## 7. Batch Size Behavior
Implemented:
- default remains 500
- Batch Size is shown in the visible summary line
- Batch Size field remains in Advanced options
- helper text explains staged/processed per batch behavior
- validation enforces positive integer
- invalid values block run start

## 8. Source Profile Status/Edit Clarification
Implemented:
- row action label changed to Manage
- edit drawer title changed to Manage Source Profile Status and Metadata
- subtitle updated to lifecycle/status-first wording
- preserved existing lock behavior:
  - profile_status editable
  - source_type locked after creation
  - source_root_path locked after creation

## 9. Provenance Non-Retroactive Clarification
Implemented:
- short page-level note added in Ingestion notes section
- full non-retroactive warning added in Manage drawer for edit mode
- correction guidance included: archive/deprecate/test and create corrected profile

## 10. Safety Confirmation
Confirmed no changes to:
- Source Intake execution behavior
- backend run payload contract
- Source Profile persistence rules for run options
- unsupported run options
- source identity lock constraints
- provenance rewrite behavior

## 11. Validation Performed
Frontend:
- npm run build passed.

Backend regression slice:
- python -m unittest discover -s tests -p "test_admin_source_profiles_api.py" -q passed.
- python -m unittest discover -s tests -p "test_event_admin_api.py" -q passed.

## 12. Deviations from Prompt
- No deviations.

## 13. Known Limitations
- Run-option summary reflects current dialog inputs and resets on next run dialog open.
- Historical source run visibility still depends on existing capped recent-report backend responses.

## 14. Recommended Next Milestone
Recommended:
- 12.61.9 Ingestion Tab Local/External Final Ergonomics

Candidate focus:
- table density and action spacing refinements
- run/report counter wording tuning
- additional readability polish from live operator feedback
