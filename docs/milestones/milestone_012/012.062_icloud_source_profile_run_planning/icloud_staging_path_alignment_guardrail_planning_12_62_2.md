# iCloud Staging Path Alignment and Cross-Operation Guardrail Planning 12.62.2

## 1. Purpose
Milestone 12.62.2 defines a safe path alignment strategy for iCloud Source Profiles and recommends guardrails before any iCloud execution is added to the Ingestion tab.

This milestone is planning/reconnaissance only:
- no Ingestion iCloud acquisition launch
- no source intake handoff execution for iCloud
- no cleanup execution from Ingestion
- no automatic path repair
- no source registration merge
- no provenance rewrite
- no credential/session handling changes

## 2. Current Managed Staging Path Generation
Current iCloud Source Profile creation logic in backend/app/services/admin/source_intake_service.py computes managed staging paths as:
- storage/exports/icloud/<slugified-source-label>

Exact generation rule:
- source label is lowercased and slugified with hyphens
- provider is inserted as a path segment (`icloud`)
- resulting path is absolute under the project root

Current source profile detail behavior:
- iCloud cloud_export profiles prefer managed_staging_path as the effective path
- source_root_path remains stored as compatibility/identity metadata
- profile details expose both paths plus effective_path_kind and divergence warnings

## 3. Current Acquisition Resolver Behavior
Current iCloud acquisition launch path in backend/app/services/icloud_acquisition/execution_service.py resolves staging root as:
- storage/exports/icloud/<sanitized-source-label>

Exact acquisition resolver rule:
- source_label is sanitized to lowercase
- non [a-z0-9_-] characters collapse to underscore
- repeated separators collapse
- default fallback is unnamed_source

Current launch validation requires an exact source registration match against:
- normalized source_label
- source_type
- normalized source_root_path equal to the resolved staging root

Current Admin acquisition flow therefore uses the acquisition resolver-derived path, not the profile managed_staging_path default.

## 4. Current source_root_path / Identity Behavior
Current source profile identity behavior in backend/app/services/admin/source_intake_service.py and backend/app/services/ingestion/ingestion_context_service.py:
- source_root_path is still a compatibility identity path for registration and historical matching
- source profiles may also carry managed_staging_path
- effective path for iCloud cloud_export profiles prefers managed_staging_path when present
- source_root_path and managed_staging_path can diverge today

Current code that treats either path as identity/effective operational data:
- source profile detail views show both
- ingestion context matching uses source_label + source_type + source_root_path
- acquisition run reporting/launch matching uses source_label + source_type + source_root_path
- source profile warnings already surface path divergence

## 5. Current Source Registration Match Behavior
Current acquisition launch-time match is strict:
- normalized label must match
- source_type must match cloud_export
- normalized source_root_path must equal resolved acquisition staging path

Current profile detail/readiness behavior:
- 12.62.1 shows best-effort registration status in the UI
- exact launch-equivalent validation is not yet centralized in a backend readiness endpoint

## 6. Path Mismatch Risks
Primary mismatch risk identified:
- managed_staging_path default generation includes provider segment
- acquisition resolver currently does not include provider segment

Implications:
- a profile may appear operationally ready in the UI but fail acquisition launch validation later
- acquisition may write to a different folder than the profile detail implies if the conventions are not aligned
- registration matching can fail even when the profile looks structurally correct

This is the main planning problem for 12.62.2.

## 7. Alignment Strategy Options
### Option A — Align profile generation to current acquisition resolver
Set:
- managed_staging_path = storage/exports/icloud/<slug>
- source_root_path = storage/exports/icloud/<slug>

Pros:
- smallest change to acquisition behavior
- preserves current Admin acquisition path convention
- simpler immediate compatibility

Cons:
- less expressive if provider-specific staging layout is desired later
- source profile may remain a compatibility wrapper around current acquisition behavior rather than the operational source of truth

### Option B — Align acquisition resolver to managed_staging_path
Use:
- acquisition path = source_profile.managed_staging_path

Pros:
- source profile becomes the operational source of truth
- more future-proof for provider-specific layouts
- less hidden path derivation

Cons:
- requires acquisition to resolve profile first
- needs backward compatibility for existing profiles and Admin execution
- may change current Admin behavior unless phased carefully

### Option C — Compatibility mapping for both paths
Support both the current resolver path and managed_staging_path as valid/compatible paths.

Pros:
- preserves legacy behavior
- can smooth migration

Cons:
- most complex option
- can create two-folder ambiguity
- harder to explain and support in UI and reports

## 8. Recommended Alignment Strategy
Recommended direction:
- make Source Profile managed_staging_path the eventual operational truth
- but stage the transition carefully

For the next implementation slice:
1. add stronger read-only validation and warnings
2. define one canonical path policy for new profiles
3. preserve compatibility for existing profiles during transition
4. avoid auto-repair or silent path mutation

