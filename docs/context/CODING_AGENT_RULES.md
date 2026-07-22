# CODING_AGENT_RULES.md — Photo Organizer

## Purpose

This document defines standing rules for AI coding agents working on the Photo Organizer codebase.

Its purpose is to reduce repeated milestone-prompt boilerplate while preserving:

- safety;
- architecture discipline;
- local-first data handling;
- milestone scope;
- durable documentation;
- clean git history;
- consistent prompt and closeout naming;
- cost-aware agent usage;
- simple, maintainable implementation;
- clear escalation when the current roadmap is insufficient.

Milestone prompts may reference this file instead of repeating every standing project rule.

This file is not a replacement for:

- the active milestone prompt;
- current repository code;
- feature-specific reconnaissance;
- product-owner decisions;
- validation;
- milestone closeout documentation.

Use repository files and the active prompt as the source of truth. Do not rely on chat memory alone.

---

## 1. Rule Priority

Apply instructions in this order:

1. explicit current product-owner direction;
2. active milestone prompt and approved prompt addenda;
3. this rules document;
4. current architecture, workflow, and context documents;
5. prior prompts and closeouts;
6. agent assumptions.

When two instructions conflict:

- follow the safer rule;
- stop and identify the conflict;
- ask for clarification before risky implementation;
- do not silently choose a new architecture or broaden scope.

A milestone prompt may explicitly override a standing rule. The closeout must document the override, why it was necessary, and how safety was preserved.

---

## 2. Standard Agent Workflow

For every coding task:

1. Read this file.
2. Read the active milestone prompt and approved addenda.
3. Perform git preflight.
4. Determine whether the task is reconnaissance or implementation.
5. Inspect the relevant current code.
6. Confirm the milestone boundary.
7. Ask only genuinely blocking questions.
8. Implement only approved scope.
9. Run the most relevant validation.
10. Create exactly one closeout using the required filename.
11. Leave commit and push actions to the User unless explicitly authorized.

Do not assume prior chat context is complete or current.

Do not implement from memory when current code, prompts, or closeouts contradict it.

---

## 3. Task Modes and Reasoning Effort

The project uses two primary milestone modes.

### 3.1 Reconnaissance / Contract Mode

Reconnaissance is the higher-reasoning phase.

Its job is to:

- inspect the relevant system;
- map current behavior;
- identify hidden dependencies;
- compare realistic implementation options;
- resolve architecture and product questions;
- identify safety, concurrency, recovery, and data-integrity concerns;
- select one recommended implementation direction;
- produce a practical roadmap for the next implementation milestone.

Reconnaissance may inspect broadly when the feature genuinely spans multiple systems.

Reconnaissance must not become speculative architecture work. Prefer the simplest safe recommendation that reuses current code.

When the prompt says reconnaissance only:

- do not modify implementation files;
- do not begin coding;
- do not create the implementation prompt unless explicitly requested;
- do not run live ingestion, cleanup, deletion, or other mutating workflows;
- create the required closeout and stop.

### 3.2 Implementation Mode

Implementation normally follows an approved reconnaissance closeout.

The reconnaissance closeout is the roadmap.

Implementation should usually use a moderate, execution-focused reasoning posture:

- verify the recon assumptions against the current branch;
- inspect the named files, services, schemas, components, and tests;
- make the smallest safe change that satisfies the locked contract;
- expand inspection only when current code materially contradicts the roadmap or tests expose an undocumented dependency;
- do not repeat broad reconnaissance;
- do not reopen settled product or architecture decisions without a concrete blocker;
- stop when required behavior and validation pass.

Implementation must not create alternative architectures merely because they are possible.

### 3.3 Direct Low-Risk Work

A separate recon milestone is not required for:

- copy-only text changes;
- small labels or wording changes;
- narrow styling fixes;
- focused tests;
- documentation-only edits;
- minor non-destructive bugs with an obvious local cause.

Even for low-risk work, inspect the directly relevant code before changing it.

### 3.4 Reasoning-Level Guidance

Recommended operating pattern:

