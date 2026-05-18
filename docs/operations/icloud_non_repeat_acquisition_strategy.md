# iCloud Non-Repeat Acquisition Strategy (Milestone 12.48)

Date: 2026-05-18
Status: Design and reconnaissance complete
Scope: Production v1.0 strategy recommendation for non-repeat iCloud acquisition after staging cleanup

## 1. Operator Summary (Plain English)

Problem:
- Today, iCloud acquisition runs with a fixed recent window (for example 25).
- After Source Intake and verified staging cleanup, local staged files are gone.
- A later acquisition run may download those same recent files again.

Why fixed recent_count is not enough:
- It only checks the latest N items and does not prove full catch-up.
- Repeated runs after cleanup can re-download already-ingested files.

What "known" means in this strategy:
- staged-known: file exists in current staging folder.
- ingested-known: provenance exists for stable source plus source-relative path.
- vault-verified-known: ingested-known and linked asset exists and asset vault file exists.
- cloud-seen-known: item was previously seen in acquisition reporting/checkpoint state.

Chosen approach:
- Use a hybrid strategy: icloudpd for acquisition, Photo Organizer for known-state and caught-up reporting.
- Do not rely on icloudpd --until-found alone.

What operator sees later (12.48.1):
- downloaded
- skipped_existing
- already_known
- failed
- caught_up_status: likely_caught_up or partial_window_only or unknown

What is deferred:
- Full cloud-native checkpointing by stable iCloud asset ID.
- Multi-account orchestration.
- Fully unattended/scheduled acquisition.

## 2. Current Behavior Summary

Current iCloud acquisition behavior is implemented as:
- Admin starts a background icloudpd run.
- Command uses: --username, --directory, --recent.
- Staging path is storage/exports/icloud/<sanitized_source_label>.
- Run status/counters are saved to icloud_acquisition_runs.
- A JSON run report is written to storage/logs/icloud_connector_reports.
- Source Intake remains separate and authoritative for ingestion.
- iCloud staging cleanup is separate, conservative, and local-only.

Current gap:
- Non-repeat logic currently depends on local staged file presence (through icloudpd existing-file checks).
- After cleanup removes staged files, repeated downloads can reoccur for recent-window runs.

## 3. Code Paths Inspected

Acquisition service and schema:
- backend/app/services/icloud_acquisition/execution_service.py
- backend/app/services/icloud_acquisition/schema.py
- backend/app/models/icloud_acquisition_run.py

Admin API and request/response contracts:
- backend/app/api/admin.py
- backend/app/schemas/admin.py
- frontend/src/lib/api.ts
- frontend/src/components/IcloudAcquisitionCard.tsx
- frontend/src/types/ui-api.ts

Source registry and ingestion context:
- backend/app/models/ingestion_source.py
- backend/app/services/ingestion/ingestion_context_service.py

Provenance and persistence:
- backend/app/models/provenance.py
- backend/app/services/persistence/asset_repository.py
- backend/app/services/duplicates/lineage.py
- backend/app/services/ingestion/pipeline_orchestrator.py

Cleanup system:
- backend/app/services/admin/icloud_staging_cleanup_execution_service.py
- backend/app/models/icloud_staging_cleanup_run.py

## 4. Current icloudpd Capability Findings

Command used (safe inspection only):
- .tools/icloudpd/Scripts/icloudpd.exe --version
- .tools/icloudpd/Scripts/icloudpd.exe --help

Observed version:
- 1.32.2

Relevant help capabilities found:
- --recent
- --until-found UNTIL_FOUND
- --only-print-filenames (list-only, no download)
- --dry-run
- --file-match-policy {name-size-dedup-with-suffix,name-id7}
- --skip-videos, --skip-live-photos, --skip-photos
- --folder-structure
- --live-photo-mov-filename-policy

Important semantics from help text:
- --until-found: "until we find X number of previously downloaded consecutive photos".
- This is local-download-state oriented wording and does not indicate DB/provenance awareness.

Not found in current integration:
- No use of --until-found in current Photo Organizer command builder.
- No use of --only-print-filenames in current Photo Organizer flow.
- No cloud-native asset ID persistence in current acquisition run model.

## 5. Is --until-found Usable by Itself?

Assessment:
- --until-found exists and is technically available.
- It is not sufficient alone for Production v1.0 non-repeat behavior after staging cleanup.

