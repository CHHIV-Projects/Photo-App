# CODING_AGENT_RULES.md — Photo Organizer

## Purpose

This document defines standing rules for AI coding agents working on the Photo Organizer codebase.

It exists to reduce repeated prompt boilerplate while preserving:

- safety
- architecture discipline
- local-first data handling
- milestone quality
- clean implementation scope
- durable documentation

Milestone prompts may reference this file instead of repeating every project rule.

This file is not a replacement for milestone prompts, codebase reconnaissance, validation, or closeout documentation.

---

## 1. How to Use This File

For every coding task:

1. Read this file first.
2. Read the milestone prompt.
3. Inspect the relevant code paths before changing code.
4. Ask clarification questions before uncertain or risky changes.
5. Implement only the approved milestone scope.
6. Validate the change.
7. Create exactly one closeout document.

Do not rely on chat memory alone.

Use repository files as the source of truth.

---

## 2. Context Reading Rules

To reduce cost and avoid unnecessary context loading:

### Always Read

- the current milestone prompt
- this file: `docs/context/CODING_AGENT_RULES.md`

### Read When Needed

Read these broader project documents only when the milestone requires broader context or when codebase behavior is unclear:

- `docs/context/PROJECT_CONTEXT.md`
- `docs/context/PROJECT_ARCHITECTURE.md`
- `docs/context/PROJECT_WORKFLOW.md`
- `docs/context/MILESTONE_HISTORY.md`
- Parking Lot documents
- prior milestone prompt and closeout files related to the same feature area

### Do Not Automatically Read Everything

Do not repeatedly read all project context documents for small scoped changes.

For most milestones, start with:

```text
1. CODING_AGENT_RULES.md
2. the milestone prompt
3. relevant source files and tests
4. specific prior closeouts only if needed
```

For high-risk milestones involving ingestion, cleanup, provenance, Vault behavior, cloud acquisition, source identity, credentials, or migrations, read the relevant architecture/context sections before coding.

---

## 3. Core Architecture Rules

These rules are mandatory unless a milestone explicitly changes them.

### Local-First Rule

Photo Organizer is a local-first archival system.

Cloud services may be acquisition sources, but they are not the system of record.

### Original Media Preservation

Original media files must be preserved.

Do not modify original media files in place.

### Vault Rule

The Vault is durable archival storage.

Treat Vault contents as immutable unless a milestone explicitly defines a safe, reviewed Vault operation.

### Source Intake Rule

Source Intake remains the ingestion authority.

Only Source Intake may move files into the ingestion path and create durable asset/provenance records.

### Cloud Acquisition Boundary

Cloud acquisition is staging only.

Cloud acquisition may download files into a managed staging/export folder, but it must not directly write to:

- Vault
- Drop Zone
- asset DB records
- provenance records
- canonical metadata records

### iCloud Staging Rule

iCloud acquisition must write only to the selected Source Profile’s managed staging path, normally under:

```text
storage/exports/icloud/<profile_slug>/
```

### Cleanup Rule

Cleanup may act only on verified local staging files.

Cleanup must never delete:

- iCloud cloud-library data
- Vault files
- DB asset records
- provenance records
- Source Profile records
- source registry / ingestion source history

### Provenance Rule

Provenance must be preserved.

Do not delete or overwrite provenance history unless a milestone explicitly scopes a safe migration or correction.

### User Authority Rule

User decisions override automation.

Do not silently undo:

- person assignments
- face reassignments
- duplicate adjudication decisions
- demotion/restore decisions
- place corrections
- date trust overrides
- accepted/rejected AI/provider suggestions

### AI / Provider Evidence Rule

AI, computer vision, geocoding, cloud-provider, or metadata-provider output is evidence, not truth.

Do not automatically promote provider output to canonical truth unless the milestone explicitly defines reviewed, safe behavior.

### Credential Safety Rule

The application must not store:

- Apple ID passwords
- 2FA codes
- session cookies
- auth tokens
- secrets
- credentials in logs
- credentials in DB records
- credentials in source-controlled files

`icloudpd` may own its own external/session mechanism. Photo Organizer may report non-secret session status only if safely available.

---

## 4. Scope Discipline Rules

Implement only the approved milestone scope.

Do not perform unrelated refactors.

Do not perform speculative architecture changes.

Do not fix unrelated UI polish, typing, formatting, naming, or performance issues unless required for the milestone.

If unrelated issues are discovered, document them in the closeout under Known Limitations or Recommended Next Milestone.

Prefer small, targeted changes over broad rewrites.

Do not change public concepts, API shapes, database models, or workflows unless the milestone explicitly requires it.

---

## 5. Reconnaissance Rules

### Reconnaissance Required

Perform reconnaissance before coding when a milestone touches:

- ingestion
- Source Intake
- Source Profiles
- source identity
- iCloud/cloud acquisition
- cleanup/deletion
- Vault behavior
- provenance
- duplicate canonicalization
- face/person identity behavior
- place/location canonical behavior
- migrations/backfills
- authentication/session behavior
- production/runtime scripts
- broad UI workflows

### Reconnaissance Output

When asked for reconnaissance only, do not edit files.

Report:

1. relevant files/services/routes/components
2. current behavior
3. proposed implementation plan
4. risks and safety concerns
5. migration/backfill needs, if any
6. tests or validation to run
7. clarification questions or blockers

Wait for approval before coding.

### Direct Implementation Allowed

Direct implementation without a separate reconnaissance response is acceptable for low-risk tasks such as:

