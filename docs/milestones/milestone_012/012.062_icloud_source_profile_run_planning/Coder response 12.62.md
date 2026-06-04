# Coder Response 12.62

## 1. Milestone Title and Date
- Milestone: 12.62 iCloud Source Profile Run Planning
- Date: 2026-06-01

## 2. Scope Completed
Completed in this milestone:
- full reconnaissance of current iCloud acquisition, source intake handoff, cleanup, and reporting behavior
- documentation of current contracts and runtime behavior
- recommendation of future Ingestion-tab iCloud workflow, option model, cleanup policy, and implementation sequence

Out of scope (intentionally not done):
- no runtime code behavior changes
- no endpoint changes
- no schema/model changes
- no credential/auth flow changes

## 3. Files Inspected
Backend/API/schema/model/service:
- backend/app/api/admin.py
- backend/app/schemas/admin.py
- backend/app/models/icloud_acquisition_run.py
- backend/app/models/source_intake_run.py
- backend/app/models/icloud_staging_cleanup_run.py
- backend/app/services/icloud_acquisition/execution_service.py
- backend/app/services/admin/source_intake_execution_service.py
- backend/app/services/admin/source_intake_service.py
- backend/app/services/admin/icloud_staging_cleanup_execution_service.py
- backend/app/services/ingestion/ingestion_context_service.py
- backend/app/services/ingestion/pipeline_orchestrator.py

Frontend:
- frontend/src/components/IcloudAcquisitionCard.tsx
- frontend/src/components/AdminView.tsx
- frontend/src/components/IngestionView.tsx
- frontend/src/lib/api.ts
- frontend/src/types/ui-api.ts

Prior milestone documentation:
- docs/operations/source_profile_operational_hardening_12_61_5.md
- docs/operations/run_intake_from_ingestion_local_external_12_61_7.md
- docs/operations/ingestion_local_external_final_ergonomics_12_61_9.md
- docs/prompts/Coder response 12.61.9.md

## 4. Current iCloud Acquisition Findings
- Launch UI is Admin iCloud card (not Ingestion tab).
- Launch endpoint is POST /api/admin/icloud-acquisition/run.
- Current request supports:
  - source_label (required)
  - username (required)
  - recent_count (1..500)
  - source_type (default cloud_export)
  - acquisition_mode (standard | list_first_non_repeat)
- Acquisition path is resolved server-side to storage/exports/icloud/<sanitized_label>.
- Run fails if matching source registration does not exist for normalized label + type + normalized source_root_path.
- acquisition_mode list_first_non_repeat runs preflight and may skip actual download when all candidates are already known.
- Reports are persisted to storage/logs/icloud_connector_reports.

## 5. Current Authentication/Session Findings
- App does not collect/store Apple password or 2FA.
- Auth/session readiness is inferred by parsing process output.
- Runtime error codes include AUTH_REQUIRED and SESSION_EXPIRED.
- UI provides operator guidance to run icloudpd auth-only command externally.
- Backend command currently does not explicitly pass --cookie-directory; session location is effectively external icloudpd config/environment behavior.
- No dedicated backend session-health endpoint currently exists.

## 6. Current Staging Findings
- Staging folder is auto-created by acquisition launch path.
- Current acquisition staging root is fixed by sanitized source label under storage/exports/icloud.
- Source Profile effective path logic prefers managed_staging_path for iCloud cloud_export profiles.
- Path convention mismatch risk exists:
  - source profile default managed staging path generation includes provider segment
  - acquisition resolve path currently does not include provider segment
- Staged files remain after intake unless cleanup is run.

## 7. Current Source Intake Handoff Findings
- Handoff is manual today.
- Admin iCloud card offers Prepare Source Intake after completed acquisition.
- Handoff matching logic validates source by normalized label + normalized source_root_path.
- Intake prefill:
  - source id selected from matched profile
  - source_intake_limit inferred from staged file inventory, otherwise recent_count fallback, capped to 500
- Source intake skip-known behavior is keyed to ingestion_source_id + source_relative_path provenance lookup.
- Known/duplicate assets are skipped/handled by existing intake and dedup pipeline behavior.

## 8. Current Cleanup Findings
- Cleanup is a separate admin operation (manual trigger).
- Cleanup blocks if another cleanup run is active.
- Cleanup blocks if source intake is active for same source.
- Cleanup validates source is cloud_export and path is under approved iCloud exports root.
- Candidate deletion requires provenance + vault evidence and no conflicting failed/deferred report evidence.
- dry_run is supported and report is always written.
- Cleanup is conservative and rerunnable.

## 9. Current Report Findings
- Acquisition report path:
  - storage/logs/icloud_connector_reports/icloudpd_acquisition_<timestamp>.json
- Source intake report path:
  - storage/logs/source_intake_reports/source_intake_<timestamp>.json (summarized via service)
- Cleanup report path:
  - storage/logs/icloud_cleanup_reports/icloud_cleanup_<timestamp>_run<id>.json
- There is no shared orchestration run id across acquisition/intake/cleanup.
- Correlation is currently by source identity + path + timestamps + individual run ids.

## 10. Concurrency Findings
- Acquisition has an acquisition-local single-active lock.
- Source intake has an intake-local single-active lock.
- Cleanup has cleanup-local active lock and source-intake-active check for same source.
- No explicit cross-lock preventing:
  - acquisition while source intake active
  - cleanup while acquisition active
- Operational overlap risk exists if workflows are launched independently.

## 11. Recommended Workflow
Recommended v1 Ingestion iCloud workflow is guided steps, not one button:
1. Verify source profile, staging path, and auth/session diagnostic state.
2. Acquire from iCloud.
3. Review acquisition output.
4. Run Source Intake for same source profile.
5. Review intake summary.
6. Offer manual cleanup action.

Reasoning:
- safer failure isolation
- clearer operator intent at each stage
- avoids premature auto-clean behavior

## 12. Recommended Run Options
Acquisition options (v1):
- account username (prefilled)
- recent_count
- optional acquisition_mode advanced toggle

Source intake options (v1):
- Total Limit
- Batch Size

Cleanup options (v1):
- dry_run default true
- explicit manual execute

## 13. Recommended Cleanup Policy
Recommended v1 policy:
- keep cleanup manual (not automatic after intake)
- surface cleanup status/recommendation after intake
- require explicit operator action for deletion pass

## 14. Recommended Implementation Sequence
Refined recommended sequence:
1. 12.62.1 iCloud Session/Staging Status UI in Ingestion
2. 12.62.2 Cross-operation concurrency guardrails
3. 12.62.3 Ingestion-tab Acquire from iCloud
4. 12.62.4 Guided Source Intake handoff in Ingestion
5. 12.62.5 Combined acquisition+intake summary
6. 12.62.6 Ingestion-tab staging cleanup workflow (manual default)
7. 12.62.7 Report correlation polish

## 15. Confirmation of Runtime Safety Boundary
Confirmed:
- no runtime behavior changed in this milestone
- documentation-only outputs were produced

## Assumptions and Open Questions
Assumptions used in planning:
- Ingestion tab should become primary operator path, Admin remains diagnostics fallback.
- External icloudpd auth workflow remains required for v1.

Open questions to resolve before implementation:
- Should acquisition staging root be aligned to managed_staging_path exactly (including provider segment), or should profile creation default be aligned to current acquisition resolver?
- Should list_first_non_repeat be exposed in first Ingestion v1 UI or deferred to advanced settings?
- Should a new orchestration endpoint be introduced early for cross-step correlation, or should UI compose existing APIs first?
- Should cleanup be offered immediately post-intake or only from explicit row action?
