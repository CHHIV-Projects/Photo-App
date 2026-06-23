# Photo Organizer — New Chat Intro for Coder v4

## Purpose

This document starts a new coding-assistant session for the **Photo Organizer** project.

You are being asked to help implement tightly scoped milestones in an existing codebase. This document is brand-agnostic and applies to any coding assistant, IDE agent, or implementation collaborator.

Use the attached project documents as the current source of truth:

```text
PROJECT_CONTEXT_v4.md
PROJECT_ARCHITECTURE_v4.md
PROJECT_WORKFLOW_v4.md
MILESTONE_HISTORY_v4.md
Parking_Lot_v4.md
CODING_AGENT_RULES.md
```

When working on a specific milestone, also review the current milestone prompt and any relevant prior closeout files.

---

## Your Role

You are the implementation partner.

Your responsibilities are to:

- inspect the existing codebase before making changes
- identify relevant files, models, services, API routes, UI components, and tests
- ask clarification questions before coding uncertain behavior
- implement only the approved milestone scope
- avoid speculative improvements
- preserve existing behavior outside the milestone
- validate your changes locally where possible
- create exactly one closeout document for the milestone

You should not redesign broad architecture unless the milestone explicitly asks for design/reconnaissance.

---

## Project Owner Workflow

The project owner uses a milestone-driven workflow.

The owner will provide:

- a milestone prompt
- clarification answers, if needed
- product decisions
- local test feedback
- screenshots, logs, and issue reports

You should:

- read the milestone prompt carefully
- perform codebase reconnaissance before coding if the change is complex
- ask focused questions if anything is unclear
- wait for lock-ins before implementing ambiguous behavior
- keep implementation tightly scoped

---

## Current Project State

Photo Organizer is a working local-first photo intelligence and archival platform.

It includes:

- Source Profiles for local, external, and cloud-staged sources
- Ingestion-tab Source Profile workflows
- local/external Source Intake
- guided iCloud acquisition using `icloudpd`
- iCloud acquisition-to-Source-Intake handoff
- iCloud workflow summary
- iCloud cleanup dry-run readiness/evaluation
- Source Profile lifecycle/status foundation
- exact deduplication into canonical Vault storage
- provenance tracking
- metadata observation and canonicalization
- face detection, clustering, assignment, and reassignment workflows
- people/person identity workflows
- event, album, collection, source-review, and place/location systems
- display-safe preview generation for HEIC/HEIF/TIFF/content-mismatch cases
- Live Photo pairing
- video metadata trust handling
- visual enrichment workspace and asset context label foundation
- Admin/background job controls and JSON operational reports

The current focus is ingestion confidence and simplification, not broad new feature expansion.

---

## Most Recent State

Recent 12.62 work validated the guided iCloud Source Profile workflow:

- Source Profile creation works.
- iCloud managed staging readiness works.
- `icloudpd` acquisition from the Ingestion tab works.
- Source Intake handoff for acquired iCloud files works.
- Cleanup Dry Run works and reports eligible staged files.
- Local Source Profile intake still works.
- A source registration / launch path mismatch was fixed in 12.62.10.1.
- HEIC display works after display-safe/review processing is run.
- BMP display-preview support remains a future item.
- A Windows/Docker/WSL ghost listener issue on port 8001 was observed and is a later runtime-hardening item.

---

## Current Near-Term Priority

The project owner wants to finish ingestion confidence before returning to broader curation systems.

Near-term sequence:

```text
1. Real iCloud staging cleanup execution, not just dry run.
2. Cleanup → reacquire → non-repeat validation.
3. Consolidate cloud ingestion steps.
4. Simplify Source Profile / Ingestion tab UX.
5. Make external imports agnostic to drive assignment.
6. Then later revisit people, source review, timeline/events, places, visual enrichment, and assigning places to non-geolocated assets.
```

Do not jump ahead to later curation/enrichment work unless explicitly asked.

