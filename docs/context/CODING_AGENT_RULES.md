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

- clean git history

- consistent prompt and closeout naming

- cost-aware coding-agent usage

Milestone prompts may reference this file instead of repeating every project rule.

This file is not a replacement for:

- milestone prompts

- codebase reconnaissance

- user/product-owner decisions

- validation

- closeout documentation

Use repository files as the source of truth. Do not rely on chat memory alone.

---

## 1. How to Use This File

For every coding task:

1. Read this file first.

2. Read the milestone prompt.

3. Perform git preflight before coding.

4. Inspect the relevant code paths before changing code.

5. Ask clarification questions before uncertain or risky changes.

6. Implement only the approved milestone scope.

7. Validate the change.

8. Create exactly one closeout document using the filename specified in the prompt.

Do not assume prior chat context is complete or current.

Do not implement based on memory if repository files, prompts, closeouts, or current code contradict memory.

---

## 2. Context Reading Rules

To reduce cost and avoid unnecessary context loading:

### Always Read

- the current milestone prompt

- this file: `docs/context/CODING_AGENT_RULES.md`

### Read When Needed

Read broader project documents only when the milestone requires broader context or when codebase behavior is unclear:

```text
docs/context/PROJECT_CONTEXT.md
docs/context/PROJECT_ARCHITECTURE.md
docs/context/ARCHITECTURE_ROADMAP.md
docs/context/PROJECT_WORKFLOW.md
docs/context/MILESTONE_HISTORY.md
Parking Lot documents
prior milestone prompt and closeout files related to the same feature area
```

### Do Not Automatically Read Everything

Do not repeatedly read all project context documents for small scoped changes.

For most milestones, start with:

```text
1. CODING_AGENT_RULES.md
2. current milestone prompt
3. relevant source files and tests
4. specific prior closeouts only if needed
```

For high-risk milestones involving ingestion, cleanup, provenance, Vault behavior, cloud acquisition, source identity, credentials, migrations, or destructive behavior, read the relevant architecture/context sections before coding.

---

## 3. Git / Working Tree Rules

### Git Preflight Required

Before coding, report:

```powershell
git branch --show-current
git status --short
git log --oneline --decorate -5
```

Expected normal state:

```text
correct branch
working tree clean
active prompt already committed
```

Allowed exception:

```text
only the active milestone prompt is modified with expected Q&A/addenda
```

If unexpected dirty files exist, stop before coding and classify them.

---

### Dirty-Tree Classification

If the working tree is dirty before coding, do not assume the dirty files belong to the current milestone.

Classify each dirty file as:

```text
A. required prior-milestone follow-up/fix
B. unrelated work
C. accidental/noise
D. required for the current milestone
```

Report the classification and a brief diff summary.

Do not edit, revert, stage, stash, commit, or delete dirty files unless explicitly authorized.

Purpose:

- avoid mixed commits

- prevent unrelated changes from entering a milestone

- catch unfinished prior work

- make git history reviewable

- preserve user trust

---

### Git Write Commands

Do not run any of these unless explicitly authorized:

```text
git commit
git push
git reset
git rebase
git merge
git tag
git checkout
git switch
git stash
git clean
```

Read-only git commands are allowed and expected for reconnaissance:

```text
git status
git diff
git diff --name-only
git diff --stat
git log
git branch
```

If a prompt says “do not run git write commands,” obey it.

---

### Specific-File Staging Standard

Milestone commits should stage specific files, not blindly stage everything.

Avoid:

```powershell
git add .
```

unless the User has reviewed the full dirty tree and explicitly approves staging all changes.

When asked to provide or prepare commit guidance, use:

```powershell
git status --short
git diff --name-only
git diff --stat

git add <specific file>
git add <specific file>

git diff --cached --name-only
git diff --cached --stat
```

Do not mix unrelated systems in one commit simply because they are dirty at the same time.

---

## 4. Prompt and Closeout Filename Rules

### Prompt Filename Authority