Why:
- Its definition depends on "previously downloaded" state.
- Current cleanup deliberately removes successfully-ingested local staged files.
- After cleanup, local-existence-based stopping becomes unreliable for non-repeat goals.
- It does not inherently map to ingested-known or vault-verified-known.

Conclusion:
- Do not rely on icloudpd --until-found alone; implement Photo Organizer known-state logic.

## 6. Known-State Definition for 12.48.1

For each candidate item evaluated by Photo Organizer logic:
- staged-known:
  - Candidate file exists in current staging tree.
- ingested-known:
  - Provenance exists for ingestion_source_id + normalized source_relative_path.
- vault-verified-known:
  - ingested-known and linked Asset exists and asset.vault_path exists.
- cloud-seen-known:
  - Candidate identity appears in prior acquisition checkpoint/inventory state for this source.

v1.0 conservative already_known rule:
- already_known requires at least ingested-known.
- For cleanup-gated safety workflows, prefer vault-verified-known.

## 7. Option Comparison (A/B/C/D)

Option A - icloudpd --until-found directly:
- Pros: minimal code change, uses built-in behavior.
- Cons: local-file-state dependent; weak after cleanup; no DB/provenance awareness.
- Verdict: not sufficient alone.

Option B - Recent window + provenance known threshold:
- Pros: uses durable DB evidence; aligns with Source Intake provenance model.
- Cons: still needs candidate identity from acquisition/listing; filename-only identity can be ambiguous.
- Verdict: viable if paired with explicit candidate inventory and conservative matching rules.

Option C - Photo Organizer checkpoint only:
- Pros: durable per-source state independent of current staging file existence.
- Cons: quality depends on identity key; weak key gives false confidence.
- Verdict: useful but should not stand alone without clear candidate identity and reporting.

Option D - Hybrid (recommended):
- Pros: keeps icloudpd as downloader, adds Photo Organizer known-state and caught-up reasoning.
- Cons: moderate implementation complexity.
- Verdict: best v1.0 balance of safety, operator clarity, and practical scope.

## 8. Recommended v1.0 Strategy

Required recommendation format:
- Use a hybrid approach: icloudpd for acquisition, Photo Organizer for known-state/caught-up reporting.

Additional explicit decision:
- Do not rely on icloudpd --until-found alone; implement Photo Organizer known-state logic.

Hybrid v1.0 behavior target:
1. Preflight candidate check (safe/list-only path).
2. Compare candidates against provenance plus asset plus vault evidence.
3. If all candidates are already_known, skip download run and report likely_caught_up.
4. If mixed unknown and known, run acquisition and report downloaded plus already_known classification.
5. Maintain per-source acquisition checkpoint/inventory summary for operator trust.

## 9. Required Implementation Steps for 12.48.1

1. Extend acquisition request/config model (backend only):
- Add optional mode fields for preflight/list-first strategy (no UI redesign required in 12.48.1).

2. Extend command builder safely:
- Add support for list-only preflight flags when requested:
  - --only-print-filenames
  - optional --dry-run
- Keep existing acquisition mode unchanged by default.

3. Parse candidate identities from preflight output:
- Normalize candidate paths/names.
- Keep parser conservative and transparent (capture unknown parse lines as unknown_identity).

4. Add known-state evaluator service:
- Input: source identity plus candidate list.
- Queries: provenance by ingestion_source_id and source_relative_path, then asset/vault verification.
- Output per candidate:
  - already_known true/false
  - known_evidence level (ingested-known or vault-verified-known)

5. Add acquisition run/report fields (or companion report payload) for operator status:
- already_known_count
- unknown_identity_count
- caught_up_status (likely_caught_up, partial_window_only, unknown)
- preflight_candidate_count

6. Add conservative short-circuit:
- If preflight candidates are all already_known and no unknown_identity:
  - do not run download subprocess
  - mark run completed with already_known status and likely_caught_up

7. Preserve existing safety boundaries:
- No automatic Source Intake.
- No automatic cleanup.
- No vault/iCloud deletion behavior changes.

## 10. Required Reporting Changes

Minimum 12.48.1 status/report support:
- downloaded
- skipped_existing
- already_known
- failed
- caught_up_status

Caught-up status enum:
- likely_caught_up
- partial_window_only
- unknown

Additional recommended fields:
- preflight_candidate_count
- unknown_identity_count
- known_evidence_basis summary
- whether download subprocess was skipped due to all-known preflight

## 11. Validation Plan (12.48.1 / 12.48.2)