- documentation or trivial UI copy: low or medium;
- normal implementation following a completed recon: medium;
- broad recon, difficult architecture, migrations, concurrency, recovery, or data-loss risk: high;
- deeper reasoning only after a concrete escalation or unresolved blocker.

The agent does not need to diagnose its own internal reasoning setting. It must recognize when the roadmap is insufficient and request escalation rather than improvising.

---

## 4. Escalation Protocol

Do not continue experimenting indefinitely when the implementation roadmap is insufficient.

Stop and report:

```text
STATUS: ESCALATION REQUIRED
```

when any of the following occurs:

- current code materially contradicts the recon closeout;
- two or more materially different architectures remain and the recon did not choose;
- the required behavior appears to need a schema migration, new persistence model, new orchestration framework, or broad cross-cutting refactor;
- an existing service cannot satisfy the locked contract without changing established semantics;
- a safety, concurrency, data-integrity, Vault, provenance, recovery, or credential issue is discovered that the recon did not resolve;
- focused investigation cannot explain a failing test or runtime result;
- implementation would require expanding beyond the named milestone;
- a product decision is required;
- the task cannot be completed confidently without deeper investigation;
- the only apparent solution is speculative or significantly more complex than the approved roadmap.

When escalating, return:

1. Exact blocker.
2. Recon assumption that does not match current code.
3. Files, services, and tests inspected.
4. Focused approaches attempted.
5. Evidence, errors, or failing tests.
6. Why proceeding would be unsafe or speculative.
7. Whether the need is:
   - higher reasoning;
   - additional reconnaissance;
   - a product-owner decision;
   - a narrower follow-up milestone.
8. Smallest recommended next step.
9. List of any incomplete uncommitted changes.

Do not create speculative abstractions or partial workarounds merely to avoid escalation.

This protocol applies to all coding agents. Some agents may ask questions naturally, but the explicit escalation format is required when the problem exceeds the approved roadmap.

---

## 5. Simplicity and Restraint

The project is complex. Complexity in the code must be justified by a real requirement.

Prefer:

- direct control flow;
- existing services and run records;
- explicit mappings;
- small helpers with clear responsibilities;
- targeted changes;
- narrow API additions;
- obvious operator behavior;
- maintainable code another agent can understand quickly.

Avoid unless clearly required:

- new orchestration frameworks;
- plugin systems;
- generic workflow engines;
- event buses;
- speculative provider abstractions;
- new persistence tables;
- duplicate run records;
- broad refactors;
- framework changes;
- abstractions for hypothetical future providers;
- multiple layers that merely wrap existing code;
- parallel implementations of an existing pathway.

Before adding a new abstraction, answer:

1. What exact current problem requires it?
2. Why can existing code not satisfy the requirement?
3. What is the smallest alternative?
4. What maintenance burden will it add?
5. Can a direct mapping, adapter, or conditional dispatch solve the problem?

If the technically elegant solution is harder for the operator or future maintainers to understand, prefer the simpler solution.

Do not overbuild merely because the model can.

---

## 6. Context Reading Rules

### Always Read

- `docs/context/CODING_AGENT_RULES.md`
- the active milestone prompt
- approved prompt addenda
- the immediately preceding recon closeout when implementing from recon

### Read as Needed

Use broader project documents only when relevant:

```text
docs/context/PROJECT_CONTEXT*.md
docs/context/PROJECT_ARCHITECTURE*.md
docs/context/ARCHITECTURE_ROADMAP*.md
docs/context/PROJECT_WORKFLOW*.md
docs/context/MILESTONE_HISTORY*.md
docs/context/Parking_Lot*.md
prior prompt and closeout files in the same feature area
```

### Targeted Implementation Reading

For an implementation milestone following recon, start with:

1. this rules document;
2. the implementation prompt;
3. the immediately preceding recon closeout;
4. named implementation files;
5. directly related tests.

Do not reread the entire repository or all project documents unless:

- current code materially contradicts the recon;
- the implementation crosses a high-risk architecture boundary;
- a test reveals an undocumented dependency;
- the prompt specifically requires broader reading.

### High-Risk Context

Read the relevant architecture and workflow sections before changing:

- ingestion;
- Source Intake;
- Source Profiles;
- source identity;
- cloud acquisition;
- cleanup or deletion;
- Vault behavior;
- provenance;
- migrations or backfills;
- authentication or sessions;
- production runtime;
- durable background routines.

---

## 7. Prompt Length and Duplication

Milestone prompts should be as long as needed, but no longer.

Do not treat prompt length as a proxy for safety or quality.

Use these principles:

- state standing rules once in this document;
- reference this document instead of repeating it;
- let reconnaissance carry architecture decisions into implementation;
- do not restate the entire recon contract in the implementation prompt;
- keep implementation prompts focused on scope, named files/services, required behavior, tests, stop conditions, and closeout;
- consolidate repeated safety boundaries;
- avoid asking the implementation agent to repeat broad repository inspection already completed during recon;
- use detailed prompts only when the feature genuinely contains many distinct safety-critical branches.

A long recon prompt may be appropriate for a broad feature.

An implementation prompt following that recon should normally be materially shorter.

---

## 8. Git and Working Tree Rules

### 8.1 Git Preflight

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
active prompt committed
```

Allowed exception:

```text
only the active prompt contains expected Q&A or addenda
```

If unexpected dirty files exist, stop before coding and classify them.

### 8.2 Dirty-Tree Classification

Classify each unexpected dirty file as:

```text
A. required prior-milestone follow-up
B. unrelated work
C. accidental or generated noise
D. required for current milestone
```

Report the classification and a brief diff summary.

Do not edit, revert, stage, stash, commit, or delete unexpected dirty files without authorization.

### 8.3 Git Write Commands

Do not run these without explicit authorization:

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

Read-only git commands are expected:

```text
git status
git diff
git diff --name-only
git diff --stat
git log
git branch
```

### 8.4 Specific-File Staging

Do not use:

```powershell
git add .
```

unless the User has reviewed the entire dirty tree and explicitly approved it.

When preparing commit guidance, use specific files and review the staged set:

```powershell
git status --short
git diff --name-only
git diff --stat

git add <specific file>
git add <specific file>

git diff --cached --name-only
git diff --cached --stat
git diff --cached --check
```

Do not mix unrelated work in one commit.

---

## 9. Prompt and Closeout File Names

The milestone prompt is authoritative for:

- milestone number;
- milestone title;
- prompt filename;
- closeout filename;
- deliverables.

Use:

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

- use the same basename;
- replace `_prompt.md` with `_closeout.md`;
- do not invent another closeout filename;
- do not create additional human-authored report files unless requested;
- do not rename for convenience.

A new milestone arc normally starts at:

```text
xx.xx.0
```

Follow-up actions increment:

```text
xx.xx.1
xx.xx.2
xx.xx.3
```

---

## 10. Prompt Addenda and Q&A

When requested, append coder questions, product answers, and final lock-ins to the same prompt file.

Recommended structure:

```markdown
## Original Prompt

## Coder Questions / Answers Round 1

## Coder Questions / Answers Round 2

