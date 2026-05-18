# Coder Response - Milestone 12.48.1

Date: 2026-05-18
Milestone: 12.48.1 - iCloud Non-Repeat Acquisition Implementation

## 1. Milestone Title and Date

- Milestone: 12.48.1 - iCloud Non-Repeat Acquisition Implementation
- Date: 2026-05-18

## 2. Scope Completed

Implemented the first safe backend non-repeat foundation with explicit mode gating and conservative preflight known-state logic.

Delivered:
- explicit acquisition_mode support:
  - standard (default)
  - list_first_non_repeat
- safe preflight command support for list-first mode
- conservative candidate parser for preflight output
- known-state evaluator service using provenance + asset + vault evidence
- conservative caught-up status logic
- short-circuit skip-download when all preflight candidates are already known and none are unknown identity
- report-first non-repeat metrics in JSON report
- minimal API/type compatibility updates
- focused unit tests

## 3. Files Inspected

- backend/app/services/icloud_acquisition/execution_service.py
- backend/app/services/icloud_acquisition/schema.py
- backend/app/models/icloud_acquisition_run.py
- backend/app/api/admin.py
- backend/app/schemas/admin.py
- backend/app/services/persistence/asset_repository.py
- backend/app/services/duplicates/lineage.py
- backend/app/models/provenance.py
- frontend/src/types/ui-api.ts
- backend/tests/test_icloud_acquisition_service.py
- docs/operations/icloud_non_repeat_acquisition_strategy.md

## 4. Files Modified or Added

Modified:
- backend/app/api/admin.py
- backend/app/models/icloud_acquisition_run.py
- backend/app/schemas/admin.py
- backend/app/services/icloud_acquisition/execution_service.py
- backend/app/services/icloud_acquisition/schema.py
- backend/tests/test_icloud_acquisition_service.py
- docs/operations/icloud_non_repeat_acquisition_strategy.md
- frontend/src/types/ui-api.ts

Added:
- backend/app/services/icloud_acquisition/known_state_service.py
- backend/tests/test_icloud_known_state_service.py
- docs/prompts/Coder response 12.48.1.md

## 5. Acquisition Mode Implementation Summary

Implemented explicit mode handling with default backward compatibility:
- standard: current behavior unchanged
- list_first_non_repeat: preflight + known-state path enabled

Mode normalization/validation rejects unsupported values.

## 6. Preflight Command Behavior

Added preflight command builder for list-first mode:
- includes:
  - --recent <N>
  - --dry-run
  - --only-print-filenames
- excludes:
  - --until-found as primary strategy dependency

Preflight runs before download in list_first_non_repeat mode.
Preflight failures are surfaced with clear run/report error state.

## 7. Candidate Parser Behavior

Added conservative parser:
- preserves raw_line for every candidate considered
- normalizes path separators and simple prefix noise
- requires confidence (path/filename extension) for mapped identity
- classifies unconfident lines as unknown_identity
- keeps unknown_identity samples in report

Unknown identities never contribute to likely_caught_up.

## 8. Known-State Evaluator Behavior

Added known-state evaluator service that compares candidates against durable state:
- staged_known: file exists under staging root
- ingested_known: provenance exists for ingestion_source_id + source_relative_path
- vault_verified_known: ingested_known + linked asset + vault file exists
- already_known: true only when ingested_known or vault_verified_known

staged_known alone is not treated as durable already_known.

## 9. Caught-Up Status Logic

Implemented conservative status derivation:
- likely_caught_up
- partial_window_only
- unknown

likely_caught_up requires all of:
- preflight success
- candidate_count > 0
- unknown_identity_count == 0
- all candidates already_known
- download skipped due to all-known short-circuit

## 10. Short-Circuit Behavior

If list-first preflight finds all candidates already known with no unknown identities:
- download subprocess is skipped
- run completes successfully
- report records download_skipped_due_to_all_known=true

No Source Intake or cleanup is triggered automatically.

## 11. Run/Report Field Changes

