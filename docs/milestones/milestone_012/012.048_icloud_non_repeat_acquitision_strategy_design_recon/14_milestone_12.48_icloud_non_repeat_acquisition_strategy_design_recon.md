```
# Milestone 12.48 — iCloud Non-Repeat Acquisition Strategy Design and Reconnaissance## GoalDetermine the safest Production v1.0 strategy for avoiding repeated iCloud downloads after verified staging cleanup.This is a **design-first / reconnaissance milestone**.Do not implement the full non-repeat acquisition behavior yet unless a tiny, clearly safe diagnostic improvement is needed.This milestone answers:```textHow should Photo Organizer know when iCloud acquisition has already seen/downloaded/ingested recent assets, especially after local staging files have been cleaned up?
```

The output of this milestone should be a concrete implementation recommendation for:

```
12.48.1 — iCloud Non-Repeat Acquisition Implementation
```

---

## Context

Photo Organizer now supports:

- Source Registry
- Source Intake
- Admin-controlled iCloud acquisition through `icloudpd`
- iCloud acquisition staging under `storage/exports/icloud/<source_label>/`
- verified iCloud staging cleanup
- provenance tracking
- Vault-backed canonical asset storage
- non-destructive ingestion
- clean production bootstrap foundation from 12.47

Current iCloud acquisition is safe but still has a production-readiness gap.

The current acquisition model uses fixed recent windows, such as:

```
recent_count = 25
```

This can cause repeated downloads after local staging cleanup because `icloudpd` may skip files only if they still exist in the staging folder.

Production v1.0 needs a safer strategy so the operator does not have to repeatedly download the same recent files or keep increasing `recent_count` to discover whether new iCloud assets exist.

---

## Core Production Rules

Do not violate these:

- Cloud acquisition writes only to local exports/iCloud staging.
- `icloudpd` must not write directly to Drop Zone.
- `icloudpd` must not write directly to Vault.
- `icloudpd` must not write directly to DB/provenance.
- Source Intake remains the only ingestion authority.
- iCloud staging cleanup deletes only verified local staging files.
- Do not delete from iCloud.
- Do not delete from Vault.
- Do not store Apple ID password, 2FA code, session cookies, or auth tokens.
- Account username is non-secret source metadata only.
- One stable iCloud source per iCloud account/library is the v1.0 production rule.
- Operator clarity is more important than hidden automation.

---

## Problem Statement

Fixed-window iCloud acquisition is not enough for Production v1.0.

Current pattern:

```
1. Run iCloud acquisition for recent N items.2. Files download into exports/iCloud staging.3. Source Intake ingests staged files.4. Verified cleanup deletes successfully ingested local staging files.5. Later acquisition runs again with same recent N.6. Since files no longer exist in staging, icloudpd may download the same files again.
```

This creates:

- repeated downloads
- unnecessary bandwidth/IO
- operator confusion
- unclear “caught up” status
- possible false impression that repeated files are new work
- pressure to keep increasing `recent_count`

Production v1.0 needs a strategy to determine when acquisition is likely caught up or when it has only checked a limited recent window.

---

## Key Design Question

The key question is:

```
Can icloudpd's own behavior, especially --until-found or equivalent options, solve this safely for our workflow after local staging cleanup?
```

If yes, define how to use it safely.

If no, define a Photo Organizer-managed strategy such as:

```
recent window + known thresholdprovenance-based known detectioncheckpoint by source/account/date/pathcloud asset ID checkpoint if availablehybrid icloudpd + Photo Organizer known-state logic
```

---

## Important Definitions to Evaluate

This milestone must define what “known” means for iCloud acquisition.

Candidate meanings:

```
file currently exists in staging
```

```
provenance exists for this stable iCloud source and source-relative path
```

```
Asset exists in DB and Vault file exists
```

```
iCloud acquisition run has previously reported/downloaded this item
```

```
cloud-native asset ID was seen before
```

```
filename/date/size combination was seen before
```

The recommendation must distinguish:

```
staged-knowningested-knownvault-verified-knowncloud-seen-known
```

If cloud-native iCloud asset IDs are not available from `icloudpd`, say so clearly and do not invent them.

---

## Scope

### In Scope

This milestone should inspect and document:

- current iCloud acquisition service/wrapper
- current Admin iCloud acquisition endpoints
- current acquisition run model/table, if any
- current acquisition reports
- current staging folder behavior
- current iCloud staging cleanup logic
- current provenance created by Source Intake for iCloud-staged files
- current source registry fields for iCloud sources
- current handling of `account_username`
- current `icloudpd` command construction
- available `icloudpd` options relevant to non-repeat behavior
- whether `icloudpd --until-found` is available in the installed/project-managed version
- whether `--until-found` behavior depends on local files still existing
- whether `icloudpd` exposes useful stable IDs, logs, reports, or metadata for checkpointing
- whether Photo Organizer can determine “already ingested” from DB/provenance/Vault state
- what reporting would be needed for operator trust

### Out of Scope

Do not implement these in 12.48:

- full non-repeat acquisition implementation
- production iCloud acquisition against real account unless explicitly approved
- large iCloud download
- full-library download
- automatic Source Intake after acquisition
- automatic cleanup after intake
- credential/session manager
- password/2FA/session storage
- multi-iCloud account support
- cloud-native provenance schema changes unless only documented
- scheduled unattended acquisition
- Admin UI redesign
- real production ingestion
- deletion from iCloud
- deletion from Vault
- destructive cleanup
- migration of existing iCloud sources

---

## Required Codebase Reconnaissance

Before recommending a strategy, inspect the codebase and document the actual current behavior.

### 1. iCloud Acquisition Service

Inspect the backend service/wrapper that invokes `icloudpd`.

Document:

- service/module names
- command construction path
- allowed flags
- current recent-count behavior
- current output/staging path behavior
- current source label/source ID behavior
- current account username usage
- current report writing behavior
- current run status behavior
- current stop/cancel behavior
- current error handling

Identify whether the service can support `--until-found` or similar without unsafe broad changes.

---

### 2. Admin/API Integration

Inspect current Admin iCloud acquisition endpoints and UI wiring.

Document:

- endpoint names
- request parameters
- current recent count / limit fields
- status endpoint behavior
- report endpoint behavior
- whether Admin can display caught-up / partial / unknown status
- whether Admin currently distinguishes downloaded, skipped, already-known, failed

Do not implement Admin UI changes yet unless documentation-only.

---

### 3. Acquisition Run Model and Reports

Inspect current acquisition run persistence and report output.

Document:

- model/table name, if any
- fields currently stored
- report file location
- report fields
- whether report includes filenames
- whether report includes paths
- whether report includes sizes/dates
- whether report includes skipped-existing count
- whether report includes enough information to compare against DB/provenance
- whether report can support future checkpoint logic

Determine whether 12.48.1 needs a schema/model change or can work with existing run/report structures.

---

### 4. Source Registry and Stable Source Identity

Inspect current source registry handling for iCloud.

Document:

- how iCloud source is represented
- source label
- source type
- source root path
- account username
- active/inactive status if any
- whether multiple iCloud test sources exist
- how Source Intake associates staged files with source identity

Confirm the v1.0 rule:

```
one stable iCloud source per iCloud account/library
```

Do not implement archive/inactive source lifecycle in this milestone.

---

### 5. Provenance and Known-State Detection

Inspect how Source Intake records provenance for iCloud-staged files.

Document:

- provenance table/model names
- fields available for source identity
- source-relative path
- asset SHA
- ingestion run link
- vault path or asset link
- whether cleaned staging files can still be recognized as already ingested
- whether known-state can be derived from provenance + asset + vault evidence

The strategy should prefer durable DB/provenance/Vault evidence over local staging existence alone.

---

### 6. iCloud Staging Cleanup

Inspect current cleanup logic.

Document:

- dry-run behavior
- execute behavior
- eligibility criteria
- provenance + asset + vault verification rules
- report output
- whether cleanup records can help future acquisition avoid redownloads
- whether cleanup removes only local staging files

Confirm cleanup remains local-only and non-destructive.

---

### 7. `icloudpd` Capability Check

Inspect installed/project-managed `icloudpd` version and help output if practical.

Document:

- installed version
- whether `--until-found` exists
- exact semantics from help text or docs available locally
- whether it works with recent download mode
- whether it depends on files already existing locally
- whether it supports dry-run/list-only behavior
- whether it has logs/database/checkpoint state
- whether it can expose stable iCloud asset identifiers
- whether it has flags affecting Live Photos, videos, originals, or folder layout

Do not run a large download.

If any command is run, use safe help/version/list-only commands only unless user approval is obtained.

---

## Design Options to Evaluate

Evaluate at least the following options.

---

## Option A — Use `icloudpd --until-found` Directly

Description:

```
Use icloudpd's built-in until-found behavior to stop acquisition after known/existing files are encountered.
```

Evaluate:

- Does it exist in the installed version?
- What does “found” mean?
- Does it mean file exists in local download directory?
- Does it still work after Photo Organizer cleanup deletes local staging files?
- Can it distinguish already-ingested from merely locally present?
- How does it behave with Live Photos?
- How does it behave with videos?
- How does it behave with folder structure changes?
- Can Admin report its result clearly?

Risk:

```
If --until-found only checks local staging existence, it may not solve the cleanup/redownload problem.
```

---

## Option B — Recent Window + Provenance Known Threshold

Description:

```
Request a recent window from icloudpd, then use Photo Organizer DB/provenance/Vault state to determine how many acquired/listed items are already known.
```

Possible rule:

```
Continue checking/downloading recent items until N consecutive already-known items are observed.
```

Evaluate:

- Can current reports provide enough item identity to compare against provenance?
- Can file path/name/date/size be matched safely?
- Is there a way to avoid downloading bytes before checking known state?
- Does this require inventory/list capability?
- What threshold is safe for v1.0?
- What should Admin report?

Risk:

```
If known detection depends only on filename, collisions or edits may cause ambiguity.
```

---

## Option C — Photo Organizer Acquisition Checkpoint

Description:

```
Persist acquisition checkpoint state per stable iCloud source.
```

Possible checkpoint fields:

- last acquisition run ID
- last checked date range
- newest seen timestamp
- oldest checked timestamp
- consecutive known count
- filenames or remote identifiers seen
- report path
- account username/source label

Evaluate:

- What durable ID can be stored?
- Is cloud asset ID available?
- If no cloud ID is available, is filename/path/date/size enough?
- How does cleanup interact with checkpoint?
- How does this recover from renamed files or changed folder structure?
- Is this too large for v1.0?

Risk:

```
A weak checkpoint can provide false confidence.
```

---

## Option D — Hybrid Strategy

Description:

```
Use icloudpd capabilities where reliable, but Photo Organizer maintains its own known-state and reporting layer.
```

Possible v1.0 direction:

```
icloudpd handles safe download/acquisition.Photo Organizer determines known/ingested/caught-up status from provenance + asset + vault + reports.
```

Evaluate:

- What is the smallest reliable hybrid?
- Can this be implemented in 12.48.1 without broad schema churn?
- Does this produce clear operator status?
- Does this avoid repeat downloads enough for v1.0?

---

## Required Output: Strategy Recommendation

The main deliverable is a written recommendation.

Create or update:

```
docs/operations/icloud_non_repeat_acquisition_strategy.md
```

If another operations doc convention exists, follow it.

The strategy document must include:

1. Current behavior summary
2. Problem statement
3. Current code paths inspected
4. Current `icloudpd` capabilities
5. Whether `--until-found` is usable
6. Definition of known-state
7. Comparison of Options A/B/C/D
8. Recommended v1.0 strategy
9. Required implementation steps for 12.48.1
10. Required reporting changes
11. Required validation plan
12. Safety constraints
13. Explicit deferrals

---

## Required Recommendation Format

The recommendation should explicitly say one of:

```
Use icloudpd --until-found directly.
```

or:

```
Do not rely on icloudpd --until-found alone; implement Photo Organizer known-state logic.
```

or:

```
Use a hybrid approach: icloudpd for acquisition, Photo Organizer for known-state/caught-up reporting.
```

If the answer is uncertain, say exactly what evidence is missing and what safe diagnostic test is needed.

Do not present uncertainty as a completed decision.

---

## Operator Reporting Requirements

The future implementation should allow Admin/reporting to distinguish:

```
downloaded_newalready_stagedalready_ingestedalready_in_vaultskipped_existingfailedunknown_identitypartial_window_checkedlikely_caught_upnot_enough_evidence
```

12.48 does not need to implement all reporting, but the strategy must define which statuses are needed for v1.0.

At minimum, the recommended 12.48.1 design should support:

```
downloadedskipped_existingalready_knownfailedcaught_up_status
```

Where caught-up status is one of:

```
likely_caught_uppartial_window_onlyunknown
```

---

## Validation Plan Required

Define a safe validation plan for 12.48.1 or 12.48.2.

Validation should include:

### Safe Test Dataset

Use a small controlled recent acquisition window.

Recommended:

```
recent_count <= 25
```

or smaller if sufficient.

Do not run full-library downloads.

### Repeat-Run Scenario

Validate:

```
Run 1:  acquire recent items into stagingRun 2:  repeat acquisition without cleanup  confirm existing/staged behaviorSource Intake:  ingest staged filesCleanup:  run verified staging cleanupRun 3:  repeat acquisition after cleanup  confirm whether system avoids or clearly identifies repeats
```

### Expected Validation Outputs

Document:

- files downloaded
- files skipped
- files already known
- files cleaned
- repeated files avoided or identified
- operator-visible caught-up status
- report paths

### Safety

Validation must not:

- delete from iCloud
- delete from Vault
- reset DB
- modify production source records unless explicitly using test source
- run against real production ingestion unless user approves

---

## Safety Requirements

This milestone must not perform destructive actions.

Do not:

- delete iCloud files
- delete Vault files
- delete DB records
- modify source registry destructively
- clean staging as part of this milestone unless using existing dry-run/read-only inspection
- run a large download
- store Apple credentials
- introduce automatic intake
- introduce automatic cleanup

Any diagnostic command that could download files must be clearly identified before it runs.

Prefer help/version/report/code inspection over real acquisition in this milestone.

---

## Documentation Requirements

The strategy document should also include a plain-English operator summary:

```
What problem are we solving?Why fixed recent_count is not enough?What does “known” mean?What approach are we choosing?What will the operator see in Admin/reports later?What is deferred?
```

This should be understandable to the project owner, not only to coder.

---

## Deliverables

Required deliverables:

1. Codebase reconnaissance summary
2. `icloudpd` capability summary
3. Current acquisition behavior summary
4. Current cleanup/provenance known-state summary
5. Options comparison
6. Recommended v1.0 strategy
7. Implementation plan for 12.48.1
8. Validation plan for 12.48.1 / 12.48.2
9. New or updated operations doc:

```
docs/operations/icloud_non_repeat_acquisition_strategy.md
```

10. Coder closeout response:

```
docs/prompts/Coder response 12.48.md
```

or current project-approved equivalent.

---

## Definition of Done

12.48 is complete when:

- current iCloud acquisition code paths are documented
- current `icloudpd` behavior/capabilities are documented
- `--until-found` viability is assessed
- known-state is defined
- options are compared
- a clear v1.0 recommendation is made
- implementation tasks for 12.48.1 are listed
- validation plan is defined
- safety constraints are preserved
- no destructive action occurred
- no large acquisition occurred
- the next implementation milestone can be written without major unresolved strategy questions

---

## Required Coder Closeout Response

After completion, create:

```
docs/prompts/Coder response 12.48.md
```

The closeout response should include:

1. Milestone title and date
2. Scope completed
3. Files inspected
4. Commands run, if any
5. `icloudpd` version/capability findings
6. Current acquisition behavior findings
7. Current report/run model findings
8. Current cleanup/provenance findings
9. Option comparison summary
10. Recommended v1.0 strategy
11. Why `--until-found` is or is not sufficient
12. Required implementation steps for 12.48.1
13. Required validation steps for 12.48.1 / 12.48.2
14. Safety confirmation
15. Deviations from prompt, if any
16. Known limitations
17. Recommended next milestone

---

## Recommended Next Milestone

If 12.48 completes with a clear strategy, the likely next milestone is:

```
12.48.1 — iCloud Non-Repeat Acquisition Implementation
```

If the strategy remains uncertain, use a narrow diagnostic milestone first:

```
12.48.1 — iCloud Non-Repeat Acquisition Diagnostic Test
```

Implementation should not begin until the project has a clear decision on:

```
whether icloudpd --until-found is sufficient,or whether Photo Organizer must maintain its own known-state/checkpoint layer.
```
