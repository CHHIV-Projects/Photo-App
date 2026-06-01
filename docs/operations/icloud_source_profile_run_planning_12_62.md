# iCloud Source Profile Run Planning 12.62

## 1. Purpose
Milestone 12.62 documents current iCloud behavior and defines a safe v1 design for future Ingestion-tab iCloud runs.

This milestone is reconnaissance only:
- no runtime behavior changes
- no auth/credential model changes
- no acquisition/intake/cleanup execution changes
- no schema contract changes

## 2. Current iCloud Acquisition Flow
Current launch path:
- UI: Admin page card in frontend/src/components/IcloudAcquisitionCard.tsx
- API helper: runIcloudAcquisition(...) in frontend/src/lib/api.ts
- Endpoint: POST /api/admin/icloud-acquisition/run in backend/app/api/admin.py

Current payload (backend/app/schemas/admin.py):
- source_label: required
- username: required
- recent_count: optional default 25, min 1, max 500
- source_type: optional default cloud_export
- acquisition_mode: optional standard | list_first_non_repeat

Current backend launch behavior (backend/app/services/icloud_acquisition/execution_service.py):
- Validates single active acquisition run (running/stop_requested lock)
- Normalizes source label and resolves staging path as storage/exports/icloud/<sanitized_label>
- Creates staging folder automatically (mkdir parents=True)
- Requires an existing ingestion source registration matching:
  - normalized source label
  - source type
  - normalized source_root_path equal to resolved staging path
- Fails with SOURCE_NOT_REGISTERED if no exact match
- Resolves icloudpd executable and version, enforces minimum supported version
- Runs icloudpd in background thread

Current non-repeat behavior:
- acquisition_mode=list_first_non_repeat runs a preflight command:
  - icloudpd --dry-run --only-print-filenames
- Preflight candidates are compared against known state (provenance/asset/vault evidence)
- If all candidates are already known and no unknown identity remains, download is skipped and run completes

Current limits:
- only recent_count is exposed for acquisition
- no date range, album filter, or explicit byte/file-type selector in current API contract

Current error reporting:
- launch errors return 400 with detail + error_code + current snapshot
- active-run conflict returns 409
- runtime errors classify to codes such as AUTH_REQUIRED, SESSION_EXPIRED, NETWORK_OR_UPSTREAM_ERROR, TIMEOUT, PROCESS_FAILED

Current acquisition report writing:
- report directory: storage/logs/icloud_connector_reports
- file pattern: icloudpd_acquisition_<timestamp>.json
- includes command metadata, status/counters, inventory snapshots, preflight known-state summary, tails, and recommended source intake command

## 3. Current icloudpd Authentication/Session Behavior
What is currently true:
- Photo Organizer does not collect password or 2FA in UI
- Photo Organizer does not implement interactive auth prompts
- Backend does not persist iCloud cookies/tokens in database
- Authentication/session failures are detected by process output classification (AUTH_REQUIRED / SESSION_EXPIRED)

Session validity checks:
- No dedicated session health endpoint
- Session readiness is inferred from preflight/download output and failure classification

Where session data lives:
- Managed by icloudpd outside app runtime
- UI guidance points operators to external auth command with cookie directory .tools/icloud_session
- Backend run command does not explicitly pass --cookie-directory today (depends on icloudpd environment/defaults)

What Ingestion tab should show when auth is not ready (recommended):
- explicit external-auth-required state
- no password/2FA fields
- operator command guidance for icloudpd auth-only flow
- last auth-related error code/message

## 4. Current iCloud Staging Behavior
Current destination behavior:
- acquisition downloads to storage/exports/icloud/<sanitized_label>
- path is derived server-side from source label, not user-specified per run
- staging folder is auto-created before run

Relationship to Source Profile managed_staging_path:
- Source Profile effective-path logic prefers managed_staging_path for iCloud cloud_export profiles
- acquisition execution currently derives path from source_label, not directly from managed_staging_path
- run launch enforces matching registered source by normalized label + type + derived staging path

Important divergence risk observed:
- source_intake_service default managed_staging_path generation uses provider segment (storage/exports/icloud/<provider>/<slug>)
- acquisition service resolve_staging_root currently uses storage/exports/icloud/<slug>
- this can create identity/path mismatch if profiles are created with provider-segment path convention

Multiple profile separation:
- separation is by sanitized source label path segment
- collisions are possible if labels sanitize to same slug

When staged files already exist:
- icloudpd may skip already-existing files
- downloaded_count is computed by filesystem delta before/after run
- file_inventory_count reflects total staged files after run