JSON report fields added:
- acquisition_mode
- preflight_enabled
- preflight_ok
- preflight_stdout_tail
- preflight_stderr_tail
- preflight_candidate_count
- already_known_count
- staged_known_count
- ingested_known_count
- vault_verified_known_count
- unknown_identity_count
- caught_up_status
- download_skipped_due_to_all_known
- known_state_summary
- candidate_samples
- unknown_identity_samples

Minimal run model durability update:
- added acquisition_mode column to icloud_acquisition_runs
- schema ensure logic adds column if missing

## 12. API/Frontend Type Changes

Backend API schema:
- IcloudAcquisitionRunRequest now includes acquisition_mode with default standard
- IcloudAcquisitionRunStatus now includes acquisition_mode

Frontend type updates:
- updated IcloudAcquisitionRunRequest and IcloudAcquisitionRunStatus in frontend/src/types/ui-api.ts

No Admin card UX redesign was implemented.

## 13. Tests Added or Validation Performed

Added/updated unit tests:
- backend/tests/test_icloud_acquisition_service.py
  - preflight command flags test
  - acquisition_mode normalization test
- backend/tests/test_icloud_known_state_service.py
  - parser unknown identity behavior
  - caught-up status derivation
  - staged-only known-state behavior
  - vault-verified known-state behavior

Executed test command:
- python -m unittest backend.tests.test_icloud_acquisition_service backend.tests.test_icloud_known_state_service

Result:
- 13 tests, all passing

## 14. Commands Run

- .tools/icloudpd/Scripts/icloudpd.exe --version
- .tools/icloudpd/Scripts/icloudpd.exe --help
- git status --short
- python -m unittest backend.tests.test_icloud_acquisition_service backend.tests.test_icloud_known_state_service

## 15. Safety Confirmation

Confirmed:
- no iCloud delete behavior added
- no Vault delete behavior added
- no automatic Source Intake added
- no automatic cleanup added
- no credential/session storage added
- no real iCloud preflight/download executed in this milestone
- no destructive DB operations executed

## 16. Deviations From Prompt

None material.

One intentional scope choice aligned with your answers:
- detailed non-repeat metrics were implemented report-first (JSON), with only minimal DB expansion (acquisition_mode).

## 17. Known Limitations

- Real repeat-run end-to-end validation was not executed in 12.48.1.
- Candidate parser is intentionally conservative and may classify borderline lines as unknown_identity.
- caught_up_status remains conservative when evidence is incomplete.

## 18. Recommended Next Milestone

Recommended next milestone:
- 12.48.2 - iCloud Non-Repeat Acquisition Repeat-Run Validation

Suggested sequence:
- acquire -> repeat without cleanup -> Source Intake -> cleanup -> repeat after cleanup

Use test source and small window (recent_count <= 25), no production-scale ingestion.

## 19. Runtime Validation Addendum

Performed narrow runtime validation after the implementation pass.

Commands/run results:
- Attempted standard dev launcher: scripts/runtime/start_photo_organizer_dev.ps1 -NoReload
- Result: blocked by existing ghost listener on port 8001 before backend launch could proceed.
- Ran scripts/runtime/stop_photo_organizer.ps1 to clear the dev stack.
- Started Docker dev services successfully.
- Started backend successfully on a temporary validation port (8010) with APP_RUNTIME_PROFILE=development.
- Started frontend successfully with NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8010.
- Opened the app in the browser and confirmed the Admin area and iCloud Acquisition card rendered.
- Verified live backend health and admin acquisition status endpoints responded successfully.
- Verified the icloud_acquisition_runs table includes acquisition_mode and that the current status response reports acquisition_mode=standard.

Validation notes:
- No real iCloud preflight/download was run.
- No Source Intake or cleanup was run during this runtime pass.
- Backend terminal output showed only normal 200-series requests during page interaction; no backend errors were observed.
- The main limitation was the pre-existing ghost listener on 8001, which prevented a clean validation of the stock launcher path on its default backend port.