Dataset:
- Use test source only.
- Keep recent_count <= 25.
- No full-library run.

Test sequence:
1. Run 1 (acquisition):
- Acquire recent items.
- Capture acquisition report.

2. Run 2 (repeat without cleanup):
- Confirm skipped-existing behavior and report consistency.

3. Source Intake:
- Ingest staged files.
- Capture source intake report.

4. Verified cleanup:
- Dry-run then execute cleanup.
- Capture cleanup report.

5. Run 3 (after cleanup):
- Execute list-first/non-repeat strategy.
- Validate:
  - repeated files are avoided or explicitly classified already_known
  - caught_up_status is surfaced
  - no false "new work" confusion

Expected outputs to record:
- downloaded count
- skipped_existing count
- already_known count
- failed count
- caught_up_status
- report file paths

Safety checks:
- no iCloud deletion
- no vault deletion
- no DB reset
- no destructive source registry actions

## 12. Safety Constraints (Preserved)

Confirmed constraints for strategy and future implementation:
- acquisition writes only to exports/iCloud staging
- Source Intake remains ingestion authority
- cleanup remains local-only with provenance plus asset plus vault verification
- no credential/token persistence in app DB
- no destructive cloud/vault actions

## 13. Explicit Deferrals

Deferred beyond 12.48:
- full cloud-native checkpoint by stable iCloud asset ID
- broad UI redesign for Admin acquisition
- multi-account strategy and source lifecycle archive/inactive model
- unattended scheduler behavior
- full-library completeness guarantees in a single run

## 14. Recon Limitations and Missing Evidence

Observed limitations during this milestone:
- Local Postgres was not running during recon, so live DB row inspection was unavailable.
- No current runtime report files were present in storage/logs to sample real payloads.

Evidence still needed in 12.48.1 validation:
- exact parse shape from --only-print-filenames output in this project's runtime conditions
- empirical behavior of --until-found when staging was previously cleaned
- practical identity quality for candidate matching when filename/path collisions occur

Given these limits, the recommendation remains safe and explicit:
- hybrid strategy with Photo Organizer known-state logic; no reliance on --until-found alone.

## 15. 12.48.1 Implementation Update

Status:
- Implemented backend foundation for explicit non-repeat mode in Milestone 12.48.1.

Implemented acquisition mode:
- Added explicit acquisition_mode values:
  - standard (default, unchanged behavior)
  - list_first_non_repeat (new explicit behavior)

Preflight command behavior:
- list_first_non_repeat performs safe preflight using:
  - --recent <N>
  - --dry-run
  - --only-print-filenames
- preflight does not download media bytes.

Candidate parser behavior:
- Added conservative parser for preflight output lines.
- Preserves raw_line for audit.
- Normalizes separators/path prefixes.
- Any non-confident identity is classified as unknown_identity.
- unknown_identity lines are retained in report samples.

Known-state evaluator behavior:
- Added known-state evaluator against durable evidence:
  - staged_known (staging file exists)
  - ingested_known (provenance match by source + source_relative_path)
  - vault_verified_known (ingested_known + asset + vault path exists)
- already_known is true only when ingested_known or vault_verified_known.
- staged_known alone is not treated as durable already_known.

Caught-up status logic:
- Added conservative enum behavior:
  - likely_caught_up
  - partial_window_only
  - unknown
- unknown_identity prevents likely_caught_up.
- likely_caught_up requires successful preflight, nonzero candidates, no unknown identities, all candidates already_known, and explicit download short-circuit.

Short-circuit behavior:
- If all preflight candidates are already_known and unknown_identity_count is zero:
  - skip download subprocess
  - complete run successfully
  - report download_skipped_due_to_all_known=true

Run/report fields:
- Detailed non-repeat metrics are report-first (JSON) for 12.48.1.
- Added report fields:
  - acquisition_mode
  - preflight_enabled
  - preflight_ok
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
- Added minimal run-table field:
  - acquisition_mode

Validation performed:
- Unit tests only (no real iCloud runs):
  - command builder tests for standard vs preflight-safe flags
  - acquisition_mode normalization tests
  - parser and caught-up status tests
  - known-state evaluator tests with mocks/temp files

Remaining limitations:
- Real repeat-run workflow validation remains pending (12.48.2):
  - acquire -> repeat -> intake -> cleanup -> repeat after cleanup
- Candidate parser remains conservative and may classify borderline lines as unknown_identity.