After source intake:
- staged files are not auto-deleted
- cleanup is separate manual workflow

## 5. Current iCloud Acquisition Status/Report Behavior
Status endpoint and shape:
- GET /api/admin/icloud-acquisition/status
- status includes run lifecycle, counters, timing, executable/version, tails, report path, error codes, and file inventory count

Single-active behavior:
- acquisition allows only one active run at a time (acquisition-local lock)

Stop behavior:
- POST /api/admin/icloud-acquisition/stop sets stop_requested and terminates subprocess
- status transitions to stop_requested, then stopped when process exits

Polling behavior:
- IcloudAcquisitionCard polls every 3 seconds while status is running or stop_requested

Report fields (selected):
- status, source_label/source_type/source_registration_status
- staging_path, recent_count, command_sanitized
- downloaded/skipped/failed counts
- initial/final inventory snapshots
- preflight/known-state fields for non-repeat mode
- error_code/error_message

## 6. Current Source Intake Handoff Behavior
Current handoff is manual and operator-driven:
- After completed acquisition in Admin card, operator clicks Prepare Source Intake
- AdminView reloads source registry and matches source by normalized label + normalized source_root_path
- If matched, form pre-populates ingestion_source_id and limit hint

Current prefill logic in AdminView:
- source_intake_limit is derived from fileInventoryCount if available, else recentCount
- value is capped to 500
- ingest_batch_size preserved (default fallback 500)

Current source identity linkage:
- acquisition does not auto-create/update ingestion source
- acquisition requires existing registration before run
- source intake reuses ingestion_source_id

Current skip-known semantics in pipeline:
- source intake skip-known checks provenance by ingestion_source_id + source_relative_path
- known files are skipped before staging
- remaining files proceed through dedup/persistence pipeline
- duplicate/known assets are handled without deleting source files

## 7. Proposed Future Ingestion-Tab iCloud Workflow
Recommended v1 workflow model: guided multi-step, not one-click orchestration.

Proposed operator flow:
1. Select active iCloud Source Profile in Ingestion tab.
2. Show session/auth readiness panel (diagnostic state only).
3. Verify managed staging path exists and is under approved exports root.
4. Run iCloud acquisition step.
5. Review acquisition summary and staged inventory.
6. Run Source Intake step against same source profile.
7. Review intake summary and source completeness.
8. Offer cleanup step (manual explicit action).

Why guided steps first:
- preserves failure boundaries (auth vs download vs intake vs cleanup)
- reduces operator confusion when partial outcomes occur
- avoids unsafe auto-clean when intake/deferred/failure evidence is mixed

## 8. Recommended v1 UI Model
Recommended placement:
- Keep iCloud operation controls in Ingestion tab source-profile row/details for cloud_export+icloud profiles
- Keep Admin tools as diagnostics/advanced fallback

Recommended v1 control labels:
- Step 1: Acquire from iCloud
- Step 2: Run Source Intake
- Step 3: Cleanup Staging (optional/manual)

Recommended status cards in Ingestion:
- iCloud session/auth note
- staging path verification result
- current/last acquisition status
- current/last source intake status
- optional cleanup status snapshot

## 9. Recommended Run Options
Current acquisition options available now:
- source label
- username
- recent_count
- acquisition_mode (standard, list_first_non_repeat)

Not currently available in app contract:
- date ranges
- album selection
- live-photo-specific behavior controls
- dedicated dry-run-only run endpoint

Recommended v1 options to expose in Ingestion:
- Acquisition:
  - account username (prefill from profile account_username)
  - recent_count
  - acquisition_mode (standard default; list_first_non_repeat optional advanced)
- Source Intake:
  - Total Limit
  - Batch Size
- Cleanup:
  - dry_run default true
  - explicit run cleanup action

## 10. Recommended Source Intake Limit/Batch Behavior
Current local/external UX already uses Total Limit + Batch Size per run.

Recommended iCloud v1 behavior:
- keep both acquisition recent_count and intake Total Limit, but simplify defaults
- auto-suggest intake limit from staged inventory count when available
- if staged inventory unavailable, default intake limit blank (unlimited)
- keep Batch Size exposed with default 500
- present helper text clarifying:
  - recent_count limits iCloud candidate window
  - intake Total Limit limits staged-file processing for this intake run

