# CODING_AGENT_RULES.md — Photo Organizer

## Document Status

**Version:** v6  
**Project phase:** Post-12.63.23.0  
**Current architecture baseline:** Source Identity and Intake Unification merged into `main`  
**Current verification priority:** Provenance correctness across the unified Source Creation, Selection, readiness, dispatch, and intake workflows.

---

## Purpose

This document defines standing rules for AI coding agents working on the Photo Organizer codebase.

Its purpose is to reduce repeated milestone-prompt boilerplate while preserving:

- safety;
- architectural discipline;
- local-first data handling;
- milestone scope;
- durable documentation;
- clean Git history;
- consistent prompt and closeout naming;
- cost-aware agent usage;
- simple and maintainable implementation;
- clear escalation when the approved roadmap is insufficient;
- Source identity correctness;
- provenance and data-integrity protection;
- honest validation reporting;
- separation between validation and repair.

Milestone prompts may reference this file instead of repeating every standing project rule.

This file is not a replacement for:

- the active milestone prompt;
- approved prompt addenda;
- current repository code;
- feature-specific reconnaissance;
- approved reconnaissance closeouts;
- product-owner decisions;
- validation;
- milestone closeout documentation.

Use repository files and the active prompt as the source of truth.

Do not rely on chat memory alone.

---

# 1. Rule Priority

Apply instructions in this order:

1. explicit current Product Owner direction;
2. active milestone prompt and approved prompt addenda;
3. this rules document;
4. current architecture, workflow, and context documents;
5. approved reconnaissance closeout;
6. prior prompts and closeouts;
7. agent assumptions.

When two instructions conflict:

- follow the safer rule;
- stop and identify the conflict;
- ask for clarification before risky implementation;
- do not silently choose a new architecture;
- do not silently broaden scope;
- do not silently change provenance, Source identity, or persistence semantics.

A milestone prompt may explicitly override a standing rule.

The closeout must document:

- the override;
- why it was necessary;
- who approved it;
- how safety was preserved;
- whether data, provenance, or migration behavior changed.

---

# 2. Standard Agent Workflow

For every task:

1. Read this file.
2. Read the active milestone prompt and approved addenda.
3. Read the approved reconnaissance closeout when the prompt identifies one.
4. Perform Git preflight.
5. Confirm the current branch.
6. Determine the milestone mode.
7. Inspect the relevant current code or documentation.
8. Confirm the milestone boundary.
9. Ask only genuinely blocking questions.
10. Escalate when the approved roadmap is materially insufficient.
11. Implement or validate only the approved scope.
12. Run the most relevant validation.
13. Create exactly one closeout using the required filename.
14. Leave commit, push, merge, branch, and tag actions to the User unless explicitly authorized.

Do not assume prior conversational context is complete or current.

Do not implement from memory when current code, prompts, closeouts, or repository documents contradict it.

---

# 3. Milestone Modes

The milestone prompt should identify the intended mode.

Supported modes include:

```text
reconnaissance-only
implementation-after-reconnaissance
direct low-risk implementation
validation-only
documentation-only
bug-fix follow-up
deployment or operational validation
```

Do not silently change milestone mode.

---

## 3.1 Reconnaissance-Only Mode

Reconnaissance is the higher-reasoning phase.

Its purpose is to:

- inspect the relevant system;
- map current behavior;
- identify hidden dependencies;
- identify authority boundaries;
- compare realistic implementation options;
- resolve architecture questions;
- identify safety, concurrency, recovery, persistence, and data-integrity concerns;
- identify provenance implications;
- identify migration or backfill requirements;
- select one recommended implementation direction;
- produce a practical implementation roadmap.

Reconnaissance may inspect broadly when the feature genuinely crosses multiple systems.

Reconnaissance must not become speculative architecture work.

Prefer the simplest safe recommendation that reuses current code and current authorities.

When the prompt says reconnaissance only:

- do not modify implementation files;
- do not begin coding;
- do not make schema changes;
- do not repair defects;
- do not create the implementation prompt unless requested;
- do not run live ingestion, cleanup, deletion, migration, or other mutating workflows unless explicitly approved;
- create the required reconnaissance closeout;
- stop after the approved recon deliverables are complete.

Reconnaissance is not merely information gathering.

The closeout should be usable as the implementation roadmap.

---

## 3.2 Implementation-After-Reconnaissance Mode

Implementation normally follows an approved reconnaissance closeout.

The reconnaissance closeout is the primary roadmap.

Implementation should use a moderate, execution-focused reasoning posture:

- verify recon assumptions against the current branch;
- inspect the named files, services, schemas, routes, components, and tests;
- make the smallest safe change satisfying the locked contract;
- expand inspection only when current code materially contradicts the roadmap;
- do not repeat broad reconnaissance;
- do not reopen settled decisions without concrete evidence;
- stop when required behavior and validation pass.

Recommended reading order:

```text
1. CODING_AGENT_RULES.md
2. active implementation prompt
3. approved recon closeout
4. named implementation files
5. directly related tests
6. broader documents only when necessary
```

Do not repeat repository-wide searching unless:

- the repository changed materially after recon;
- the recon omitted a required path;
- targeted code contradicts the recon;
- tests expose an undocumented dependency;
- a persistence, provenance, or safety boundary remains unresolved.

When escalating, identify the exact recon assumption that failed.

Implementation must not create alternative architectures merely because they are possible.

---

## 3.3 Direct Low-Risk Implementation Mode

A separate recon milestone is not required for:

- copy-only text changes;
- small labels or wording changes;
- narrow styling fixes;
- focused tests;
- documentation-only edits;
- minor non-destructive bugs with an obvious local cause;
- mechanical corrections.

Even for low-risk work:

- inspect the directly relevant code;
- preserve scope;
- avoid unrelated cleanup;
- run relevant validation;
- create the required closeout.

Do not classify work as low-risk merely to reduce effort when it touches provenance, Source identity, ingestion, cleanup, schema, Vault, credentials, or deployment.

---

## 3.4 Validation-Only Mode

Validation-only milestones establish evidence about current behavior without changing implementation.

Examples include:

- provenance verification;
- exact duplicate behavior;
- cross-Source duplicate behavior;
- changed-drive-letter behavior;
- NAS Source lineage;
- Optical eject/reinsert identity;
- iCloud staging handoff;
- runtime smoke testing;
- backup and restore rehearsal;
- performance baselining.

In validation-only mode:

- inspect the approved test matrix;
- create or use only approved controlled test data;
- run the approved checks;
- collect database, API, report, filesystem, and UI evidence;
- document pass/fail results;
- do not modify implementation code;
- do not silently repair defects;
- do not modify schema;
- do not perform unapproved data cleanup;
- do not broaden the test matrix without explanation.

A validation milestone must not silently become a repair milestone.

When a defect is found:

1. preserve the evidence;
2. classify severity;
3. determine whether testing should continue or stop according to the prompt;
4. identify whether prior milestone conclusions are affected;
5. do not repair unless explicitly authorized;
6. recommend the smallest separate fix milestone.

---

## 3.5 Documentation-Only Mode

Documentation-only work may update:

- Project Context;
- Project Architecture;
- Project Workflow;
- Coding Agent Rules;
- Milestone History;
- Parking Lot;
- release roadmap;
- chat handoff documents;
- milestone documentation.

In documentation-only mode:

- do not modify application code;
- verify statements against current code, prompts, closeouts, and approved decisions;
- distinguish implemented behavior from future direction;
- preserve historical prompt and closeout files;
- do not delete historical milestone records;
- create only the requested documents;
- report new and superseded files;
- use exact-file staging guidance;
- ensure current global documents agree on major project state.

---

## 3.6 Bug-Fix Follow-Up Mode

A bug-fix follow-up should remain limited to the documented defect.

Rules:

- reproduce or confirm the defect;
- identify the smallest safe repair;
- preserve existing architecture;
- do not turn the repair into a broad refactor;
- add targeted regression coverage;
- document whether the defect invalidates earlier validation;
- document any retained limitation;
- create one closeout.

A bug fix should not be hidden inside unrelated later work.

---

## 3.7 Deployment or Operational Validation Mode

Deployment and runtime work may require reconnaissance, implementation, or validation-only behavior.

The prompt must identify which applies.

Deployment work should explicitly consider:

- target host;
- operating system;
- Docker;
- PostgreSQL;
- Redis;
- NAS mounts;
- Vault paths;
- permissions;
- Source identity providers;
- service supervision;
- logs;
- health checks;
- backup;
- restore;
- promotion;
- rollback;
- secrets;
- network exposure.

Do not assume Windows identity behavior works unchanged on Linux.

---

# 4. Reasoning-Level Guidance

Recommended operating pattern:

### High reasoning

Use for:

- architecture;
- reconnaissance;
- provenance;
- Source identity;
- ingestion authority;
- cleanup or destructive work;
- schema design;
- migrations;
- backfills;
- concurrency;
- recovery;
- credential/session behavior;
- deployment architecture;
- backup and restore;
- ambiguous cross-system behavior;
- data-loss risk.

### Medium reasoning

Use for:

- targeted implementation after approved recon;
- bounded backend changes;
- bounded frontend changes;
- test additions;
- implementation debugging;
- closeout creation;
- targeted validation automation.

### Lower reasoning

Use for:

- narrow documentation edits;
- simple copy changes;
- mechanical updates;
- small isolated tests;
- low-risk formatting corrections.

The agent does not need to report an internal model setting.

It must recognize when the approved roadmap is insufficient and escalate rather than improvising.

High reasoning should produce a concrete roadmap, not endless exploration.

---

# 5. Escalation Protocol

Do not continue experimenting indefinitely when the roadmap is insufficient.

Stop and report:

```text
STATUS: ESCALATION REQUIRED
```

when:

- current code materially contradicts the recon closeout;
- two or more materially different architectures remain unresolved;
- required behavior appears to need a new schema or migration;
- a new persistence model appears necessary;
- a new orchestration framework appears necessary;
- an existing service cannot satisfy the contract without changing established semantics;
- a safety, concurrency, data-integrity, Vault, provenance, recovery, or credential issue is discovered;
- focused investigation cannot explain a failing test or runtime result;
- implementation would materially expand beyond the milestone;
- a product decision is required;
- the only apparent solution is speculative;
- the only apparent solution is materially more complex than the approved roadmap;
- required manual or physical validation cannot be completed;
- a frontend value would need to become backend execution authority;
- a parallel ingestion or workflow engine appears necessary;
- unrelated dirty files threaten commit isolation.

Required format:

```text
STATUS: ESCALATION REQUIRED

Observed conflict:
Approved assumption that does not match:
Files or systems inspected:
Evidence:
Data/provenance implications:
Why proceeding is unsafe or materially broader:
Smallest safe options:
Recommended decision:
Incomplete changes, if any:
```

Do not create speculative abstractions or partial workarounds merely to avoid escalation.

Stop at the escalation point.

---

# 6. Simplicity and Restraint

The project is complex.

Complexity in the code must be justified by a current requirement.

Prefer:

- direct control flow;
- existing services;
- existing run records;
- explicit mappings;
- small helpers;
- clear responsibilities;
- targeted changes;
- narrow API additions;
- obvious operator behavior;
- maintainable code;
- thin orchestration around existing authorities.

Avoid unless clearly required:

- new orchestration frameworks;
- generic workflow engines;
- plugin systems;
- event buses;
- speculative provider abstractions;
- new persistence tables;
- duplicate run records;
- broad refactors;
- framework changes;
- abstractions for hypothetical providers;
- multiple wrapper layers;
- parallel implementations of existing pathways.

Before adding an abstraction, answer:

1. What exact current problem requires it?
2. Why can existing code not satisfy the requirement?
3. What is the smallest alternative?
4. What maintenance burden will it add?
5. Can a direct mapping, adapter, or conditional dispatch solve the problem?
6. Does it alter authority, provenance, or failure behavior?

Prefer the simpler safe implementation.

Do not overbuild merely because the agent can.

---

# 7. Context Reading Rules

## 7.1 Always Read

- `docs/context/CODING_AGENT_RULES*.md` identified by the prompt;
- the active milestone prompt;
- approved prompt addenda;
- the immediately preceding recon closeout when implementing from recon.

## 7.2 Read as Needed

Use broader documents only when relevant:

```text
docs/context/PROJECT_CONTEXT*.md
docs/context/PROJECT_ARCHITECTURE*.md
docs/context/ARCHITECTURE_ROADMAP*.md
docs/context/PROJECT_WORKFLOW*.md
docs/context/MILESTONE_HISTORY*.md
docs/context/Parking_Lot*.md
v1.0 release roadmap
prior prompt and closeout files in the same feature area
```

## 7.3 Targeted Implementation Reading

For implementation after recon, begin with:

1. this rules document;
2. implementation prompt;
3. approved recon closeout;
4. named files;
5. directly related tests.

Do not reread the entire repository unless required.

## 7.4 High-Risk Context

Read relevant architecture and workflow sections before changing:

- ingestion;
- Source Intake;
- Source Profiles;
- Source Endpoints;
- Source Selection;
- Run Ingestion dispatch;
- cloud acquisition;
- cleanup;
- Vault;
- provenance;
- exact duplicate behavior;
- migrations;
- backfills;
- authentication;
- sessions;
- production runtime;
- durable background routines;
- backup and restore.

---

# 8. Cost-Aware Investigation and Stopping

Milestone prompts should be as long as needed, but no longer.

Do not treat prompt length or repository search volume as a proxy for quality.

Use these principles:

- standing rules belong here;
- milestone prompts describe the current delta;
- reconnaissance carries architecture into implementation;
- implementation prompts should not restate the entire recon;
- start with likely relevant files;
- stop broad investigation when the implementation path is stable;
- do not repeat repository-wide scans without a reason.

Stop broad investigation when:

- the authority boundary is confirmed;
- affected persistence is understood;
- provenance impact is understood;
- required files are identified;
- implementation path is known;
- validation is defined;
- further searching is unlikely to change the plan.

Do not stop while any of these remain unclear:

- provenance;
- failure behavior;
- migration risk;
- cleanup scope;
- destructive behavior;
- execution authority;
- persistence semantics;
- identity matching;
- rollback or recovery implications.

Longer execution time is not itself evidence of better work.

The objective is the smallest safe and validated change.

---

# 9. Git and Working Tree Rules

## 9.1 Git Preflight

Before editing, report:

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

## 9.2 Branch Correctness

Substantial implementation should normally occur on the approved feature branch.

If:

- the prompt expects a feature branch but the repository is on `main`;
- the repository is on an unrelated feature branch;
- a new unrelated arc is being started on a completed branch;

stop and report the mismatch.

Do not create or switch branches unless explicitly authorized.

Documentation-only work may occur on `main` only when the prompt or User permits it.

## 9.3 Dirty-Tree Classification

Classify each unexpected dirty file as:

```text
A. required prior-milestone follow-up
B. unrelated work
C. accidental or generated noise
D. required current-milestone work
```