## Final Lock-ins
```

The active prompt may remain dirty during implementation when:

- it was committed before handoff;
- only expected Q&A or addenda changed;
- the User confirms this is intentional.

Stop and ask when an addendum materially changes:

- milestone scope;
- safety boundaries;
- live-operation approval;
- destructive behavior;
- Vault behavior;
- source identity;
- provenance;
- schema, migration, or backfill behavior;
- credential handling;
- the implementation architecture;
- prompt or closeout filenames.

---

## 11. Core Architecture Rules

These rules are mandatory unless a milestone explicitly changes them.

### 11.1 Local-First

Photo Organizer is a local-first archival system.

Cloud providers may be acquisition sources, but they are not the system of record.

### 11.2 Original Media Preservation

Do not modify original media files in place.

### 11.3 Vault

The Vault is durable archival storage.

Treat Vault contents as immutable unless a milestone explicitly defines a reviewed Vault operation.

Do not write directly to Vault from:

- cloud acquisition;
- external scanning;
- preview code;
- helper utilities;
- identity probes.

### 11.4 Source Intake Authority

Source Intake is the ingestion authority.

Only Source Intake may move files into the ingestion path and create durable asset or provenance records.

Do not bypass Source Intake to create:

- assets;
- provenance;
- canonical metadata;
- Vault records.

### 11.5 Cloud Acquisition Boundary

Cloud acquisition is staging only.

It may write to an approved managed staging or export location.

It must not directly write to:

- Vault;
- Drop Zone;
- asset records;
- provenance records;
- canonical metadata records.

### 11.6 iCloud Staging

iCloud acquisition writes only to the selected Source Profile’s managed staging path, normally under:

```text
storage/exports/icloud/<profile_slug>/
```

### 11.7 Cleanup

Cleanup may act only on verified local staging files.

Cleanup must never delete:

- cloud-library data;
- remote provider data;
- Vault files;
- assets;
- provenance;
- Source Profiles;
- source registry history.

Cleanup must be bounded, verified, and reportable.

### 11.8 Provenance

Preserve provenance.

Do not delete or overwrite provenance history unless a milestone explicitly scopes a safe correction or migration.

Provenance must remain explainable after ingestion, dedupe, Source Profile changes, cleanup, or canonicalization.

### 11.9 User Authority

Do not silently undo user decisions, including:

- person assignments;
- face reassignments;
- duplicate adjudication;
- demotion or restoration;
- place corrections;
- date trust overrides;
- accepted or rejected AI/provider suggestions.

### 11.10 AI and Provider Evidence

AI, computer vision, geocoding, cloud-provider, and metadata-provider outputs are evidence, not canonical truth.

Do not promote them automatically unless the milestone defines reviewed behavior.

### 11.11 Credential Safety

Do not store or expose:

- passwords;
- 2FA codes;
- session cookies;
- tokens;
- secrets;
- credentials in logs;
- credentials in DB rows;
- credentials in source-controlled files.

Provider helpers may own external session mechanisms. Photo Organizer may expose only safe non-secret status.

---

## 12. Scope Discipline

Implement only the approved milestone.

Do not:

- perform unrelated refactors;
- fix nearby issues that are not required;
- change APIs, models, workflows, or identity semantics outside scope;
- add speculative future support;
- turn a focused milestone into architecture cleanup;
- broaden tests into unrelated systems without a reason.

When unrelated issues are discovered:

- document them under Known Limitations, Parking Lot, or Recommended Next Milestone;
- do not fix them unless the User approves.

Prefer small targeted changes over broad rewrites.

A validation-discovered bug may remain within the milestone when it is directly caused by or blocks the milestone behavior. Otherwise split it into a separate fix.

---

## 13. Reconnaissance Requirements

Reconnaissance is required before broad or high-risk changes involving:

- ingestion;
- Source Intake;
- Source Profiles;
- source identity;
- cloud acquisition;
- cleanup or deletion;
- Vault;
- provenance;
- duplicate canonicalization;
- face/person identity;
- place canonicalization;
- migrations or backfills;
- authentication or sessions;
- runtime and deployment scripts;
- durable background workflows;
- broad UI workflows.

A recon closeout should identify:

1. relevant files, routes, services, components, and models;
2. current behavior;
3. current execution and data flow;
4. safety boundaries;
5. concrete gaps;
6. chosen implementation direction;
7. files likely to change;
8. tests and manual validation;
9. migration or backfill need;
10. blockers and escalation points;
11. controls to retain or retire;
12. whether one implementation milestone is sufficient.

Do not present several equal architectures without recommending one.

Do not recommend new infrastructure without proving the existing system cannot meet the requirement.

---

## 14. Stop Conditions

Stop and ask before coding when:

- the request conflicts with this document;
- unexpected dirty files exist;
- safety cannot be proven;
- Source Intake would be bypassed;
- cloud acquisition would write directly to Vault, Drop Zone, assets, or provenance;
- cleanup could affect anything outside verified local staging;
- code structure materially differs from the prompt or recon;
- an unapproved migration or backfill is required;
- deletion or destructive behavior was not explicitly scoped;
- source identity semantics must change;
- local/external behavior may be broken by cloud-specific work;
- cloud behavior may be broken by filesystem-specific work;
- secrets might be stored or exposed;
- broad refactoring appears necessary;
- multiple product-relevant implementations remain;
- filenames are unclear;
- additional report files seem necessary;
- an existing proven pathway would be duplicated;
- the milestone requires a new framework or persistence model not approved in recon.

Use the escalation protocol when the blocker exceeds a normal clarification question.

---

## 15. File and Data Safety

Before code can delete, move, rewrite, hide, demote, import, or clean data, identify:

- exact files or records affected;
- verification protecting them;
- whether the action is reversible;
- whether it is local, external, NAS, or cloud-facing;
- operator confirmation;
- logging and reporting;
- provenance behavior;
- failure and interruption handling.

For destructive actions prefer:

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

## 16. Source Profile and Identity Rules

Source Profiles are the user-facing source concept.

Preserve:

- stable Source identity;
- Source history;
- endpoint and Source Profile distinction;
- endpoint-relative root semantics;
- active/inactive state;
- explainable provenance.

Do not confuse:

- display label with durable identity;
- drive letter with device identity;
- observed path with endpoint identity;
- Source Root with endpoint boundary.

Durable identity should use appropriate evidence, such as:

- Volume GUID or filesystem UUID;
- device serial where safely available;
- removable-media identity;
- optical media fingerprint;
- NAS server/share identity;
- provider/account identity;
- observed path history as evidence only.

Drive letters and mount paths are observations, not durable identity.

Do not silently repair, relink, canonicalize, or migrate legacy Sources outside an approved milestone.

---

## 17. iCloud Rules

For iCloud:

- `icloudpd` remains the preferred acquisition adapter;
- acquisition is staging-only;
- Source Intake performs ingestion;
- cleanup is local-staging-only;
- credentials and 2FA are never stored;
- username may be stored as non-secret metadata;
- managed staging must match the selected Source Profile;
- acquisition and intake results must remain linked or explainable;
- non-repeat behavior must not rely only on staged file existence after cleanup;
- cleanup must not create redownload loops without reporting.

The established operator flow may include:

```text
Refresh / Prepare
Import / Resume
Cleanup
```

or a proven orchestration wrapper around those phases.

Do not redesign working iCloud behavior without a named requirement.

Normal UI should emphasize:

```text
Source Profile
Inventory state
Logical candidates
Current or last run
Progress
Result
Next safe action
Advanced Details
```

Keep raw run IDs, low-level cleanup internals, provider diagnostics, and historical counters in Advanced Details unless needed for normal operation.

---

## 18. UI and UX

Normal workflows should expose operator concepts, not backend plumbing.

Prefer:

```text
Source
Availability
Relevant options
Primary action
Progress
Result
Next safe action
Advanced Details
```

Use Advanced Details for:

- canonical paths;
- internal IDs;
- normalized labels;
- identity evidence;
- provider diagnostics;
- run IDs;
- technical conflicts;
- report paths;
- historical accounting;
- low-level timings.

Use clear statuses:

```text
Ready
Available
Unavailable
Blocked
Needs attention
Resume available
Running
Stopping
Completed
Completed with warnings
Failed
Interrupted
```

Warnings should be:

- handled automatically;
- converted to a blocker;
- or placed in Advanced Details.

Do not leave multiple competing normal workflows for the same action.

Do not make the operator choose something already determined by Source identity or workflow context.

---

## 19. Runtime and Deployment

Preserve Windows development behavior unless a milestone targets Linux or mini-server deployment.

When changing runtime scripts:

- preserve dev/prod separation;
- do not fall back to development storage in production;
- report occupied ports clearly;
- report unresolved listeners clearly;
- do not kill unrelated processes without confirmation;
- keep startup and shutdown understandable to a non-programmer.

Future deployment model:

```text
Mini server = compute, runtime, web, and AI host
NAS = durable media storage and backup layer
```

Do not place live database files on an unvalidated mapped NAS share.

---

## 20. Testing and Validation

Run the most relevant validation available.

Possible validation includes:

- focused unit tests;
- API tests;
- full backend suite when warranted;
- frontend lint and production build;
- migration checks;
- dry runs;
- runtime health checks;
- report/log inspection;
- browser smoke;
- approved live workflow testing.

Do not claim full validation when only partial checks were run.

When a check cannot run:

- state why;
- distinguish implementation capability from live-environment limitations;
- identify the smallest remaining manual test.

For ingestion, cloud, cleanup, and identity work, consider:

- interruption;
- resume;
- stale running state;
- progress;
- durable reports;
- partial completion;
- cleanup safety;
- source-type regressions;
- metadata before/after counts.

Do not run live ingestion or destructive operations unless explicitly approved.

---

## 21. Closeout Requirements

Create exactly one human-authored closeout per milestone.

Do not create separate files such as:

```text
report.md
operations.md
coder_response.md
```

unless explicitly requested.

The closeout filename must match the prompt basename, replacing:

```text
_prompt.md
```

with:

```text
_closeout.md
```

Runtime-generated reports and screenshots are allowed. Reference them from the closeout.

### Standard Closeout Structure

Use this structure unless the prompt requires more detail:

```markdown
# Milestone <number> — <title>