---

## Critical Architecture Rules

These rules must be preserved:

```text
Acquisition acquires.
Source Intake ingests.
Vault preserves.
DB/provenance explain.
Cleanup only acts on verified local staging.
```

More specifically:

- Source Intake is the only path into Drop Zone, Vault, DB asset records, and provenance.
- iCloud acquisition must write only to managed staging under `storage/exports/icloud/<profile_slug>/`.
- Cloud acquisition must never write directly to Vault, DB, Drop Zone, or provenance.
- Cleanup must never delete iCloud cloud-library data.
- Cleanup must never delete Vault files.
- Cleanup must never delete DB records.
- Cleanup must never delete provenance.
- Cleanup must never delete Source Profile/source registry rows.
- The application must not store Apple passwords, 2FA codes, session cookies, or auth tokens.
- AI/provider outputs are evidence, not canonical truth.
- User corrections and manual decisions are authoritative.
- Workflows should remain local-first and non-destructive by default.

If your implementation conflicts with one of these rules, stop and ask before coding.

---

## Implementation Expectations

Before coding:

1. Inspect the existing implementation.
2. Identify the relevant backend and frontend code paths.
3. Check whether a migration is required.
4. Check whether existing tests cover the affected behavior.
5. Identify risk of breaking local/external Source Intake while changing iCloud behavior.
6. Ask clarification questions if the prompt and codebase disagree.

While coding:

- keep changes minimal and scoped
- avoid broad refactors unless requested
- do not rename public concepts casually
- preserve current APIs unless the prompt requires changes
- preserve existing local/external workflows when modifying cloud workflows
- preserve safety guards and add tests where practical
- write clear error messages and operator-facing status text

After coding:

- run relevant backend tests
- run relevant frontend build/type checks where practical
- validate the workflow manually if possible
- document anything not tested

---

## Documentation Requirement

Create **one closeout document only** for each milestone.

Do not create separate operations documents and coder-response documents unless explicitly requested.

Use this closeout structure:

```markdown
# Milestone <number> — <title>

## 1. Scope Completed
What was implemented.

## 2. Operational Behavior
How the feature now works from a user/operator perspective.

## 3. Files Changed
Modified/added files.

## 4. API / Data Model Changes
Only if applicable.

## 5. Safety Boundaries Preserved
What was intentionally not changed.

## 6. Validation Performed
Tests/builds run and results.

## 7. Deviations from Prompt
Anything not done or changed.

## 8. Known Limitations
Known issues or deferred work.

## 9. Recommended Next Milestone
Next step.
```

Recommended location/pattern will be specified in each milestone prompt.

---

## Expected Style of Clarification Questions

Ask targeted questions such as:

- Which existing service owns this behavior?
- Should this be implemented in backend only or backend + UI?
- Should this be a migration or forward-only behavior?
- What should happen to existing historical records?
- What is the exact safety behavior for edge cases?
- Should this be visible to normal users or Advanced/Admin only?
- Which tests are expected?

Avoid broad, vague questions such as:

```text
What do you want me to do?
Should I improve the UI?
Should I refactor this?
```

---

## Current Likely Next Milestone

The likely next milestone is:

```text
12.62.11 — Verified iCloud Staging Cleanup Execution
```

Expected theme:

Turn the existing cleanup dry-run capability into a real, explicitly confirmed cleanup execution path for verified local iCloud staging files.

Likely safety requirement:

```text
Delete local staged iCloud files only after verification.
Never delete iCloud cloud files.
Never delete Vault files.
Never delete DB records.
Never delete provenance.
```

Do not implement this until you receive the full milestone prompt.

---

## Success Criteria

A milestone is successful when:

- scope is implemented exactly as requested
- safety boundaries are preserved
- existing local/external ingestion still works
- iCloud-specific behavior does not leak into unrelated workflows
- validation is clear
- any limitations are documented
- one closeout document is created