Report:

- classification;
- file path;
- brief diff summary;
- recommended handling.

Do not edit, revert, stage, stash, commit, delete, or clean unexpected files without authorization.

## 9.4 Git Write Commands

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
git branch -d
git branch -D
git push --delete
```

Read-only Git commands are expected:

```text
git status
git diff
git diff --name-only
git diff --stat
git log
git branch
git ls-files
```

## 9.5 Specific-File Staging

Do not use:

```powershell
git add .
```

unless the User explicitly approves the full dirty tree.

Preferred review and staging sequence:

```powershell
git status --short
git diff --name-only
git diff --stat

git add "<specific file>"
git add "<specific file>"

git diff --cached --name-only
git diff --cached --stat
git diff --cached --check
```

The staged file list must match the expected milestone file list.

Do not commit unexplained files.

Do not mix unrelated work in one commit.

---

# 10. Prompt and Closeout File Names

The active milestone prompt is authoritative for:

- milestone number;
- title;
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
12.75.0_provenance_verification_recon_prompt.md
12.75.0_provenance_verification_recon_closeout.md
```

Rules:

- use the same basename;
- replace `_prompt.md` with `_closeout.md`;
- do not invent another closeout filename;
- do not rename for convenience;
- do not create additional human-authored report files unless requested.

A new milestone arc normally begins at:

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

# 11. Prompt Addenda and Q&A

When requested, append Coder questions, Product Owner answers, and final lock-ins to the same prompt file.

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
- milestone mode;
- safety boundaries;
- live-operation approval;
- destructive behavior;
- Vault behavior;
- Source identity;
- provenance;
- schema;
- migration;
- backfill;
- credential handling;
- implementation architecture;
- prompt filename;
- closeout filename.

---

# 12. Core Architecture Rules

These rules are mandatory unless a milestone explicitly changes them.

---

## 12.1 Local-First

Photo Organizer is a local-first archival system.

Cloud providers may be acquisition Sources.

They are not the system of record.

The local Vault and database remain archival and operational truth.

---

## 12.2 Original Media Preservation

Do not modify original Source media in place.

This applies to:

- Local;
- External;
- Removable Media;
- NAS;
- Optical;
- cloud libraries;
- temporary acquisition staging before approved cleanup.

---

## 12.3 Vault

The Vault is immutable canonical storage.

Do not write directly to Vault from:

- cloud acquisition;
- Source probes;
- external scanning;
- preview code;
- identity providers;
- helper utilities;
- UI workflows.

Do not rewrite canonical originals for:

- metadata correction;
- curation;
- duplicate adjudication;
- display compatibility;
- enrichment.

---

## 12.4 Source Intake Authority

Source Intake is the filesystem ingestion authority.

Only Source Intake may govern:

- Drop Zone handoff;
- canonical Vault placement;
- Asset creation;
- provenance creation or observation;
- exact duplicate handling;
- canonical ingestion metadata processing;
- Source Intake reporting.

Do not bypass Source Intake to create:

- Assets;
- provenance;
- canonical metadata;
- Vault records.

Source Selection and dispatch do not ingest media.

---

## 12.5 Cloud Acquisition Boundary

Cloud acquisition is staging-only.

It may write to an approved managed staging or export location.

It must not directly write to:

- Vault;
- Drop Zone;
- Asset records;
- provenance records;
- canonical metadata.

---

## 12.6 Cleanup

Cleanup may act only on verified temporary local staging.

Cleanup must never delete:

- cloud-library data;
- remote provider data;
- original Source media;
- Vault files;
- Assets;
- provenance;
- Source Profiles;
- Source Endpoints;
- Source registry history.

Cleanup must be:

- bounded;
- verified;
- reportable;
- explicitly approved where required;
- fail-closed when path identity is uncertain.

---

## 12.7 User Authority

Do not silently undo user decisions, including:

- Person assignments;
- face reassignment;
- duplicate adjudication;
- demotion or restoration;
- Place corrections;
- date trust overrides;
- accepted AI/provider suggestions;
- rejected AI/provider suggestions;
- Event assignments;
- album or collection decisions.

---

## 12.8 AI and Provider Evidence

AI, computer vision, geocoding, metadata-provider, and cloud-provider output are evidence.

They are not canonical truth by default.

Do not promote evidence automatically unless the milestone explicitly defines reviewed behavior.

---

## 12.9 Credential Safety

Do not store or expose:

- passwords;
- 2FA codes;
- session cookies;
- tokens;
- secrets;
- credentials in logs;
- credentials in database rows;
- credentials in source-controlled files.

Provider helpers may own external session mechanisms.

Photo Organizer may expose only approved non-secret status.

---

# 13. Source Architecture Rules

## 13.1 Source Endpoint

A Source Endpoint is the durable identity of a:

- device;
- volume;
- NAS share;
- provider;
- Optical disc;
- future Source boundary.

Examples:

```text
identified Windows volume
canonical \\server\share
optical_media_fingerprint_v2
provider-specific iCloud identity
```

A Source Endpoint is not:

- a drive letter;
- a friendly Source name;
- an arbitrary folder path;
- a physical Optical drive;
- a temporary staging directory.

---

## 13.2 Source Profile

A Source Profile is the user-facing saved Source.

Architectural definition:

```text
Source Profile
= Source Endpoint
+ one endpoint-relative root
+ friendly Source name
+ status/settings
```

The UI term **Source** normally means Source Profile.

---

## 13.3 Endpoint-Relative Root

Semantics:

```text
NULL       legacy, unknown, or unresolved
""         entire endpoint
"path"     folder inside endpoint boundary
```

Containment must reject:

```text
..
absolute escape
share escape
volume escape
media-root escape
```

Do not treat an endpoint-relative root as a new endpoint.

---

## 13.4 Observed Path

Observed Path is current host access evidence.

Examples:

```text
E:\
F:\
\\HENDERSON-NAS\Photos
```

Observed Path is not durable identity.

Do not use a changed drive letter alone to create a new Source identity.

---

## 13.5 Runtime Root

Runtime Root is the backend-resolved execution path for one launch.

It is derived after:

- current probing;
- Source identity comparison;
- endpoint-relative-root application;
- containment validation.

The frontend may display Runtime Root.

The frontend must not authorize it.

---

## 13.6 Source Selection

Source Selection verifies current identity and availability.

It may derive:

- identity match;
- availability;
- resolved current path;
- Runtime Root;
- workflow kind;
- operator message;
- technical evidence.

Source Selection must not:

- ingest files;
- create an intake run;
- repair identity silently;
- trust frontend fingerprints or paths.

---

## 13.7 Readiness

Readiness is non-mutating.

It reports whether a saved Source can proceed.

It must not:

- create intake runs;
- rewrite endpoint identity;
- silently migrate identity versions;
- silently relink a Source;
- accept weak identity evidence.

Launch-time revalidation remains required.

---

## 13.8 Run Ingestion Dispatch

Run Ingestion dispatch revalidates the saved Source immediately before launch.

Dispatch:

- loads the saved Source Profile;
- reruns authoritative Source Selection;
- verifies identity and availability;
- resolves Runtime Root;
- applies containment;
- checks operation guardrails;
- routes to the existing workflow.

Dispatch is not:

- an ingestion engine;
- a new queue;
- a new persistence model;
- permission to trust frontend execution values.

Filesystem Sources continue to use Source Intake.

iCloud continues to use provider-specific iCloud Intake.

---

## 13.9 Frontend Values Are Not Execution Authority

Do not treat these frontend values as authoritative:

```text
runtime path
endpoint ID
fingerprint
workflow kind
readiness result
identity match
Source containment
```

The backend must recompute or verify them.

---

# 14. Source-Type-Specific Rules

## 14.1 Local

Local represents storage internal to the current host.

Current implementation is Windows-first.

Do not assume Windows volume evidence works unchanged on Linux or macOS.

---

## 14.2 External

External represents attached HDD or SSD storage.

Rules:

- drive letter is not identity;
- reconnecting under another letter may still be the same endpoint;
- alias is not identity;
- one endpoint may support multiple intentional Source roots.

---

## 14.3 Removable Media

Removable Media represents writable removable storage such as USB flash media.

It uses the same endpoint-linked model but remains a separate Source Type.

Do not collapse modern Removable Media into a legacy generic type.

---

## 14.4 NAS

NAS identity is anchored to canonical server/share authority.

Example:

```text
\\HENDERSON-NAS\Photos
```

Rules:

- direct UNC access is supported;
- server-only UNC is invalid;
- mapped drive letter is not NAS identity;
- endpoint-relative root must remain inside the share;
- traversal must be rejected;
- NAS reuses filesystem Source Intake;
- do not introduce a NAS-specific ingestion engine.

---

## 14.5 Optical

Optical identity represents the logical disc, not the drive.

Current identity version:

```text
optical_media_fingerprint_v2
```

v2 excludes:

- free space;
- computed used space;
- file timestamps;
- directory timestamps;
- drive letter;
- mount point;
- physical drive identity.

Existing v1 records remain legacy.

Rules:

- do not silently migrate v1 to v2;
- do not treat v1 and v2 as interchangeable;
- do not use the physical Optical drive as disc identity;
- exact matching remains fail-closed.

Not supported unless explicitly scoped:

- audio ripping;
- DVD/Blu-ray movie ripping;
- decryption;
- disc writing;
- automatic eject.

---

## 14.6 iCloud

For iCloud:

- `icloudpd` remains the preferred acquisition adapter;
- acquisition is staging-only;
- Source Intake performs canonical ingestion;
- cleanup is local-staging-only;
- credentials and 2FA are never stored;
- username may be stored as non-secret metadata;
- staging must match the selected Source Profile;
- acquisition and intake results must remain linked and explainable;
- staging path alone is not sufficient final provenance;
- working iCloud behavior must not be redesigned without a named requirement.

Established operator concepts may include:

```text
Refresh / Prepare
Import / Resume
Cleanup
```

