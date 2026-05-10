# Milestone 12.41 Design: iCloudpd Connector Service

## 1) Summary Decision

Decision: Adopt icloudpd as the preferred iCloud acquisition adapter, implemented as a backend-managed connector service that stages files only.

Boundary:
- icloudpd acquires to storage/exports/icloud/<source_label>/
- Source Intake ingests from registered source roots
- No direct writes from icloudpd to Drop Zone, Vault, or DB

Decision record:
- Raw PyiCloud adapter remains experimental and useful for diagnostics, metadata exploration, and fallback investigation.
- icloudpd is preferred for practical acquisition because it has proven authentication/session behavior and skip-existing download semantics.

## 2) Installation and Execution Model

Selected model for 12.42: Option B, project-managed helper environment.

Design:
- Install icloudpd into a dedicated helper environment under project root:
  - .tools/icloudpd/ (venv and pinned requirements)
- Backend resolves executable in this order:
  1. Explicit config value (for operator override)
  2. Project helper executable path
  3. System PATH fallback
- Backend records resolved executable path and version per run report.

Rationale:
- Keeps backend venv dependency surface stable
- Provides reproducibility for local and server installs
- Avoids deployment fragility of PATH-only setups

## 3) Command Construction and Allowlist

Command shape (12.42):
- icloudpd
- --username <apple_id>
- --directory <validated_staging_path>
- --recent <count>
- --skip-videos false (default behavior retained if currently expected)
- any required non-mutating auth/session flags supported by icloudpd runtime

Required runtime inputs:
- source_label
- username (Apple ID)
- recent_count
- staging directory (derived, not user free-typed)

Defaults and limits:
- default recent_count: 100
- max recent_count: 500
- values outside range rejected with validation error

Allowed flags policy:
- Strict backend allowlist only
- Unknown or unsupported advanced flags rejected in 12.42
- Future advanced options can be added explicitly one-by-one

Forbidden flags and behaviors:
- Any delete or mutation option
- Any option that can modify/remove iCloud content
- Any output directory outside storage/exports/icloud/<source_label>/
- Any direct Drop Zone or Vault output path

Safety validation before subprocess launch:
- source_label sanitized and normalized
- staging path canonicalized and validated as descendant of storage/exports/icloud
- recent_count validated against cap
- command built from structured args, never shell-concatenated user text

## 4) Staging Path Convention

Canonical staging root:
- storage/exports/icloud/<source_label>/

Path policy:
- Configurable base root through backend settings for portability
- source_label sanitation rules:
  - lowercase normalization
  - allowed: a-z, 0-9, underscore, hyphen
  - disallowed characters replaced with underscore
  - collapse repeated separators
  - trim leading/trailing separators
- Folder creation:
  - create if missing
  - reuse if exists
  - never delete staged files automatically

Admin display:
- Show resolved absolute path and project-relative path
- Show source registration status for same path

## 5) Source Registry Relationship

Target source model:
- source_label: stable iCloud account/library identity
- source_type: cloud_export
- source_root_path: storage/exports/icloud/<source_label>/

12.42 behavior:
- Acquisition checks Source Registry before launch
- If missing source registration:
  - Run is blocked by default
  - API returns SOURCE_NOT_REGISTERED with source create guidance
- No implicit auto-create during acquisition in 12.42

12.43 UX:
- Admin card offers explicit Register Source action before Run Acquisition
- Acquisition and registration remain separate actions

## 6) Credential and Session Handling

Security policy:
- No Apple ID password stored in app DB or config
- No password or 2FA code entry in Admin UI in 12.42/12.43
- Use icloudpd native session/cookie behavior

Backend behavior:
- Connector attempts run assuming session already exists
- If icloudpd reports auth required, 2FA required, or session expired:
  - Mark run failed with explicit auth status code
  - Return operator guidance for manual session bootstrap
- Never log secrets; redact username minimally where needed

Session location handling:
- Backend does not need deep session-file parsing in 12.42
- Backend only surfaces auth-state errors from icloudpd execution output

## 7) Run and Status Model

Decision: persisted DB run model plus JSON report artifact.

New model for 12.42:
- icloud_acquisition_runs

Core fields:
- id
- status (idle, running, stop_requested, completed, failed, stopped)
- source_label
- source_type
- source_root_path
- username
- staging_path
- recent_count
- started_at
- completed_at
- elapsed_seconds
- exit_code
- downloaded_count
- skipped_existing_count
- failed_count
- stdout_tail
- stderr_tail
- report_path
- error_code
- error_message
- created_by
- stop_requested

Service pattern:
- Reuse existing admin background pattern used by duplicate, face, and source-intake services
- Single active run lock
- Snapshot status endpoint
- Run endpoint returns accepted + run id

Stop support (12.42):
- Include best-effort Stop
- Behavior:
  - if process active, request terminate
  - mark stop_requested immediately
  - finalize as stopped if termination succeeds
- If process already ended, stop returns no-op with latest status

## 8) Report Format

Report storage:
- Reuse existing convention directory: storage/logs/icloud_connector_reports/

File naming:
- icloudpd_acquisition_<UTC timestamp>.json

Report schema:
- report_type: icloudpd_acquisition
- timestamp_utc
- status
- source_label
- source_registration_status
- username_redacted
- staging_path
- command_sanitized
- resolved_executable
- icloudpd_version
- recent_count
- exit_code
- downloaded_count
- skipped_existing_count
- failed_count
- stdout_tail
- stderr_tail
- file_inventory_after_run
- recommended_source_intake_command
- notes