- copy-only text changes
- small display/UI label changes
- narrow styling fixes
- small tests
- minor non-destructive bug fixes
- documentation-only changes

Even then, inspect the relevant code before changing it.

---

## 6. Stop Conditions

Stop and ask before coding if:

- the requested behavior conflicts with this rules document
- safety verification cannot be proven
- cleanup might affect anything outside local staging
- cloud acquisition would write directly into Vault, DB, Drop Zone, or provenance
- the codebase structure differs materially from the prompt
- implementation requires a migration not mentioned in the prompt
- implementation requires deleting records or files not explicitly scoped
- source identity semantics need to change
- local/external workflows might be broken by an iCloud-specific change
- secrets or credentials might be exposed, logged, or stored
- the milestone requires broad refactoring
- multiple plausible implementations exist and the product decision matters

Do not guess on safety-sensitive behavior.

---

## 7. File and Data Safety

Before changing code that deletes, moves, rewrites, or hides data, identify:

- what exact files/records can be affected
- what verification protects them
- whether the operation is reversible
- whether the operation is local-only or external/cloud-facing
- how the operator confirms the action
- where the action is logged/reported
- how existing provenance remains explainable

For destructive actions, prefer:

```text
dry run
explicit confirmation
bounded scope
positive verification
report output
clear skipped/protected counts
```

---

## 8. Source Profile / Ingestion Rules

Source Profiles are the user-facing source concept.

Backend source registry / ingestion-source records may still exist as compatibility and identity layers.

When working on Source Profiles:

- preserve stable source identity
- do not confuse display label with canonical internal identity
- do not treat drive letter as durable external-drive identity
- preserve source history
- keep archived/inactive sources explainable in provenance
- prevent wrong-profile/wrong-path operations
- make local, external, and cloud workflows coexist safely

Local/external and cloud workflows may differ internally, but they should not pollute each other.

---

## 9. iCloud Rules

When working on iCloud workflows:

- `icloudpd` is the preferred acquisition adapter
- acquisition is staging-only
- Source Intake performs ingestion
- cleanup is local-staging-only
- no Apple credentials or 2FA codes are stored
- account username may be stored as non-secret source metadata
- managed staging path must match the selected Source Profile
- acquisition and intake results must be clearly linked or clearly explained
- non-repeat behavior must not rely only on local staged file existence after cleanup
- cleanup must not cause repeated unnecessary redownload loops without clear reporting

---

## 10. UI / UX Rules

Normal user-facing workflows should avoid exposing backend plumbing unless needed.

Prefer:

```text
Source
Readiness
Action
Progress
Result
Next safe action
Advanced Details
```

Use Advanced Details for:

- canonical paths
- source registry identity
- normalized labels
- provider diagnostics
- run IDs
- technical conflicts
- raw report paths

Readiness should generally be user-facing and binary:

```text
Ready
Blocked
```

Warnings should either be:

- automatically handled
- converted into blockers
- or moved to Advanced Details

Avoid stale or contradictory “next step” messages.

---

## 11. Runtime / Deployment Rules

Preserve Windows development workflow unless a milestone explicitly targets Linux/mini-server deployment.

When changing runtime scripts:

- preserve dev/prod separation
- avoid accidental production data use
- avoid fallback to development storage in production mode
- report occupied ports clearly
- report unresolved/ghost listener conditions clearly
- avoid killing unrelated processes without explicit operator confirmation
- keep startup/shutdown behavior understandable for a non-programmer operator

For future mini-server work:

```text
Mini server = compute/runtime/web/AI host
NAS = durable media storage and backup layer
```

Do not assume NAS should host live database files on a mapped share unless explicitly validated.

---

## 12. Testing and Validation Rules

Run the most relevant validation available for the milestone.

Validation may include:

- unit tests
- backend API tests
- frontend type checks/builds
- targeted manual workflow tests
- script dry runs
- DB migration checks
- report/log verification

If a validation step cannot be run, state why.

Do not report a milestone as fully validated if only partial checks were run.

For ingestion/cloud/cleanup changes, validation should include local/external regression awareness where applicable.

---

## 13. Closeout Requirement

Create exactly one closeout document per milestone/action.

Do not create separate operations documents and coder-response documents unless explicitly requested.

The closeout should use this structure:

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

The closeout must report deviations clearly.

---

## 14. Cost-Aware Agent Behavior

Minimize unnecessary agent cost by avoiding broad wandering.

Do:

- start with likely relevant files
- inspect targeted code paths first
- summarize findings before broad searches
- ask focused questions when blocked
- keep changes narrowly scoped
- report unrelated findings instead of fixing them
- avoid repeated repo-wide scans

Do not:

- read every project document for every small task
- repeatedly search the whole repository without a reason
- rewrite unrelated systems
- make speculative improvements
- continue coding after hitting a stop condition

For complex milestones, reconnaissance-first usually saves cost by preventing wrong implementation.

---

## 15. Prompt Compliance

When a milestone prompt conflicts with this file:

1. Follow the stricter safety rule.
2. Ask for clarification.
3. Do not proceed with risky implementation until clarified.

When the prompt explicitly overrides a rule, the closeout must document:

- what rule was overridden
- why it was in scope
- what safety measures were used
- how validation was performed

---

## 16. Success Criteria

A coding-agent session is successful when:

- the approved milestone scope is implemented
- unrelated systems are not changed
- core safety boundaries are preserved
- the implementation is validated
- limitations are documented
- the closeout is complete
- future work is identified without expanding current scope
- project state remains understandable and portable
