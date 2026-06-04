# Coder Response 12.41
## iCloudpd Connector Service Design

Date: 2026-05-09
Milestone prompt: 12.41 icloudpd connector service design

## Scope Completed

Completed a design-only milestone for integrating icloudpd as a supported acquisition connector while preserving architecture boundaries and safety guardrails.

This response covers:
- execution model decision
- command and path safety model
- Source Registry relationship
- credential/session policy
- run/status/report model
- Source Intake handoff design
- Admin UI preview for follow-on milestone
- implementation scope split for 12.42 and 12.43
- explicit deferrals

No backend or frontend implementation code was added for this milestone.

## Summary Decision

Use icloudpd as the preferred iCloud acquisition adapter, with strict boundary separation:
- icloudpd acquires to staged export folders only
- Source Intake remains the ingestion authority
- no direct icloudpd writes to Drop Zone, Vault, or DB

Raw PyiCloud scripts remain available as experimental/diagnostic tooling.

## Reconnaissance Completed (Step 2.5)

Reviewed existing patterns before finalizing design:
- admin background job run/stop/status patterns
- existing run tables and status snapshots
- report/log directory conventions
- Source Registry and Source Intake APIs/workflow
- config/path conventions
- existing subprocess usage
- frontend admin card patterns
- operator docs and icloud evaluation artifacts

Result: the 12.41 design intentionally reuses current project patterns instead of introducing a new architecture style.

## Key Design Decisions

### 1) Installation and Execution Model

Selected: Option B, project-managed helper environment.
- icloudpd isolated from backend venv
- reproducible and version-controllable
- executable resolution supports explicit override, helper path, then PATH fallback

### 2) Command Construction and Guardrails

Design uses strict backend command allowlist with structured arguments only.

Required inputs:
- source_label
- username (Apple ID)
- recent_count
- validated staging path

Limits:
- default recent_count: 100
- max recent_count: 500

Disallowed:
- delete/mutation flags
- output paths outside storage/exports/icloud/source_label
- direct output to Drop Zone or Vault

### 3) Staging Convention

Canonical staging path:
- storage/exports/icloud/source_label

Policy:
- sanitize source_label before folder use
- create folder if missing, reuse if present
- never auto-delete staged files

### 4) Source Registry Relationship

Target model:
- source_label = stable iCloud account/library identity
- source_type = cloud_export
- source_root_path = storage/exports/icloud/source_label

12.42 behavior:
- check source registration before acquisition
- do not auto-create source registration
- block run with explicit guidance if source is missing

### 5) Credential and Session Policy

Security decisions:
- do not store Apple password in DB/config
- do not send password/2FA through Admin UI in this phase
- rely on icloudpd session/cookie behavior
- surface auth/session-expiry failures as operator guidance

### 6) Run/Status Model

Selected: persisted run record plus report artifact.

12.42 should add:
- background run model and status endpoint
- stdout/stderr tail capture with truncation
- counters (downloaded/skipped/failed)
- report path and sanitized command snapshot
- best-effort Stop support

### 7) Report Format

Report directory:
- storage/logs/icloud_connector_reports

Report includes:
- run metadata and status
- source and staging details
- sanitized command
- counts and log tails
- source registration status
- recommended Source Intake command

Report excludes secrets (passwords, 2FA, cookies, tokens).

### 8) Source Intake Handoff

12.42 and 12.43 keep the boundary explicit:
1. Run iCloud Acquisition
2. Review run report
3. Run Source Intake manually

No automatic acquisition-plus-intake chaining in this milestone scope.

### 9) Admin UI Preview (12.43)

Planned Admin card:
- source label selector
- Apple ID/username
- recent count input
- staging path display
- run/stop controls
- live status and last-run summary
- report link/details
- source registration status
- next action: Run Source Intake

## Clarification Answers (Requested by Milestone)

1. Which installation model is recommended?
- Option B (project-managed helper environment).

2. Should 12.42 use a subprocess wrapper?
- Yes.

3. Should 12.42 create a DB run table?
- Yes, plus JSON report artifacts.

4. Should 12.42 include Stop support?
- Yes, best-effort graceful stop.

5. Should acquisition auto-create source registration?
- No.

6. Should acquisition auto-run Source Intake?
- No.

7. What should max recent count be?
- 500 (default 100).

8. How should credential/session requirements be surfaced?
- Explicit auth/session error states with operator guidance; no password handling in app.

9. What Admin UI should 12.43 implement?
- Dedicated iCloud Acquisition card with run/status/stop/report and Source Intake handoff.

10. What remains deferred?
- Scheduling, credential vaulting, auto-chaining into Source Intake, mutation operations, and advanced iCloud metadata import features.

## Deliverable Location

Primary design document created at:
- docs/architecture/icloudpd_connector_service_design_12_41.md

This Coder response document is the milestone closeout summary.

## Definition of Done Check

12.41 done criteria met:
- clear design document exists
- icloudpd selected as preferred adapter
- execution model chosen
- staging convention defined
- credential/session policy defined
- run/status/report model defined
- Source Intake handoff defined
- Admin UI plan defined
- implementation scope for 12.42 and 12.43 defined

## Explicit Deferrals

Deferred as requested:
- backend implementation
- Admin UI implementation
- scheduled sync automation
- NAS automation specifics
- credential vault/password manager integration
- full-library unbounded download orchestration
- iCloud mutation operations
- automatic Source Intake execution
- Live Photo playback
- cloud-native iCloud provenance schema expansion
- iCloud albums/favorites/people import