The milestone prompt is the authority for:

- prompt filename

- closeout filename

- milestone number

- milestone title

- deliverables

Every prompt should include exact file names.

Use this pattern:

```text
<milestone>_<exact_snake_case_name>_prompt.md
<milestone>_<exact_snake_case_name>_closeout.md
```

Example:

```text
12.75.0_source_identity_workflow_alignment_prompt.md
12.75.0_source_identity_workflow_alignment_closeout.md
```

Rules:

- do not invent a different closeout filename

- use the same basename as the prompt

- replace `_prompt.md` with `_closeout.md`

- do not create a separate report file unless explicitly requested

- do not rename files for convenience

---

### Milestone Arc Numbering

A new milestone arc normally starts at:

```text
xx.xx.0
```

Follow-up prompts, subprompts, and approved secondary actions increment:

```text
xx.xx.1
xx.xx.2
xx.xx.3
```

Do not change milestone numbering conventions unless the prompt explicitly says so.

---

### Prompt Addenda / Q&A

Prompt Q&A, addenda, and final lock-ins should be appended to the same prompt file when the User requests that the prompt record be updated.

Recommended headings:

```markdown
## Original Prompt

## Coder Questions / Answers Round 1

## Coder Questions / Answers Round 2

## Final Lock-ins
```

A prompt file may be modified during active implementation if:

- the initial prompt was already committed before handoff

- the only dirty file is the active prompt

- the User confirms the modification is expected

Do not require a new git commit after every minor prompt addendum.

However, stop and ask if prompt addenda materially change:

- milestone scope

- safety boundaries

- live operation approval

- cleanup or destructive behavior

- Vault behavior

- source identity or provenance semantics

- schema/migration/backfill behavior

- credential/session handling

- prompt filename or closeout filename

- implementation direction after a major clarification

---

## 5. Core Architecture Rules

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

Do not write directly to Vault from cloud acquisition, external scanning, preview, or helper code unless the milestone explicitly changes the ingestion architecture.

### Source Intake Rule

Source Intake remains the ingestion authority.

Only Source Intake may move files into the ingestion path and create durable asset/provenance records.

Do not bypass Source Intake to create asset, provenance, canonical metadata, or Vault records.

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

- remote cloud data

- Vault files

- DB asset records

- provenance records

- Source Profile records

- source registry / ingestion source history

Cleanup must be bounded, verified, and reportable.

### Provenance Rule

Provenance must be preserved.

Do not delete or overwrite provenance history unless a milestone explicitly scopes a safe migration or correction.

Provenance must remain explainable after ingestion, dedupe, source-profile changes, cleanup, or canonicalization.

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

## 6. Scope Discipline Rules

Implement only the approved milestone scope.

Do not perform unrelated refactors.

Do not perform speculative architecture changes.

Do not fix unrelated UI polish, typing, formatting, naming, or performance issues unless required for the milestone.

Do not change public concepts, API shapes, database models, workflows, or source identity semantics unless the milestone explicitly requires it.

If unrelated issues are discovered, document them in the closeout under Known Limitations or Recommended Next Milestone.

Prefer small, targeted changes over broad rewrites.

If a small follow-up fix is discovered during validation, keep it clearly tied to the milestone or split it into a separate follow-up commit/milestone.

---

## 7. Reconnaissance Rules

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

- long-running background/durable routines

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

8. dirty-tree classification, if applicable

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

## 8. Stop Conditions

Stop and ask before coding if:

- the requested behavior conflicts with this rules document

- the working tree contains unexpected dirty files

- safety verification cannot be proven

- cleanup might affect anything outside verified local staging

- cloud acquisition would write directly into Vault, DB, Drop Zone, or provenance

- Source Intake would be bypassed

- the codebase structure differs materially from the prompt

- implementation requires a migration not mentioned in the prompt

- implementation requires deleting records or files not explicitly scoped

- source identity semantics need to change

- local/external workflows might be broken by an iCloud-specific change

- iCloud workflows might be broken by a local/external-specific change