Redaction policy:
- Exclude passwords, tokens, 2FA codes, session cookie values, raw secret-bearing env vars
- Truncate stdout/stderr tails to bounded size

## 9) Relationship to Source Intake

Workflow for 12.42/12.43:
1. Run iCloud Acquisition
2. Review run status and report
3. Run Source Intake manually

Policy:
- No automatic Source Intake trigger in 12.42
- Acquisition report includes exact next command and API handoff hints
- Admin UI shows clear next action button for Source Intake

## 10) Admin UI Design Preview (for 12.43)

Admin section title:
- iCloud Acquisition

Fields:
- Source label selector
- Username input (Apple ID)
- Recent count input with cap hint
- Resolved staging folder display
- Source registration status badge
- Run button
- Stop button
- Current run status panel
- Last run summary counts
- Report link
- Next action: Run Source Intake

Warnings shown inline:
- Experimental connector
- Download-only staging
- Does not ingest directly to Vault or DB
- Requires valid icloudpd session

## 11) Safety Guardrails

Hard guardrails:
- Command allowlist only
- Reject forbidden/mutating flags
- Validate output path is under storage/exports/icloud
- Never write to Drop Zone or Vault directly
- source_label sanitation and normalization
- recent_count max cap
- subprocess runtime timeout
- single-active-run lock
- secret redaction in logs and reports
- bounded stdout/stderr capture

## 12) Error Handling Matrix

1) icloudpd not installed
- Admin message: icloudpd executable not found
- Report: failed with error_code EXECUTABLE_NOT_FOUND
- Retry safe: yes after install
- Source Intake blocked: yes

2) unsupported icloudpd version
- Admin message: unsupported version, expected minimum shown
- Report: failed with VERSION_UNSUPPORTED
- Retry safe: yes after update
- Source Intake blocked: yes

3) authentication required
- Admin message: session required, run manual icloudpd auth bootstrap
- Report: failed with AUTH_REQUIRED
- Retry safe: yes after auth bootstrap
- Source Intake blocked: yes

4) 2FA required / session expired
- Admin message: re-authentication required
- Report: failed with SESSION_EXPIRED
- Retry safe: yes after re-auth
- Source Intake blocked: yes

5) network failure / Apple server issue / rate limit
- Admin message: temporary upstream/network failure
- Report: failed with NETWORK_OR_UPSTREAM_ERROR
- Retry safe: yes with backoff
- Source Intake blocked: yes

6) output path invalid
- Admin message: invalid staging path configuration
- Report: failed with INVALID_STAGING_PATH
- Retry safe: yes after config fix
- Source Intake blocked: yes

7) partial download
- Admin message: run completed with partial failures
- Report: completed_with_warnings including counts
- Retry safe: yes
- Source Intake blocked: no, operator decision

8) subprocess timeout
- Admin message: acquisition timed out
- Report: failed with TIMEOUT
- Retry safe: yes
- Source Intake blocked: yes

9) operator cancel
- Admin message: run stopped by operator
- Report: status stopped
- Retry safe: yes
- Source Intake blocked: yes for that run

## 13) Implementation Plan for 12.42 (Backend)

1. Add icloud acquisition run model and migration
2. Add service module with background worker, lock, stop flag, and status snapshot
3. Add executable resolver and version probe utility
4. Add source_label sanitizer and staging path validator utility
5. Add command builder with strict allowlist
6. Add subprocess runner with timeout and bounded log capture
7. Add report writer under storage/logs/icloud_connector_reports
8. Add admin API endpoints:
   - POST /api/admin/icloud-acquisition/run
   - GET /api/admin/icloud-acquisition/status
   - POST /api/admin/icloud-acquisition/stop
9. Add source registration preflight check
10. Add backend tests:
   - command construction safety
   - path validation
   - missing source behavior
   - auth error mapping
   - stop behavior

## 14) UI Implementation Plan for 12.43

1. Add iCloud Acquisition card to Admin view
2. Wire run/status/stop API calls following existing card patterns
3. Add polling while running or stop_requested
4. Add source registration status and Register Source shortcut
5. Add last-run summary and report link
6. Add warning panel and session guidance text
7. Add basic form validation for source_label, username, recent_count

## 15) Explicit Deferrals

Deferred beyond 12.43:
- Automatic acquisition plus Source Intake chaining
- Scheduled sync and cron orchestration
- NAS-specific deployment automation
- Credential vault integration
- Password/2FA entry in Admin UI
- Full-library unbounded downloads
- Any iCloud mutation operations
- Album/favorites/people import
- Cloud-native iCloud provenance schema expansion
- Live Photo playback UI

## Clarification Answers (Requested in 12.41 prompt)

1. Installation model recommended: Option B project-managed helper environment.
2. 12.42 subprocess wrapper: yes.
3. 12.42 DB run table: yes, plus report artifact.
4. 12.42 Stop support: yes, best-effort graceful stop.
5. Auto-create source registration: no, keep explicit.
6. Auto-run Source Intake: no.
7. Max recent count: 500 (default 100).
8. Credential/session surfacing: auth errors mapped to explicit operator guidance, no password handling in app.
9. 12.43 Admin UI: dedicated iCloud Acquisition card with run/status/stop/report and Source Intake handoff.
10. Deferred items: scheduling, vault/credential integration, auto-chaining, mutation operations, advanced iCloud metadata imports.
