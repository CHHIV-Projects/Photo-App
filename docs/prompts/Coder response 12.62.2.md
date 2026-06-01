# Coder Response 12.62.2

## 1. Milestone Title and Date
- Milestone: 12.62.2 iCloud Staging Path Alignment and Cross-Operation Guardrail Planning
- Date: 2026-06-01

## 2. Scope Completed
Completed in this milestone:
- reconnaissance of current iCloud managed staging path generation and acquisition resolver behavior
- analysis of source_root_path vs managed_staging_path identity behavior
- evaluation of alignment strategies and mismatch handling
- analysis of current cross-operation locks and guardrail gaps
- documentation of recommended next milestones and staged implementation approach

Out of scope (intentionally not done):
- no path rewrite implementation
- no acquisition behavior changes
- no source intake behavior changes
- no cleanup behavior changes
- no credential/session changes
- no new orchestration service implementation

## 3. Files Inspected
Backend/API/schema/model/service:
- backend/app/services/icloud_acquisition/execution_service.py
- backend/app/services/admin/source_intake_service.py
- backend/app/services/admin/icloud_staging_cleanup_execution_service.py
- backend/app/services/admin/source_intake_execution_service.py
- backend/app/services/ingestion/ingestion_context_service.py
- backend/app/models/ingestion_source.py
- backend/app/models/icloud_acquisition_run.py
- backend/app/models/source_intake_run.py
- backend/app/models/icloud_staging_cleanup_run.py
- backend/app/api/admin.py
- backend/app/schemas/admin.py

Frontend:
- frontend/src/components/IngestionView.tsx
- frontend/src/components/IcloudAcquisitionCard.tsx
- frontend/src/components/AdminView.tsx
- frontend/src/lib/api.ts
- frontend/src/types/ui-api.ts

Prior milestone docs:
- docs/operations/icloud_source_profile_run_planning_12_62.md
- docs/operations/icloud_session_staging_readiness_ui_12_62_1.md
- docs/prompts/Coder response 12.62.md
- docs/prompts/Coder response 12.62.1.md

## 4. Current Path Generation Findings
Current managed staging path generation:
- backend/app/services/admin/source_intake_service.py computes iCloud managed_staging_path as storage/exports/icloud/<slugified-source-label>
- provider segment is included

Current acquisition staging root generation:
- backend/app/services/icloud_acquisition/execution_service.py resolves path as storage/exports/icloud/<sanitized-source-label>
- provider segment is not included in the resolver result

Current identity behavior:
- source_root_path remains compatibility/identity metadata
- managed_staging_path is the effective operational path for iCloud source profile views
- both can diverge

## 5. Path Mismatch Risk Findings
The main risk is a convention split:
- profile creation defaults point at one path format
- acquisition launch validation expects another path format

Impact:
- profiles can appear ready but fail acquisition launch validation
- profile detail views can show an operational path that does not match acquisition behavior
- source registration matching can fail even when the profile looks structurally correct

## 6. Alignment Strategy Recommendation
Recommended direction:
- eventual operational truth should be Source Profile managed_staging_path
- but transition must be staged carefully to preserve Admin compatibility

Strategy evaluation:
- Option A is smallest change, but keeps acquisition-led path derivation
- Option B is the cleanest long-term model, but needs phased migration and backward compatibility
- Option C is the most complex and risk-prone

Recommendation:
- favor Option B as the long-term architecture
- use a staged migration plan rather than a silent immediate switch

## 7. Existing Profile Mismatch Handling Findings
Deterministic mismatch detection is possible from existing data when comparing:
- managed_staging_path
- expected acquisition path
- approved root membership
- profile status

What is not available from static code inspection:
- the actual count of mismatched profiles in the live database

Recommended policy:
- do not auto-repair referenced profiles
- allow explicit repair later for unreferenced profiles only if a safe path exists
- prefer archive/recreate for referenced profiles unless a safe migration path is proven

## 8. Readiness Validation Findings
Recommended readiness policy for future execution:
- Ready only when active, aligned, approved-root valid, registration matched, and no known auth or active-operation conflict
- Warning for missing staging folder, auth unknown, or no recent acquisition status
- Not Ready for profile inactive, path mismatch, unsafe root, registration mismatch, active conflict, or auth-required state
- Unknown when data is insufficient

Code-based refinement:
- path mismatch and approved-root blocked should stay hard Not Ready
- auth must remain conservative; no Ready state without a deterministic health signal

## 9. Cross-Operation Concurrency Findings
Current locks observed:
- iCloud acquisition has its own single-active lock
- Source Intake has its own single-active lock
- cleanup has its own active lock and blocks source intake on same source

Current gaps:
- acquisition can still overlap with source intake if launched separately
- cleanup can still overlap with acquisition
- different entry points do not share one global unified guardrail

Conclusion:
- existing locks are not sufficient for a future unified Ingestion iCloud workflow

## 10. Guardrail Implementation Findings
Recommended staged guardrail approach:
1. UI-only checks for operator feedback
2. backend shared guardrail checks for enforcement
3. orchestration service only after path policy is stable

Reasoning:
- UI-only is too weak on its own
- orchestration is likely too large for the next slice
- backend checks are the right enforcement layer once the canonical path policy is decided

## 11. Admin Compatibility Findings
Admin should remain unchanged as a diagnostic/legacy surface during migration.

Recommended compatibility policy:
- do not break Admin behavior while path alignment is being stabilized
- preserve backward compatibility when introducing canonical path changes
- allow Ingestion to move toward source-profile-aware operation without removing Admin controls

## 12. Recommended Implementation Sequence
Refined sequence:
1. 12.62.3 iCloud Path Canonicalization Foundation
2. 12.62.4 iCloud Readiness Validation Endpoint
3. 12.62.5 Cross-Operation Guardrails
4. 12.62.6 Acquire from iCloud in Ingestion
5. 12.62.7 Guided Source Intake Handoff
6. 12.62.8 Combined Acquisition + Intake Summary
7. 12.62.9 Manual Cleanup Step in Ingestion

## 13. Safety Confirmation
Confirmed:
- no runtime behavior changed in 12.62.2
- documentation-only milestone output

## 14. Deviations from Prompt
- No deviations from the reconnaissance-only intent.
- Actual live mismatch counts were not computed because that requires database inspection, not static code reading.

## 15. Known Limitations
- the exact number of mismatched profiles is unknown from code inspection alone
- readiness and guardrails remain conceptual until a canonical path policy is implemented
- no backend readiness endpoint was added in this milestone

## 16. Recommended Next Milestone
- 12.62.3 iCloud Path Canonicalization Foundation

Open questions to resolve before coding:
- Should the canonical iCloud staging path be provider-segmented or slug-only?
- Should acquisition continue to derive path from label during transition, or should it resolve managed_staging_path once canonicalization lands?
- Should the first enforcement change be UI guardrails, backend guardrails, or both together?