Keep raw run IDs, provider diagnostics, historical counters, and low-level cleanup details under Advanced Details unless needed for normal operation.

---

# 15. Provenance Rules

Provenance is a first-class architectural system.

Do not treat it as a report-only concern.

---

## 15.1 Content Identity and Provenance Are Separate

SHA-256 identifies exact content.

Provenance explains origin.

Therefore:

```text
same SHA-256
does not mean
same provenance
```

The same Asset may have legitimate observations from:

- Local;
- External;
- Removable Media;
- NAS;
- Optical;
- iCloud;
- multiple roots on one endpoint;
- multiple Source-relative paths.

---

## 15.2 Asset, Vault, and Provenance Distinction

Agents must distinguish:

```text
Asset
Vault file
Source Endpoint
Source Profile
endpoint-relative root
Source-relative asset path
Observed Path
Runtime Root
Source Intake run
provenance observation
cloud acquisition record
skipped/deferred inventory record
```

Do not use these terms interchangeably.

---

## 15.3 Provenance Anchor

For modern Sources, provenance should be logically explainable through:

```text
Asset
→ Source Profile
→ Source Endpoint
→ Source-relative path
→ intake or observation context
```

The implemented persistence may retain compatibility layers.

Do not obscure the architectural meaning.

---

## 15.4 Source-Relative Path

Distinguish:

```text
runtime absolute path
endpoint boundary
configured endpoint-relative root
asset Source-relative path
```

Runtime absolute paths are host-specific.

Source-relative paths should explain origin without depending on a transient drive letter or mount point.

---

## 15.5 Exact Duplicate Provenance

When exact content already exists:

- do not create a second Asset;
- do not create a second Vault file;
- preserve a legitimate new Source observation when current semantics require it;
- preserve earlier provenance;
- report duplicate behavior accurately;
- avoid uncontrolled duplicate provenance rows.

Do not “repair” duplicate provenance by deleting historical rows without an explicitly scoped correction or migration.

---

## 15.6 Repeated Intake Idempotency

Repeated unchanged intake should be deterministic.

It must not create noisy duplicate provenance history merely because another run occurred.

Preferred principle:

```text
current-state observation
+ event history only for meaningful change
```

Meaningful change may include:

- first observation from a Source/path;
- Source-relative path change;
- status change;
- reason change;
- identity evidence change;
- correction of incomplete provenance.

Unchanged repeat observation should not generate duplicate event noise.

---

## 15.7 Cross-Source Duplicate Behavior

When the same SHA-256 is ingested from another Source:

Expected architecture normally permits:

```text
one Asset
one Vault file
multiple valid Source observations
```

Do not collapse separate Source origins merely because content is identical.

Do not create a second Asset merely to preserve origin.

---

## 15.8 Provenance and Source Changes

These changes must not erase historical origin:

- Source status changes;
- display-name changes;
- changed drive letter;
- changed Observed Path;
- curation;
- Event assignment;
- Place assignment;
- Person assignment;
- album membership;
- collection membership;
- duplicate canonical selection;
- visibility changes.

---

## 15.9 Skipped and Deferred Inventory

Items seen in Source or provider inventory but not imported are not successful Asset provenance.

Skipped/deferred state should remain separate from canonical Asset lineage.

Use the approved state model or log.

Do not append duplicate unchanged history on every run.

Append history only when:

- a new skip/defer event occurs;
- state changes;
- reason changes;
- meaningful identity evidence changes.

Do not falsely create Asset or provenance records for unsupported, deferred, ambiguous, or policy-blocked items.

---

## 15.10 Provenance and iCloud

Temporary staging paths do not fully explain cloud origin.

Current provenance should remain linked to the intended iCloud Source context.

Future provider-native identifiers may add richer cloud lineage.

Do not use cleanup of local staging as justification to remove provenance.

---

## 15.11 Provenance and Reports

Reports may summarize provenance effects.

Reports are not the provenance system of record.

Database state remains authoritative.

---

# 16. Provenance Evidence Standards

For provenance work, conclusions should be supported by appropriate combinations of:

```text
database records
API responses
Source Intake reports
known SHA-256 values
Asset records
Vault-file checks
Source Profile records
Source Endpoint records
Source-relative paths
repeat-run comparisons
cross-Source comparisons
```

UI labels are supporting evidence.

UI labels alone are not proof.

Intake summary counts are supporting evidence.

Summary counts alone are not proof.

The closeout should identify:

- query or inspection method;
- expected rows or counts;
- actual rows or counts;
- expected relationships;
- actual relationships;
- whether behavior is confirmed;
- whether behavior is inferred;
- whether behavior remains untested;
- whether environment blocked validation.

Do not describe an inference as confirmed behavior.

---

# 17. Provenance Validation Matrix Expectations

When a prompt scopes provenance validation, expect cases such as:

- new unique file from one Source;
- repeated same Source and same path;
- same endpoint with different Source roots;
- exact duplicate across different Sources;
- exact duplicate across different Source Types;
- changed drive letter;
- NAS UNC Source;
- Optical eject/reinsert;
- wrong Optical disc;
- iCloud staging handoff;
- rejected or failed file;
- inactive/reactivated Source;
- Source display-name behavior;
- legacy Source behavior.