## 11. Cleanup Timing Recommendation
Current cleanup behavior (backend/app/services/admin/icloud_staging_cleanup_execution_service.py):
- manual run only (no automatic cleanup)
- dry_run supported
- blocks if cleanup already active
- blocks if source intake active for same source
- only cloud_export sources under approved iCloud exports root
- eligible files require evidence coherence:
  - provenance exists for same source
  - corresponding vault asset/path exists
  - no conflicting failure/deferred evidence from source intake reports

Recommended v1 policy:
- keep cleanup manual by default
- do not auto-clean immediately after intake in first iCloud Ingestion workflow
- show cleanup recommendation and explicit confirmation step

## 12. Report/Summary Recommendation
Current report artifacts:
- iCloud acquisition report: storage/logs/icloud_connector_reports
- Source intake report: storage/logs/source_intake_reports
- Cleanup report: storage/logs/icloud_cleanup_reports

Current linkage characteristics:
- no single shared orchestration run id across acquisition/intake/cleanup
- linkable via:
  - ingestion_source_id (intake/cleanup, and inferred from acquisition registration)
  - source label/path
  - staging path
  - timestamps

Recommended v1 combined summary fields:
- Acquisition:
  - status, recent_count, downloaded_count, skipped_existing_count, failed_count, staging_path, report_path
- Intake:
  - status, files_scanned, skipped_known, selected, staged, processed_new_unique, failed_or_rejected, remaining_unknown, source_complete, report_path
- Cleanup:
  - status, dry_run, eligible_count, deleted_count, skipped_count, total_bytes_deleted, report_path
- Correlation:
  - source_id/source_label, source_root_path/effective_path, acquisition_run_id, source_intake_run_id, cleanup_run_id, started/finished timestamps

## 13. Concurrency/Locking Recommendation
Current observed constraints:
- iCloud acquisition has its own single-active lock
- Source Intake has its own single-active lock
- Cleanup blocks concurrent cleanup and blocks source intake active for same source
- No explicit cross-lock preventing acquisition while source intake is active
- No explicit cleanup block on active acquisition

Risk:
- overlapping acquisition/intake/cleanup can occur in combinations not intended for operator workflow safety

Recommended v1 policy for Ingestion workflow:
- enforce one ingestion-related operation at a time in Ingestion UI orchestration
- block:
  - acquisition if any source intake/cleanup active
  - source intake if acquisition/cleanup active
  - cleanup if acquisition/source intake active
- preserve Admin endpoints for diagnostics but warn on overlap risk

## 14. Error Handling Recommendation
Expected operator-facing iCloud failure classes for v1:
- AUTH_REQUIRED / SESSION_EXPIRED
- EXECUTABLE_NOT_FOUND
- VERSION_UNSUPPORTED
- SOURCE_NOT_REGISTERED
- NETWORK_OR_UPSTREAM_ERROR
- TIMEOUT / PROCESS_FAILED
- staging path missing/outside approved root (profile/path validation)
- permission denied / disk full / partial run failures (from stderr/classification)

Recommended message strategy:
- concise plain-language headline
- include backend error code
- include actionable next step
- include report path when available
- keep raw stdout/stderr tail behind expandable details

## 15. Relationship to Admin
Recommended direction:
- Ingestion tab becomes primary operator workflow for source-profile-based iCloud intake
- Admin remains diagnostics and low-level controls

API strategy recommendation:
- reuse existing Admin APIs immediately for staged rollout
- add a thin orchestration endpoint later only if cross-step state management becomes too complex client-side

Do not remove current Admin behavior in first phase.

## 16. Implementation Risks
Key risks identified:
- path convention mismatch between managed_staging_path defaults and acquisition resolve_staging_root convention
- label sanitization collisions leading to ambiguous staging directory identity
- concurrency overlap across acquisition/intake/cleanup due separate locks
- auth/session false assumptions because session readiness is inferred from runtime errors
- user confusion from dual limits (recent_count vs intake Total Limit) without clear copy
- no shared orchestration run id across three report types

## 17. Recommended Next Milestone
Recommended next slice:
- 12.62.1 iCloud Session + Staging Readiness Panel in Ingestion (no orchestration yet)

Proposed refined sequence:
1. 12.62.1 iCloud Source Profile Session/Staging Status UI
2. 12.62.2 Cross-Operation Concurrency Guardrails (orchestration-safe gating)
3. 12.62.3 Ingestion-Tab Acquire from iCloud (reuse existing acquisition API)
4. 12.62.4 Guided Source Intake Handoff in Ingestion
5. 12.62.5 Combined Acquisition + Intake Summary View
6. 12.62.6 iCloud Staging Cleanup Step in Ingestion (manual default)
7. 12.62.7 Report Correlation Polish