Pragmatic recommendation for the next milestone:
- choose one canonical layout and make both profile creation and acquisition resolve to that same canonical path
- keep Admin compatible during transition

## 9. Existing Profile Mismatch Handling Recommendation
Current code can deterministically detect mismatches by comparing:
- managed_staging_path
- expected acquisition path
- approved root membership
- profile status

What is not currently known from code alone:
- how many existing iCloud profiles are mismatched in the live database

That count requires a database scan or query, not just static code inspection.

Recommended policy:
- do not auto-repair referenced profiles
- for unreferenced mismatched profiles, allow explicit repair later only if a safe path exists
- for referenced profiles, recommend archive/recreate unless a safe migration path is proven
- keep repair manual in all cases

## 10. Readiness Validation Policy
Recommended readiness states for future execution:

### Ready
- profile_status = active
- cloud_export + icloud
- approved root OK
- managed staging path aligned with expected acquisition path
- source registration matched or deterministically satisfiable
- no known auth-required state
- no conflicting active operation

### Warning
- auth unknown
- staging folder missing but creatable
- no recent acquisition status
- path is otherwise aligned but not yet verified on disk

### Not Ready
- profile not active
- path mismatch
- unsafe path / outside approved root
- source registration mismatch
- active conflicting operation
- last auth error AUTH_REQUIRED or SESSION_EXPIRED

### Unknown
- readiness cannot be determined from existing data

Recommended policy refinement from code findings:
- path mismatch and approved-root blocked should remain hard Not Ready
- auth should remain conservative; do not infer Ready without a deterministic check

## 11. Cross-Operation Concurrency Findings
Current locks/guards observed:
- iCloud acquisition has its own single-active lock
- Source Intake has its own single-active lock
- iCloud cleanup has its own active-run lock
- cleanup blocks source intake for the same source

Current gaps:
- acquisition is not explicitly blocked by source intake
- source intake is not explicitly blocked by acquisition
- cleanup is not explicitly blocked by acquisition
- cleanup for different sources is not globally coordinated with acquisition/intake

Conclusion:
- current backend locks are not sufficient by themselves for a safe unified Ingestion iCloud workflow

## 12. Guardrail Implementation Options
### UI-only guardrails
Ingestion checks active statuses and disables buttons.

Pros:
- low risk
- fast to ship

Cons:
- Admin can still launch overlapping operations
- race conditions remain possible

### Backend guardrail checks
Backend checks acquisition/intake/cleanup active state before launching Ingestion workflow actions.

Pros:
- safer and race-resistant
- consistent regardless of UI entry point

Cons:
- backend behavior changes required
- must avoid disturbing Admin diagnostics unless intentionally shared

### Orchestration service
Create a unified coordinator for iCloud acquisition/intake/cleanup.

Pros:
- best long-term architecture
- supports combined summary and state correlation later

Cons:
- larger scope
- should not be first step

Recommended staged approach:
1. UI guardrails first for operator feedback
2. backend shared guardrail checks next for enforcement
3. orchestration service only after path policy stabilizes

## 13. Admin Compatibility Recommendation
Admin should remain the diagnostic and legacy execution surface.

Recommended compatibility policy:
- do not break Admin iCloud behavior during path alignment work
- if the resolver changes, preserve backward-compatible behavior for existing Admin flows
- allow Ingestion to move toward source-profile-aware operation without removing Admin controls

Long-term direction:
- Ingestion becomes primary operator workflow
- Admin remains advanced/diagnostic fallback

## 14. Implementation Risks
Key risks:
- path-convention migration may break existing profiles if handled too aggressively
- dual-path compatibility can confuse users and create duplicate folders
- cross-operation guardrails can become inconsistent if only implemented in UI
- source registration match semantics may diverge between readiness and launch if not centralized
- old profiles may be referenced and therefore unsafe to auto-repair

## 15. Recommended Next Milestones
Recommended next slice after 12.62.2:
1. establish the canonical iCloud staging path policy
2. add a backend readiness/validation endpoint if frontend composition becomes insufficient
3. implement shared cross-operation guardrail checks
4. only then add Ingestion-tab iCloud acquisition launch
5. follow with guided source intake handoff
6. then combined acquisition/intake summary
7. finish with manual cleanup workflow

Suggested milestone sequence:
- 12.62.3 iCloud Path Canonicalization Foundation
- 12.62.4 iCloud Readiness Validation Endpoint
- 12.62.5 Cross-Operation Guardrails
- 12.62.6 Acquire from iCloud in Ingestion
- 12.62.7 Guided Source Intake Handoff
- 12.62.8 Combined Acquisition + Intake Summary
- 12.62.9 Manual Cleanup Step in Ingestion