Do not improvise destructive cleanup of test data.

Test-data cleanup must be:

- explicitly approved;
- bounded;
- verified;
- documented;
- separate from production data.

---

# 18. Validation-Discovered Defects

When validation discovers a defect:

1. preserve the evidence;
2. do not modify test data unnecessarily;
3. determine whether prior milestone conclusions are affected;
4. classify severity;
5. follow the prompt’s stop/continue rule;
6. do not repair unless authorized;
7. recommend the smallest scoped fix milestone.

The closeout should distinguish:

```text
confirmed defect
suspected defect
environment limitation
test-design limitation
not tested
```

---

# 19. Scope Discipline

Implement only the approved milestone.

Do not:

- perform unrelated refactors;
- fix nearby issues not required;
- change APIs outside scope;
- change models outside scope;
- change workflow semantics outside scope;
- change Source identity outside scope;
- change provenance outside scope;
- add speculative future support;
- broaden tests into unrelated systems without reason;
- add compatibility work solely to preserve disposable test data;
- reintroduce retired UI workflows.

When unrelated issues are discovered:

- document them under Known Limitations;
- recommend a Parking Lot entry;
- recommend a follow-up milestone;
- do not fix them without approval.

Prefer targeted changes over broad rewrites.

---

# 20. Stop Conditions

Stop and ask before coding when:

- the request conflicts with this document;
- the branch is wrong;
- unexpected dirty files exist;
- safety cannot be established;
- Source Intake would be bypassed;
- cloud acquisition would write directly to Vault, Drop Zone, Assets, or provenance;
- cleanup could affect anything outside verified temporary staging;
- code materially differs from prompt or recon;
- an unapproved migration or backfill is required;
- destructive behavior was not explicitly scoped;
- Source identity semantics must change;
- provenance semantics must change;
- local/external behavior may be broken by provider-specific work;
- provider behavior may be broken by filesystem work;
- secrets might be exposed;
- broad refactoring appears necessary;
- several product-relevant implementations remain unresolved;
- required filenames are unclear;
- an additional report file appears necessary;
- an existing proven pathway would be duplicated;
- a new framework or persistence model appears necessary;
- required manual, physical, or provider validation cannot be completed.

Use the escalation protocol when the issue exceeds a normal clarification question.

---

# 21. File and Data Safety

Before code can:

- delete;
- move;
- rewrite;
- hide;
- demote;
- import;
- clean;
- migrate;
- backfill;
- relink;
- merge records;

identify:

- exact files or records affected;
- positive verification protecting them;
- whether action is reversible;
- Source type;
- operator confirmation;
- reporting;
- provenance behavior;
- interruption behavior;
- recovery behavior.

For destructive or mutating actions prefer:

```text
dry run
explicit confirmation
bounded scope
positive verification
report output
protected/skipped counts
resumable or reviewable failure state
```

---

# 22. Migration and Backfill Rules

For milestones affecting:

- provenance;
- Source identity;
- Asset relationships;
- canonical fields;
- exact duplicate behavior;
- historical Source records;
- cleanup state;
- ingestion behavior;

consider:

- current data;
- forward-only compatibility;
- migration requirement;
- backfill requirement;
- recomputability;
- rollback;
- historical record protection;
- identity-version compatibility;
- test versus retained production data.

Do not silently add a migration or backfill.

Do not silently reinterpret old records.

Do not treat v1 and v2 identity contracts as interchangeable.

---

# 23. UI and UX Rules

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

Current ownership boundary:

### Ingestion owns

- Create Source;
- Select Source;
- Run Ingestion;
- Last Source Intake Summary;
- Known Sources;
- Source Intake History;
- Source Details;
- safe Source management.

### Admin owns

- background/system operations;
- Duplicate Processing;
- Face Processing;
- Place Geocoding;
- Display Preview Generation;
- Live Photo Pairing;
- runtime/system status.

Admin is not a parallel ingestion interface.

Do not reintroduce duplicate controls for:

- Source Intake;
- Source Registry;
- Known Sources;
- Source Intake History;
- iCloud Intake;

into Admin unless explicitly scoped.

Use Advanced Details for:

- endpoint IDs;
- fingerprints;
- canonical paths;
- identity evidence;
- internal run IDs;
- provider diagnostics;
- report paths;
- technical conflicts;
- low-level counters;
- low-level timings.

Do not make the operator choose a value already determined by Source identity or workflow context.

---

# 24. Runtime and Deployment Rules

Preserve Windows development behavior unless a milestone targets Linux or mini-server deployment.

Current development script path:

```powershell
.\scripts\runtime\start_photo_organizer_dev.ps1
```

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

Do not place live PostgreSQL data on an unvalidated mapped NAS share.

Linux deployment requires explicit consideration of:

- Linux Source identity providers;
- removable-media identity;
- Optical probing;
- mount-path behavior;
- permissions;
- NAS mount behavior;
- Runtime Root resolution.

---

# 25. Testing and Validation