- secrets or credentials might be exposed, logged, or stored

- the milestone requires broad refactoring

- multiple plausible implementations exist and the product decision matters

- the prompt filename or closeout filename is unclear

- a separate report file seems necessary but was not explicitly requested

Do not guess on safety-sensitive behavior.

---

## 9. File and Data Safety

Before changing code that deletes, moves, rewrites, hides, demotes, imports, or cleans data, identify:

- what exact files/records can be affected

- what verification protects them

- whether the operation is reversible

- whether the operation is local-only or external/cloud-facing

- how the operator confirms the action

- where the action is logged/reported

- how existing provenance remains explainable

- how failure or interruption is handled

For destructive or cleanup actions, prefer:

```text
dry run
explicit confirmation
bounded scope
positive verification
report output
clear skipped/protected counts
resumable or reviewable failure states
```

---

## 10. Source Profile / Ingestion Rules

Source Profiles are the user-facing source concept.

Backend source registry / ingestion-source records may still exist as compatibility and identity layers.

When working on Source Profiles:

- preserve stable source identity

- do not confuse display label with canonical internal identity

- do not treat drive letter as durable external-drive identity

- preserve source history

- keep archived/inactive sources explainable in provenance

- prevent wrong-profile/wrong-path operations

- make local, external, NAS/network, and cloud workflows coexist safely

- distinguish user-facing aliases from machine-readable identity

Local/external/cloud workflows may differ internally, but they should not pollute each other.

Future source identity work should prefer stable identifiers where available, such as:

```text
device serial
VID/PID
volume serial number
filesystem UUID
network share/server identity
NAS/share identity
observed mount/path history
human alias as display name
```

Drive letters and transient mount paths are observations, not durable identity.

---

## 11. iCloud Rules

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

### Unified iCloud Intake Rule

The v1 iCloud operator model is unified iCloud Intake:

```text
Refresh / Prepare Next 1000
Import Next 1000
```

Refresh prepares the exact candidate set.

Import consumes that exact prepared set.

Long-running imports should use durable chunked run/resume behavior, not one fragile synchronous request.

Top-level UI should focus on:

```text
Source Profile
Total Imported from Source
Last Inventory Refresh
Available Inventory
Logical Candidates Ready
Current/Last Run Summary
Next Safe Action
Advanced Details
```

Historical totals, raw run IDs, cleanup internals, and provider diagnostics should normally live in Advanced Details.

---

## 12. UI / UX Rules

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

- historical accounting totals

- cleanup counters

- low-level timing details

Readiness should generally be user-facing and clear:

```text
Ready
Blocked
Available
Unavailable
Unknown
Resume Available
Needs Review
```

Warnings should either be:

- automatically handled

- converted into blockers

- or moved to Advanced Details

Avoid stale or contradictory “next step” messages.

---

## 13. Runtime / Deployment Rules

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

## 14. Testing and Validation Rules

Run the most relevant validation available for the milestone.

Validation may include:

- unit tests

- backend API tests

- frontend type checks/builds

- targeted manual workflow tests

- script dry runs

- DB migration checks

- report/log verification

- UI validation

- live/local workflow validation, only when approved

If a validation step cannot be run, state why.

Do not report a milestone as fully validated if only partial checks were run.

For ingestion/cloud/cleanup/source-identity changes, validation should include local/external regression awareness where applicable.

For long-running routines, validation should consider:

- interruption behavior

- resume behavior

- stale running states

- durable reports

- partial completion

- cleanup safety

- user-visible progress

---

## 15. Closeout Requirement

Create exactly one human-authored closeout document per milestone/action.

Do not create separate:

```text
report.md
operations.md
coder_response.md
```

unless explicitly requested.

The closeout filename must be the exact filename specified in the prompt.

The closeout must use the same basename as the prompt, replacing:

```text
_prompt.md
```

with:

```text
_closeout.md
```

Application-generated runtime reports are allowed, for example:

```text
JSON run reports
cleanup reports
intake reports
logs
diagnostic exports
screenshots
```

These are runtime artifacts, not human-authored milestone report files. Reference them from the closeout when relevant.

---

### Required Closeout Structure

Use this structure unless the milestone prompt explicitly modifies it:

```markdown
# Milestone <number> — <title>

## 1. Scope Completed
What was implemented.

## 2. Operational Behavior
How the feature now works from a user/operator perspective.

## 3. Files Changed
Modified/added/deleted files.

## 4. API / Data Model Changes
Only if applicable.

## 5. Safety Boundaries Preserved
What was intentionally not changed.

## 6. Validation Performed
Tests/builds/manual checks run and results.

## 7. User / Live Validation
If applicable, what the User tested after implementation.

## 8. Deviations from Prompt
Anything not done, changed, or interpreted differently.

## 9. Known Limitations
Known issues or deferred work.

## 10. Recommended Next Milestone
Next step.

## 11. Git Status
git status --short and relevant diff summary at closeout time.
```

The closeout must report deviations clearly.

If the closeout includes post-closeout live validation, append it to the same closeout file rather than creating a separate report.

---

## 16. Cost-Aware Agent Behavior

Minimize unnecessary agent cost by avoiding broad wandering.

Do:

- start with likely relevant files

- inspect targeted code paths first

- summarize findings before broad searches

- ask focused questions when blocked

- keep changes narrowly scoped

- report unrelated findings instead of fixing them

- avoid repeated repo-wide scans

- use reconnaissance-first when risk is high

- keep durable rules in this document rather than repeating them in every prompt

Do not:

- read every project document for every small task

- repeatedly search the whole repository without a reason

- rewrite unrelated systems

- make speculative improvements

- continue coding after hitting a stop condition

- fix unrelated issues just because they are nearby

For complex milestones, reconnaissance-first usually saves cost by preventing wrong implementation.

---

## 17. Prompt Compliance

When a milestone prompt conflicts with this file:

1. Follow the stricter safety rule.

2. Ask for clarification.

3. Do not proceed with risky implementation until clarified.

When the prompt explicitly overrides a rule, the closeout must document:

- what rule was overridden

- why it was in scope

- what safety measures were used

- how validation was performed

If the prompt lacks required file names, ask for clarification before creating a closeout.

If the prompt requests multiple closeout/report documents, ask for confirmation unless explicitly required by the User.

---

## 18. Performance Awareness

Milestones should consider:

- ingestion time

- query efficiency

- background processing impact

- UI responsiveness

- scalability with large photo libraries

- disk/network implications for NAS/external/cloud workflows

Expensive operations should be identified explicitly and may be candidates for background processing or Parking Lot.

Examples:

- duplicate lineage

- face processing

- visual enrichment

- iCloud acquisition

- Source Intake

- cleanup scans

- external drive/NAS scanning

- AI model inference

Do not optimize speculatively unless performance work is explicitly in scope.

When performance is observed but not in scope, document it under Known Limitations or Recommended Next Milestone.

---

## 19. Documentation Discipline

Milestone prompt and closeout files are the primary detailed record for each action.

Global documents should reflect current system state and workflow, not every implementation detail.

Update global documents when a milestone changes:

- architecture

- workflow

- source identity

- ingestion model

- safety model

- deployment/runtime model

- major user-facing behavior

- milestone process

Do not create new documentation patterns without approval.

Do not create high-noise conversational artifacts such as `Coder response*.md` for new milestones unless explicitly requested.

---

## 20. Success Criteria

A coding-agent session is successful when:

- the approved milestone scope is implemented

- unrelated systems are not changed

- unexpected dirty files are identified before coding

- core safety boundaries are preserved

- the implementation is validated

- limitations are documented

- exactly one closeout document is created

- the closeout uses the exact filename specified in the prompt

- future work is identified without expanding current scope

- project state remains understandable and portable

- git history can be reviewed by logical change group

- the User can confidently test, commit, and continue