## 1. Repository State
Branch, HEAD, and working tree.

## 2. Scope Completed
What was implemented.

## 3. Operational Behavior
How the feature works for the operator.

## 4. Files Changed
Added, modified, and deleted files.

## 5. API / Data Model Changes
Only when applicable.

## 6. Architecture and Safety Boundaries
What was reused and what was intentionally not changed.

## 7. Validation Performed
Commands and results.

## 8. Live / Manual Validation
Operator or runtime testing.

## 9. Deviations from Prompt
Anything not completed or interpreted differently.

## 10. Known Limitations
Remaining issues and environment limitations.

## 11. Recommended Next Milestone
The next logical action.

## 12. Git Status
`git status --short` and relevant diff summary.
```

The prompt may require a more detailed feature-specific closeout.

Append post-closeout testing to the same file. Do not create another closeout.

---

## 22. Cost-Aware Agent Behavior

Minimize unnecessary agent time and token use without sacrificing safety.

Do:

- begin with the likely relevant files;
- use the recon closeout as the roadmap;
- inspect targeted call chains;
- summarize findings before broad searches;
- ask focused questions;
- stop when acceptance criteria pass;
- report unrelated issues instead of fixing them;
- use existing tests and patterns;
- escalate when deeper reasoning is needed.

Do not:

- reread every project document for every task;
- repeat repository-wide scans without a reason;
- repeat completed reconnaissance during implementation;
- reconsider settled decisions without evidence;
- rewrite unrelated systems;
- add speculative improvements;
- keep trying unrelated approaches after a stop condition;
- use high-effort exploration for a straightforward roadmap implementation.

Longer execution time is not itself evidence of better work.

The objective is the smallest safe, validated change—not maximum exploration.

---

## 23. Performance Awareness

Consider:

- ingestion time;
- query efficiency;
- UI responsiveness;
- background workload;
- disk and network effects;
- large-library scale;
- NAS and cloud latency.

Expensive operations include:

- duplicate lineage;
- face processing;
- visual enrichment;
- iCloud acquisition;
- Source Intake;
- cleanup scans;
- external/NAS scans;
- AI inference.

Do not optimize speculatively.

When performance is observed but outside scope, document it as a limitation or future milestone.

---

## 24. Documentation Discipline

Prompt and closeout files are the primary detailed record for each milestone.

Update global documents only when the milestone changes:

- architecture;
- workflow;
- source identity;
- ingestion model;
- safety model;
- deployment;
- major operator behavior;
- milestone process.

Do not create new documentation patterns without approval.

Do not create conversational artifact files such as `Coder response*.md` unless requested.

---

## 25. Success Criteria

A coding-agent session is successful when:

- the approved scope is completed;
- the recon roadmap is followed or a clear escalation is raised;
- unnecessary architecture is avoided;
- unrelated systems remain untouched;
- dirty files are identified before coding;
- core safety boundaries are preserved;
- validation is appropriate and honestly reported;
- exactly one correctly named closeout is created;
- limitations and deviations are documented;
- the working tree remains understandable;
- the commit can be reviewed as a logical change set;
- the User can safely test, commit, and continue;
- the code is simpler to maintain than an overbuilt alternative.