Run the most relevant validation available.

Possible validation includes:

- focused unit tests;
- integration tests;
- API tests;
- full backend suite;
- frontend lint;
- frontend production build;
- migration checks;
- database queries;
- dry runs;
- runtime health checks;
- report inspection;
- browser smoke tests;
- physical-device validation;
- provider validation;
- approved live workflow tests.

Do not claim full validation when only partial checks were run.

Distinguish:

```text
unit validation
integration validation
database validation
API validation
manual UI validation
physical-device validation
live provider validation
production-runtime validation
```

Do not describe:

- automated tests as live validation;
- API success as proof of correct DB provenance;
- one Source Type as validation of all Source Types;
- a mocked provider test as live provider validation;
- application startup as complete workflow validation.

When required manual or physical validation has not occurred, describe the milestone as partially validated.

When a check cannot run:

- state why;
- identify what remains untested;
- distinguish implementation capability from environment limitation;
- identify the smallest remaining manual test.

Do not run live ingestion or destructive operations unless explicitly approved.

---

# 26. Closeout Requirements

Create exactly one human-authored closeout per milestone.

Do not create separate files such as:

```text
report.md
operations.md
coder_response.md
validation_notes.md
implementation_notes.md
```

unless explicitly requested.

The closeout filename must match the prompt basename by replacing:

```text
_prompt.md
```

with:

```text
_closeout.md
```

Runtime-generated reports, screenshots, and query exports are allowed.

Reference them from the closeout.

---

## 26.1 Standard Closeout Structure

Use this structure unless the prompt requires something different:

```markdown
# Milestone <number> — <title>

## 1. Repository State
Branch, HEAD, and working tree.

## 2. Scope Completed
What was implemented or validated.

## 3. Operational Behavior
How the feature works for the operator.

## 4. Files Changed
Added, modified, and deleted files.

## 5. API / Data Model / Persistence Changes
Only when applicable.

## 6. Architecture and Authority Boundaries
Existing authorities reused and boundaries preserved.

## 7. Safety Boundaries Preserved
What was intentionally not changed.

## 8. Validation Performed
Commands and results.

## 9. Provenance / Data Integrity Evidence
Required when touching ingestion, exact duplicates, Source identity,
cleanup, or provenance.

## 10. Live / Manual Validation
Operator, physical-device, provider, or runtime testing.

## 11. Untested Behavior
Anything not validated and why.

## 12. Deviations from Prompt
Anything omitted, changed, or interpreted differently.

## 13. Known Limitations
Remaining issues and environment limitations.

## 14. Recommended Next Milestone
The next logical action.

## 15. Git Status
git status --short and relevant diff summary.
```

The closeout must distinguish:

```text
confirmed
inferred
not tested
blocked
```

Append post-closeout validation to the same file.

Do not create another closeout.

---

# 27. Documentation Discipline

Prompt and closeout files are the primary detailed milestone record.

Update global documents only when a milestone changes:

- architecture;
- workflow;
- Source identity;
- ingestion model;
- provenance model;
- safety model;
- deployment;
- major operator behavior;
- milestone process.

For documentation version changes:

- create the requested new version;
- preserve historical milestone records;
- report superseded global files;
- do not overwrite unrelated files;
- ensure new current documents agree;
- use exact-file staging.

Do not create conversational artifact files such as:

```text
Coder response.md
Agent notes.md
Discussion summary.md
```

unless requested.

---

# 28. Performance Awareness

Consider:

- ingestion time;
- query efficiency;
- UI responsiveness;
- background workload;
- disk effects;
- network effects;
- NAS latency;
- cloud latency;
- large-library scale.

Expensive operations include:

- duplicate lineage;
- Face Processing;
- Visual Enrichment;
- iCloud acquisition;
- Source Intake;
- cleanup scans;
- NAS scans;
- external-device scans;
- AI inference;
- preview generation.

Do not optimize speculatively.

When performance is observed but out of scope:

- document it;
- identify likely phase;
- recommend a future milestone;
- do not expand the current milestone without approval.

---

# 29. Success Criteria

A coding-agent session is successful when:

- approved scope is completed;
- the correct branch is used;
- the recon roadmap is followed or a clear escalation is raised;
- unnecessary architecture is avoided;
- existing authorities are reused;
- unrelated systems remain untouched;
- dirty files are identified before coding;
- core safety boundaries are preserved;
- Asset identity and provenance remain distinct;
- exact duplicate behavior preserves valid Source origin;
- repeated intake avoids provenance noise;
- skipped/deferred inventory is not misrepresented as successful provenance;
- Source Endpoint, Source Profile, Observed Path, and Runtime Root remain distinct;
- Source Selection and dispatch remain backend-authoritative;
- validation is appropriate and honestly reported;
- validation-only work remains non-mutating;
- physical/provider limitations are clearly identified;
- exactly one correctly named closeout is created;
- limitations and deviations are documented;
- the working tree remains understandable;
- the change set is logically reviewable;
- the User can safely test, commit, merge, and continue;
- the implementation is simpler to maintain than an overbuilt alternative.
