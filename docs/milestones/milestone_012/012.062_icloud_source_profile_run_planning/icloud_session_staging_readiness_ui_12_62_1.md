# iCloud Session and Staging Readiness UI 12.62.1

## 1. Purpose
Milestone 12.62.1 adds iCloud readiness/status visibility in the Ingestion tab for iCloud Source Profiles.

This milestone is UI/readiness-only:
- no iCloud acquisition launch from Ingestion
- no source intake handoff execution for iCloud
- no cleanup execution
- no credential collection

## 2. Readiness Panel Behavior
Placement:
- Ingestion tab Source Profile Details drawer for iCloud profiles only:
  - source_type=cloud_export
  - cloud_provider=icloud

Panel includes:
- overall readiness badge
- managed staging path state
- expected acquisition path
- path alignment status
- source registration best-effort status
- auth/session status (conservative)
- last matching acquisition status (if clearly matched)
- recommended next action
- static Admin fallback note

Non-iCloud profiles:
- do not show iCloud readiness panel.

## 3. Readiness Status Definitions
States shown:
- Ready
- Warning
- Not Ready
- Unknown

Current 12.62.1 policy:
- Not Ready for blocking conditions:
  - profile not active
  - managed staging path outside approved iCloud exports root
  - managed staging path and expected acquisition path mismatch
  - auth action required (AUTH_REQUIRED/SESSION_EXPIRED)
  - source registration mismatch (best-effort derived)
- Warning for caution/partial conditions:
  - staging folder not checked/missing
  - auth unknown
  - source registration unknown
- Unknown used only when profile/readiness context cannot be computed.

## 4. Staging Path Display
Readiness panel shows:
- Managed Staging Path
- Approved root result
- Staging folder status (exists/missing/not checked/unsafe)

Path/staging checks reuse existing Details behavior:
- Verify Staging
- Create Staging Folder (existing approved action)

## 5. Acquisition Path Display
Readiness panel shows Expected Acquisition Path derived from current acquisition resolver convention:
- storage/exports/icloud/<sanitized_label>

Sanitization mirrors acquisition behavior:
- lowercase/trim
- non [a-z0-9_-] collapsed to underscore
- repeated separators collapsed
- fallback unnamed_source

## 6. Path Alignment Warning
If managed staging path differs from expected acquisition path, panel shows mismatch and Not Ready.

Required warning text shown:
- Managed staging path differs from the current iCloud acquisition path. Acquisition may fail or use a different folder until this is aligned.

## 7. Source Registration Match Behavior
12.62.1 uses best-effort frontend composition (no new endpoint):
- matched
- mismatch
- unknown

Signals used:
- path alignment result
- matched latest acquisition status source_registration_status when clearly tied to profile identity

If uncertain, panel shows unknown plus explanatory helper text.

## 8. Auth/Session Display Behavior
Auth state is intentionally conservative:
- Action Required when last matching acquisition error_code is AUTH_REQUIRED or SESSION_EXPIRED
- Unknown otherwise

No auth Ready state is shown in this milestone.

Credential safety:
- no password field
- no 2FA field
- helper text explicitly states auth is handled outside app by icloudpd.

## 9. Last Acquisition Status Behavior
Panel shows last acquisition status only when global latest acquisition record clearly matches the selected profile by:
- source label
- source type cloud_export
- staging/source root path equivalence to expected/acquisition-relevant path

If not clearly matched:
- No matching recent acquisition status found.

Shown fields when matched:
- status
- started/finished
- downloaded/skipped/failed counts
- error code
- report path

## 10. Admin Relationship
Admin iCloud tooling is unchanged.

Panel includes static note:
- iCloud acquisition is still run from Admin until the Ingestion iCloud workflow is implemented.

## 11. Safety Boundaries
Confirmed unchanged:
- no iCloud acquisition launch from Ingestion
- no iCloud source intake launch/handoff execution
- no cleanup execution
- no source path rewrites
- no source registration auto-repair
- no credential/token/session storage behavior changes
- no Admin iCloud behavior changes

## 12. Validation Performed
Validated:
- TypeScript diagnostics for changed frontend files (no errors)
- frontend production build passes

## 13. Limitations
Known limitations for 12.62.1:
- no deterministic session-health endpoint; auth is inferred from last known matched error only
- source registration status is best-effort in frontend and may be unknown when evidence is insufficient
- readiness is intentionally conservative and does not attempt backend launch-equivalent validation
- no row-level readiness badge added in table (Details drawer is source of truth)

## 14. Recommended Next Milestone
Recommended next:
- 12.62.2 iCloud Staging Path Alignment and Cross-Operation Guardrail Planning

Suggested focus:
- align managed_staging_path and acquisition resolver path conventions
- define stricter registration/readiness validation policy
- plan cross-operation guardrails across acquisition/intake/cleanup
