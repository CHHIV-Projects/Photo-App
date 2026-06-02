# Coder Response 12.62.6 (Implementation Closeout)

## 1. Milestone
12.62.6 — Acquire from iCloud in Ingestion Tab

## 2. Summary of Work Completed
Completed:

1. Added Ingestion-specific iCloud acquisition flow in Source Profile Details drawer.
2. Added acquisition confirmation dialog with Recent Count and Acquisition Mode options.
3. Implemented on-demand includeUsername=true fetch at Acquire click to retrieve real account username for payload.
4. Kept username display masked in drawer/confirmation while using real username internally for launch payload.
5. Implemented readiness/guardrail gating based on backend snapshot.
6. Added acquisition status polling and run summary display in Ingestion drawer.
7. Added Request Stop action via existing stop endpoint.
8. Added terminal-state operator guidance messages.
9. Added acquisition-specific structured 409 payload parsing support in frontend API helper.
10. Removed Total Limit and Batch Size from Create Source Profile flow.

## 3. Files Modified
1. frontend/src/components/IngestionView.tsx
2. frontend/src/lib/api.ts
3. docs/operations/acquire_from_icloud_in_ingestion_tab_12_62_6.md
4. docs/prompts/Coder response 12.62.6.md

## 4. Key Implementation Notes
1. Ingestion acquisition state machine is independent from Admin component state.
2. Existing Admin acquisition UI component was not reused directly.
3. Existing backend acquisition endpoints and status semantics were reused.
4. Structured guardrail details are preserved for acquisition start errors with low-risk, acquisition-focused parsing.
5. Readiness remains backend-authoritative and action gating is conservative.

## 5. Validation
Passed:

1. frontend: npm run build

Result:

1. Next.js compile, lint, and type validation passed.

## 6. Boundaries Preserved
Not changed:

1. No automatic Source Intake handoff/run
2. No cleanup run behavior from Ingestion acquisition flow
3. No credential/password/2FA/session storage additions
4. No backend acquisition semantics changes
5. No Admin iCloud component behavior changes

## 7. Parking-Lot Note
EXT-001 — External Drive Identity Should Be Device-Based, Not Drive-Letter-Based (documented only; no implementation in this milestone).
