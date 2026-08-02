# PROJECT_WORKFLOW_v7.md

## Document Status

**Version:** v7
**Project phase:** v1.0 stabilization with Linux-server Development and isolated Test foundations operational
**Current architecture:** Windows client/operator + Linux authoritative repository/runtime + Synology NAS durable-storage/backup infrastructure
**Current deployment branch:** `feature/deployment-linux-runtime`
**Current workflow emphasis:** milestone discipline, reconnaissance as implementation roadmap, evidence-based validation, provenance protection, clean branch lifecycle, cost-aware coding-agent use, environment-aware operations, and reliable continuation between chats and tools.

### Update Scope

This v7 revision preserves the established application and deployment workflow.

It does not introduce a materially different deployment methodology.

Changes are limited to aligning the workflow with the current architecture:

```text
Windows workstation
→ operator, browser, VS Code client, Remote SSH, tunnels,
  administration/recovery access, and general filesystem Source access node

Linux mini-server
→ authoritative editable repository, Development runtime, Test runtime,
  Docker execution, PostgreSQL, Redis, application storage, and GPU compute

Synology NAS
→ mounted durable-storage and backup infrastructure,
  not current live Development/Test application or database storage
```

The provenance workflow remains unchanged pending the separate post-12.64 documentation reconciliation.

---

## 1. Purpose

This document defines the working collaboration model between:

- **User / Product Owner**
- **ChatGPT / Architect and Planner**
- **Coder / Implementation Agent in VS Code or a similar coding environment**

This workflow exists to keep development:

- milestone-driven;
- safe;
- understandable;
- well documented;
- portable across chats and tools;
- resistant to mixed commits;
- resistant to scope drift;
- cost-aware when using AI coding agents;
- aligned with current architecture;
- protective of provenance and data integrity;
- recoverable across long milestone arcs;
- reviewable through clean Git history;
- explicit about which machine, terminal, environment, and authority are involved.

The project uses AI tools, but the User remains the final Product Owner and decision maker.

The workflow also ensures that:

```text
reconnaissance becomes a usable implementation roadmap;
implementation does not repeat unnecessary broad analysis;
provenance and architecture decisions remain explicit;
completed milestone arcs are merged and validated safely;
deployment work remains controlled and evidence-based;
current project documents become the durable source of truth.
```

---

## 2. Working Principles

The workflow is governed by these principles:

```text
Design before implementation when risk is unclear.
Reconnaissance before coding when code reality is uncertain.
Implementation follows approved scope.
Validation proves behavior.
Provenance and data integrity require evidence.
User testing confirms real-world usability.
Git history preserves logical work units.
Documentation records actual behavior.
Commands identify their execution environment.
Deployment changes require explicit authority.
```

Additional principles:

- Product intent should be translated into explicit implementation outcomes.
- The safest simple architecture is preferred over parallel systems.
- Existing authoritative workflows should be reused rather than duplicated.
- New scope discovered during implementation should normally be deferred.
- A milestone must not silently broaden into a different milestone.
- Validation-only work must not silently become implementation work.
- Coding-agent cost should be reduced through focused prompts and targeted reading, not by reducing safety.
- Architectural and safety assumptions should be verified against the repository before implementation.
- Windows, Linux, Development, Test, NAS, and future Production must not be treated as interchangeable execution contexts.
- Repository edits, runtime mutations, and live validation are separate authorities.
- Existing Development, Test, Portainer, NAS, and other shared-host resources must be protected from unrelated work.

---

# Part I — Roles and Responsibilities

## 3. User / Product Owner

The User:

- defines product goals and priorities;
- decides intended user behavior;
- approves architecture and workflow decisions;
- reviews proposed milestone scope;
- approves milestone sequencing;
- saves milestone prompts into the repository;
- provides prompts to the Coder;
- brings Coder questions back to ChatGPT;
- tests completed work in the approved target environment;
- performs or authorizes live validation;
- reports real-world behavior;
- provides screenshots, logs, error output, and usability feedback;
- confirms milestone completion before final commit;
- usually manages Git commits and pushes;
- explicitly authorizes Coder Git write commands when desired;
- explicitly authorizes Docker, database, NAS, deployment, and other live mutations;
- decides whether completed feature branches are retained or deleted;
- maintains or approves project documentation organization;
- decides when a project chat should be continued in a new conversation.

The User is not expected to translate product intent into code-level instructions alone.

ChatGPT and the Coder should make technical implications understandable before requiring a product decision.

---

## 4. ChatGPT / Architect and Planner

ChatGPT:

- helps design system architecture;
- helps sequence milestone arcs;
- identifies when reconnaissance is needed;
- identifies when direct implementation is safe;
- writes structured milestone prompts;
- names prompt and closeout files explicitly;
- defines scope and out-of-scope boundaries;
- defines authority and safety boundaries;
- defines validation evidence;
- identifies the correct execution environment for commands;
- anticipates likely Coder questions;
- answers Coder questions clearly and decisively;
- keeps answers aligned with current repository facts;
- distinguishes design assumptions from observed implementation facts;
- interprets Coder closeouts;
- interprets User testing feedback;
- determines whether a milestone is complete;
- recommends fixes or follow-up milestones;
- recommends Git staging and commit structure;
- recommends branch creation and merge strategy;
- proposes documentation updates;
- prepares continuation-chat handoffs;
- writes delta-focused prompts that reference standing coding-agent rules;
- protects Development, Test, NAS, and future Production boundaries.

ChatGPT should determine the appropriate milestone mode:

```text
reconnaissance-only
implementation-after-reconnaissance
direct small implementation
validation-only
documentation-only
bug-fix follow-up
deployment or operational validation
```

ChatGPT should also determine the appropriate reasoning level when material:

```text
high
medium
lower
```

ChatGPT should not merely restate the User’s request.

It should convert product intent into an implementation-ready scope containing:

```text
strategy
intent
required outcome
authority boundaries
environment and terminal
out of scope
validation evidence
stopping conditions
escalation conditions
```

ChatGPT should not rely on chat memory alone when current repository documents, prompts, closeouts, code evidence, or deployment guides are available.

---

## 5. Coder / Implementation Agent

The Coder:

- reads the milestone prompt;
- follows `docs/context/coding_agent_rules_v7.md` once that document is active;
- performs Git preflight before coding;
- confirms the authoritative repository and current branch;
- performs reconnaissance when requested or required;
- inspects targeted implementation paths;
- uses approved reconnaissance closeouts as implementation roadmaps;
- asks clarification questions before implementing uncertain behavior;
- escalates when the approved plan conflicts with code reality;
- keeps changes tightly scoped;
- avoids speculative refactoring;
- avoids unrelated cleanup;
- preserves existing behavior unless change is explicitly approved;
- validates the implementation;
- creates one closeout document;
- reports deviations;
- reports known limitations;
- reports Git state;
- stops before unsafe scope expansion;
- does not run unauthorized Git write commands;
- does not run unauthorized Docker, database, NAS, deployment, or destructive runtime commands;
- does not read or print protected secrets or configuration without explicit scope and authorization.

The Coder should not:

- reinterpret product behavior without approval;
- introduce a parallel engine when an existing authority can be reused;
- change provenance semantics incidentally;
- change Source identity semantics incidentally;
- broaden cleanup or destructive behavior;
- silently add migrations or backfills;
- treat frontend values as backend execution authority;
- repeat broad repository reconnaissance when an approved roadmap already exists;
- continue searching merely to create the appearance of thoroughness;
- assume Windows paths when working in the authoritative Linux repository;
- assume Linux Source identity exists because the application runtime is on Linux;
- rebuild, recreate, replace, or remove containers without authorization;
- use ad hoc Docker commands to bypass missing Test promotion or rollback workflows.

Coder Git write commands such as the following require explicit authorization:

```text
commit
push
reset
rebase
merge
tag
checkout
switch
stash
branch creation or deletion
```

Read-only Git commands are expected during preflight and validation.

---

# Part II — Project Documentation

## 6. Core Project Documents

The current system should remain understandable through:

```text
project_context_v7.md
project_architecture_v7.md
project_workflow_v7.md
coding_agent_rules_v7.md
canonical_parking_lot_v7.md
MILESTONE_HISTORY.md
v1.0 release roadmap
milestone prompt files
milestone closeout files
deployment guides
deployment milestone prompt and closeout files
```

These documents support:

- transition to new chats;
- onboarding future contributors;
- reduction of reliance on chat history;
- architectural consistency;
- preservation of product decisions;
- implementation history;
- deployment continuity;
- recovery after a long pause.

Global documents describe current project truth.

Application milestone prompts and closeouts preserve application-history truth.

Deployment milestone prompts and closeouts preserve server, runtime, environment, and operational-history truth.

---

## 7. Documentation Authority

When current documents conflict with old chat recollection:

```text
current repository documentation
+ current code
+ approved milestone closeouts
+ approved deployment guides and deployment closeouts
```

should be treated as more authoritative than old conversational memory.

Documentation should describe actual behavior, not merely intended behavior.

When a major implementation changes architecture or product state, relevant global documents should be updated.

Not every small milestone requires a global documentation update.

Operational detail should remain in maintained operator and deployment guides when duplicating it in a global context document would create drift.

---

## 8. Milestone Documentation Locations

### Application milestones

Application-functionality milestone documentation is organized under:

```text
docs/milestones/
```

Milestone parent folders may use an arc-specific structure such as:

```text
docs/milestones/milestone_012/012.064_unified_intake_provenance_verification/
```

or another approved project structure.

### Deployment milestones

Server construction, runtime migration, environment isolation, deployment validation, and deployment operations are documented under:

```text
docs/server_deployment/
docs/server_deployment/deployment_milestones/
```

Deployment prompt and closeout files remain beside one another.

Application milestone history remains focused on application functionality.

Deployment milestones do not need to be duplicated into the application milestone-history document.

---

# Part III — Prompt and Closeout Standards

## 9. Prompt and Closeout Naming Standard

### Application milestone filename pattern

Every application milestone prompt must explicitly state:

- the exact prompt filename;
- the exact closeout filename.

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

### Deployment milestone filename pattern

Deployment milestones use the established separate sequence:

```text
<deployment_number>_deployment_<exact_snake_case_name>_prompt.md
<deployment_number>_deployment_<exact_snake_case_name>_closeout.md
```

Example:

```text
010_deployment_architecture_documentation_reconnaissance_prompt.md
010_deployment_architecture_documentation_reconnaissance_closeout.md
```

Rules for both forms:

- no spaces;
- lowercase snake case for the descriptive portion;
- prompt and closeout use the same basename;
- replace `_prompt.md` with `_closeout.md`;
- do not invent a different closeout name;
- do not create a separate report file unless explicitly required.

### Application milestone arc numbering

A new application milestone arc should normally begin with:

```text
xx.xx.0
```

Follow-up actions increment:

```text
xx.xx.1
xx.xx.2
xx.xx.3
```

Deployment milestones use their independent sequential numbering and do not consume application milestone numbers.

---

## 10. Prompt Composition Standard

A good milestone prompt should define:

```text
strategy
intent
required outcome
current context
authoritative repository
target environment
command execution location
scope
out of scope
authority boundaries
safety boundaries
expected implementation shape
validation evidence
deliverables
stopping conditions
escalation conditions
definition of done
```

Prompts should describe required behavior and architectural boundaries without unnecessary micromanagement.

Potential tools, libraries, files, services, or functions may be mentioned when helpful.

They should not be over-prescribed unless:

- the mechanism is part of the safety contract;
- reconnaissance established an exact implementation path;
- a specific existing authority must be reused;
- introducing alternatives would create risk.

Prompts should be complete enough to execute, but not longer merely because more context is available.

---

## 11. Preferred Prompt Structure

Milestone prompts should generally use:

1. Title
2. Required file names
3. Reasoning level
4. Milestone mode
5. Goal
6. Background and current context
7. Authoritative repository and target environment
8. Required documents or closeouts to read
9. Scope
10. Out of scope
11. Architecture and authority boundaries
12. Backend requirements, if applicable
13. Frontend requirements, if applicable
14. Data/provenance requirements, if applicable
15. Runtime/deployment requirements, if applicable
16. Safety boundaries
17. Validation checklist
18. Manual or live validation plan
19. Escalation and stop conditions
20. Deliverables
21. Definition of done
22. Required closeout structure
23. Recommended next milestone

Standing instructions should include:

```text
Read and obey docs/context/coding_agent_rules_v7.md.
Create one closeout document only.
Do not create a separate report file.
Use the exact closeout filename.
Do not run Git write commands unless explicitly authorized.
Do not mutate Docker, database, NAS, or deployment state unless authorized.
Escalate before materially broadening scope.
```

Safety-sensitive prompts should repeat the most important safety rules directly even when they also appear in standing documents.

---

## 12. Prompt Handoff Formatting

Coder handoff prompts should be delivered as one complete copyable block.

Rules:

- commentary outside the block should be minimal;
- avoid broken nested code fences;
- preserve all prompt headings in one block;
- answers intended for repasting to the Coder should be self-contained;
- commands should identify their execution environment;
- Git commands should normally appear in one complete Linux-shell block when acting on the authoritative server repository;
- Windows PowerShell blocks should be used only for Windows-specific operations;
- do not scatter a single Git operation across multiple disconnected command blocks unless troubleshooting requires observation between stages.

---

## 13. Prompt File Lifecycle

### Initial prompt commit

The initial prompt should normally be committed before Coder handoff.

Purpose:

- preserve the original instruction state;
- create a durable implementation baseline;
- reduce ambiguity between coding sessions;
- prevent the active prompt from existing only in chat.

Recommended commit message:

```text
Docs: add <milestone> <short name> prompt
```

### Prompt addenda and Coder Q&A

Coder questions and approved answers should be appended to the same prompt file.

Recommended headings:

```markdown
## Original Prompt

## Coder Questions / Answers Round 1

## Coder Questions / Answers Round 2

## Final Lock-ins
```

Minor clarifications do not require a separate commit each time.

It is acceptable for the active prompt to remain modified during implementation when:

- the initial prompt was already committed;
- the dirty file is the active prompt;
- the changes are expected Q&A or lock-ins;
- the User confirms the modification is intentional.

### Material prompt changes

A prompt update should be committed before implementation continues when it materially changes:

- scope;
- safety boundaries;
- provenance;
- Source identity;
- ingestion authority;
- schema;
- migrations;
- backfills;
- Vault behavior;
- cleanup or destructive behavior;
- live-operation approval;
- Docker or deployment authority;
- database or NAS authority;
- credential/session behavior;
- prompt or closeout filename;
- implementation direction;
- handoff to another Coder after a long pause.

### Final prompt state

At final milestone commit, the prompt should contain:

- original scope;
- material Q&A;
- final lock-ins;
- approved safety or implementation changes.

The final milestone commit normally includes:

```text
implementation files
updated prompt file
one closeout file
```

Documentation-only reconnaissance may commit the prompt and closeout as one logical evidence package when explicitly approved.

---

## 14. Single Closeout File Standard

The Coder should create exactly one human-authored closeout per milestone/action.

Do not create separate:

```text
report.md
operations.md
coder_response.md
implementation_notes.md
validation_notes.md
```

unless explicitly requested.

Application-generated artifacts remain allowed:

```text
JSON run reports
cleanup reports
import reports
logs
screenshots
diagnostic exports
database query output
deployment validation evidence
```

These artifacts should be referenced from the closeout when relevant.

They do not replace the closeout.

---

## 15. Required Closeout Structure

Use this structure unless the milestone prompt explicitly modifies it:

```markdown
# Milestone <number> — <title>

## 1. Scope Completed
What was implemented or validated.

## 2. Operational Behavior
How the system now behaves.

## 3. Files Changed
Added, modified, and deleted files.

## 4. API / Data Model / Persistence Changes
Only when applicable.

## 5. Architecture and Authority Boundaries
Existing authorities reused and boundaries preserved.

## 6. Safety Boundaries Preserved
What was intentionally not changed.

## 7. Validation Performed
Tests, builds, database checks, reports, and manual checks.

## 8. User / Live Validation
What the User validated after implementation.

## 9. Deviations from Prompt
Anything changed, omitted, or interpreted differently.

## 10. Known Limitations
Known gaps and deferred work.

## 11. Recommended Next Milestone
The next logical action.

## 12. Git Status
Branch, git status --short, and relevant diff summary.
```

Deployment closeouts may additionally include:

```markdown
## Environment Identity
Host, Compose project, ports, networks, volumes, configuration path,
release identity, and affected shared-host resources.

## Live Mutation Record
Exact authorized runtime actions, safeguards, and observed result.
```

For provenance or data-integrity work, include:

```markdown
## Provenance Evidence
Database, API, report, or runtime evidence supporting the conclusion.
```

The closeout must distinguish:

- confirmed facts;
- assumptions;
- inferences;
- reconstructed evidence;
- untested behavior.

---

# Part IV — Milestone Modes

## 16. Reconnaissance-Only Milestone

Use reconnaissance-only when:

- code reality is uncertain;
- architecture spans multiple systems;
- safety boundaries are unclear;
- implementation shape may depend on current persistence;
- provenance semantics may be affected;
- migration/backfill needs are unknown;
- a broad UI or orchestration change is proposed;
- deployment or runtime behavior needs mapping.

The Coder should not edit implementation files.

A reconnaissance milestone may create only:

- the approved prompt file;
- one reconnaissance closeout;
- explicitly authorized documentation updates.

Expected reconnaissance output:

```text
current implementation map
relevant files and functions
authority boundaries
data and schema implications
provenance implications
current failure behavior
environment and runtime implications
recommended implementation shape
exact likely files to change
tests to run
manual validation requirements
risks
blockers
escalation conditions
implementation stopping conditions
```

Reconnaissance is not merely information gathering.

For approved work, it should become the implementation roadmap.

---

## 17. Implementation-After-Reconnaissance Milestone

Use after a reconnaissance plan has been reviewed and approved.

The implementation prompt should identify the reconnaissance closeout as the primary roadmap.

Coder reading order:

```text
1. coding_agent_rules_v7.md
2. implementation prompt
3. approved reconnaissance closeout
4. targeted implementation files
5. additional context only when needed
```

The Coder should not repeat broad repository exploration unless:

- the repository changed materially;
- the reconnaissance closeout is incomplete;
- targeted inspection contradicts the reconnaissance;
- a safety-relevant path was missed.

The implementation should follow the approved shape and escalate if reality differs materially.

---

## 18. Direct Small Implementation Milestone

Use for low-risk, tightly bounded changes such as:

- copy changes;
- documentation updates;
- isolated display fixes;
- small tests;
- narrow non-destructive bug fixes;
- mechanical naming corrections.

Even small prompts should:

- reference `coding_agent_rules_v7.md`;
- state scope and out of scope;
- require validation;
- require one closeout;
- prohibit unrelated changes.

---

## 19. Validation-Only Milestone

Use when the purpose is to establish evidence about current behavior without changing implementation.

Examples:

- provenance retesting;
- cross-Source duplicate validation;
- changed-drive-letter behavior;
- NAS path validation;
- Optical eject/reinsert behavior;
- Development runtime smoke testing;
- Test environment validation;
- Production runtime smoke testing;
- backup/restore rehearsal;
- performance baselining.

A validation-only milestone should:

- define the target environment;
- define the test matrix;
- define controlled test data;
- define database evidence;
- define report evidence;
- define API evidence;
- define expected pass/fail criteria;
- define whether testing stops on critical failure;
- prohibit implementation changes unless separately approved;
- prohibit unapproved runtime mutation.

A validation milestone must not silently become a repair milestone.

When a defect is found:

```text
document the evidence;
classify severity;
continue or stop according to the prompt;
do not repair outside approved scope;
recommend a separately scoped implementation milestone.
```

---

## 20. Documentation-Only Milestone

Use for:

- global context refresh;
- architecture refresh;
- workflow refresh;
- coding-agent-rules refresh;
- milestone-history updates;
- roadmap updates;
- Parking Lot consolidation;
- chat handoff documents;
- deployment documentation reconciliation.

Documentation-only work should:

- reflect current code and closeouts;
- avoid inventing unimplemented behavior;
- clearly distinguish current state from future direction;
- preserve historical milestone documents;
- use exact-file staging;
- avoid live Docker, database, NAS, or deployment inspection unless separately authorized;
- identify when a detail belongs in an operator guide rather than a global document.

---

## 21. Bug-Fix Follow-Up Milestone

Use when live validation reveals a contained defect.

A follow-up may be:

```text
same milestone closeout addendum
small .1 follow-up milestone
tracked bug-fix document
Parking Lot item
deployment follow-up milestone
```

Choice depends on:

- severity;
- scope;
- safety impact;
- whether the original milestone can still be considered complete;
- whether implementation has already been committed;
- whether runtime state or release identity is affected.

A bug fix should not be hidden inside unrelated later work.

---

# Part V — Reasoning-Level Guidance

## 22. High Reasoning

Use High reasoning for:

- architecture;
- reconnaissance;
- provenance;
- Source identity;
- ingestion authority;
- cleanup or destructive work;
- schema design;
- migrations and backfills;
- credential/session handling;
- ambiguous cross-system behavior;
- Production deployment architecture;
- backup and recovery design;
- environment isolation;
- candidate promotion and rollback;
- safety-sensitive workflow redesign.

High reasoning should produce a concrete roadmap, not endless exploration.

---

## 23. Medium Reasoning

Use Medium reasoning for:

- targeted implementation after approved reconnaissance;
- bounded backend changes;
- bounded frontend changes;
- test implementation;
- closeout creation;
- implementation-level debugging;
- targeted validation automation;
- bounded operator-script changes with approved architecture.

Medium reasoning is normally appropriate when:

- architecture is already approved;
- authority boundaries are known;
- likely files are identified;
- scope is bounded.

---

## 24. Lower Reasoning

Use lower reasoning for:

- narrow documentation edits;
- simple copy changes;
- mechanical updates;
- small isolated tests;
- low-risk formatting corrections.

Lower reasoning should not be used merely to reduce cost when architecture, runtime state, or data integrity is uncertain.

---

# Part VI — Standard Workflow Cycle

## 25. Step 1 — Milestone Definition

ChatGPT drafts the milestone prompt.

The milestone should state:

- milestone mode;
- reasoning level;
- exact file names;
- goal;
- context;
- authoritative repository;
- target environment;
- command execution location;
- approved architecture;
- scope;
- out of scope;
- validation;
- escalation;
- definition of done.

The User reviews and approves the prompt.

---

## 26. Step 2 — Branch and Repository Preflight

The authoritative editable repository is:

```text
/home/chuck/projects/photo-organizer-dev
```

Normal Git and repository commands run in:

```text
VS Code Remote SSH / Linux terminal on henderson-server1
```

Before a new implementation arc begins:

```bash
cd /home/chuck/projects/photo-organizer-dev
git branch --show-current
git status --short
git log --oneline --decorate -5
git fetch origin
```

Normal starting state:

```text
expected branch
working tree clean
local branch synchronized with its upstream
```

For a substantial new application arc, the normal lifecycle remains:

```text
main
→ new feature branch
→ milestone prompts and implementation
→ arc validation
→ final documentation
→ merge to main
→ validate merged main
→ optionally delete branch
```

An explicitly approved long-running deployment or documentation branch may continue across related deployment milestones when:

- the branch purpose remains current;
- the worktree is clean;
- the branch is synchronized with its upstream;
- the next work remains within the approved branch arc;
- the Product Owner approves continuing there.

Do not continue new unrelated work on a completed feature branch merely because it still exists.

The Windows administrative/recovery clone is not the normal editable repository.

---

## 27. Step 3 — Save and Commit Prompt

The User saves the prompt under its exact filename.

Recommended sequence in the **VS Code Remote SSH / Linux terminal**:

```bash
cd /home/chuck/projects/photo-organizer-dev
git status --short

git add -- "<exact prompt path>"

git diff --cached --name-only
git diff --cached --stat
git diff --cached --check

git commit -m "Docs: add <milestone> <short name> prompt"
git push

git status --short
```

The staged file list should match the expected prompt file exactly.

Windows CRLF line endings should be normalized to Linux LF before commit when they cause whitespace-check failures.

---

## 28. Step 4 — Handoff to Coder

The User provides the prompt to the Coder.

The Coder:

- reads standing rules;
- reads the prompt;
- reads approved reconnaissance when applicable;
- performs Git preflight;
- confirms the authoritative repository and environment;
- inspects relevant paths;
- identifies conflicts;
- asks questions or escalates before coding when needed.

---

## 29. Step 5 — Coder Git Preflight

Before editing, in the authoritative Linux repository:

```bash
git branch --show-current
git status --short
git log --oneline --decorate -5
```

Expected state:

```text
correct branch
clean working tree
prompt committed
```

Allowed exception:

```text
only the active prompt is modified with expected Q&A/addenda
```

If other dirty files exist, the Coder must stop and classify them.

Classification:

```text
A. required prior-milestone follow-up
B. unrelated work
C. accidental/noise
D. required current-milestone work
```

The Coder must not revert, stage, commit, stash, discard, or move files without authorization.

---

## 30. Step 6 — Reconnaissance or Targeted Inspection

For a reconnaissance milestone, inspect broadly enough to produce the roadmap.

For implementation after reconnaissance, inspect only enough to confirm the roadmap and perform the targeted change.

Stop broad exploration when:

- the implementation path is known;
- the relevant authority is confirmed;
- affected persistence is understood;
- expected files are identified;
- validation is defined;
- further searching is unlikely to change the plan.

Do not continue repository-wide searching merely to appear thorough.

For safety-sensitive work, do not stop before confirming:

- authority;
- persistence;
- failure path;
- rollback or recovery implications;
- provenance impact;
- data migration needs;
- target environment;
- shared-host effects;
- whether live inspection or mutation is authorized.

---

## 31. Step 7 — Clarification Loop

Coder asks targeted questions.

The User brings questions to ChatGPT.

ChatGPT responds with:

- direct decisions;
- product lock-ins;
- architecture lock-ins;
- explicit deferrals;
- stopping conditions;
- answers concise enough to paste back.

Answers should be appended to the prompt when material.

Questions that reveal material scope changes should trigger a prompt update and possibly a new commit.

---

## 32. Step 8 — Escalation Protocol

Escalation is required when:

- code reality contradicts approved architecture;
- safe implementation requires new schema;
- safe implementation requires migration/backfill;
- provenance semantics would change;
- Source identity authority would change;
- cleanup or destructive behavior would broaden;
- frontend input would become backend authority;
- a parallel engine or duplicate workflow appears necessary;
- unrelated dirty files threaten commit isolation;
- required validation cannot be performed;
- implementation is materially larger than represented;
- the approved milestone cannot be completed safely;
- live runtime state contradicts tracked contract;
- a Development change would affect Test or future Production;
- a Docker, database, NAS, or deployment mutation is needed but not authorized;
- protected configuration or secret contents would need to be exposed;
- a missing promotion or rollback workflow would need to be bypassed.

Required escalation format:

```text
STATUS: ESCALATION REQUIRED

Observed conflict:
Why the approved plan cannot safely proceed:
Files, systems, and environments involved:
Data/provenance/runtime implications:
Smallest safe options:
Recommended decision:
```

The Coder should stop at the escalation point.

The Coder should not improvise through material architecture or safety conflicts.

---

## 33. Step 9 — Implementation

The Coder implements according to:

- approved prompt;
- approved reconnaissance;
- Q&A;
- final lock-ins;
- standing rules.

The Coder should:

- change only required files;
- reuse existing authorities;
- avoid speculative refactoring;
- avoid unrelated formatting;
- preserve existing behavior unless approved;
- add focused tests;
- document unavoidable deviations;
- keep generated artifacts out of milestone commits unless explicitly required;
- avoid Git write commands unless authorized;
- avoid runtime mutation unless authorized;
- preserve Development/Test isolation;
- preserve the Windows Source-provider boundary unless explicitly changing it.

---

## 34. Step 10 — Coder Validation

Validation may include:

- targeted unit tests;
- broader backend test suite;
- frontend lint;
- frontend production build;
- API checks;
- database queries;
- structured report review;
- operator self-tests;
- Compose rendering;
- container and image identity checks;
- manual workflow checks;
- `git diff --check`.

Validation should match milestone risk.

A small copy edit does not require a full live intake.

A provenance or ingestion change requires stronger evidence.

A Development code change normally requires:

```text
build affected image
recreate or replace affected Development container
check Development health
perform targeted application validation
```

A simple container restart is insufficient to activate repository edits because Development source is copied into images and is not bind-mounted.

A Test validation must preserve the existing candidate unless replacement is explicitly authorized and supported by an approved workflow.

---

## 35. Step 11 — Closeout Document

The Coder creates one closeout using the exact filename.

The closeout records:

- actual implementation;
- actual files;
- actual validation;
- affected environment;
- runtime mutations, when authorized;
- deviations;
- limitations;
- unresolved questions;
- Git state.

The closeout must not claim validation that was not performed.

When evidence is reconstructed rather than directly captured, it must be labeled as reconstructed.

---

## 36. Step 12 — User Testing

The User tests behavior in the approved target environment.

User testing may occur through:

- the Windows Development Operator;
- a browser reached through an SSH tunnel;
- VS Code Remote SSH;
- the server-side Development operator;
- the server-side Test operator;
- Windows filesystem Source workflows;
- controlled live media or Source validation;
- other explicitly approved tools.

User testing should focus on:

- real workflow;
- operator clarity;
- expected result;
- failure behavior;
- edge cases;
- usability;
- regression risk;
- environment isolation.

Screenshots, reports, and terminal output should be retained when useful.

For live operations, approval boundaries in the prompt must be followed.

---

## 37. Step 13 — Feedback and Fix Decision

The User reports results.

ChatGPT determines whether:

- milestone passes;
- closeout needs a live-validation addendum;
- a contained fix belongs in the current milestone;
- a `.1` application follow-up is required;
- a deployment follow-up milestone is required;
- a defect belongs in the Parking Lot;
- the milestone should remain open.

A feature should not be marked complete merely because automated tests passed if required manual behavior was not validated.

---

## 38. Step 14 — Final Staging and Commit

ChatGPT provides exact-file Git commands for the **VS Code Remote SSH / Linux terminal** unless a Windows-specific operation is required.

Preferred sequence:

```bash
cd /home/chuck/projects/photo-organizer-dev

git status --short
git diff --name-only
git diff --stat

git add -- "<specific implementation file>"
git add -- "<specific implementation file>"
git add -- "<exact prompt file if modified>"
git add -- "<exact closeout file>"

git diff --cached --name-only
git diff --cached --stat
git diff --cached --check

git commit -m "Milestone <number>: <summary>"
git push

git status --short
git log --oneline --decorate -5
```

Do not use:

```bash
git add .
```

unless:

- the entire dirty tree has been reviewed;
- every file belongs to the same logical commit;
- the User explicitly approves staging all files.

The staged file list must be compared against the expected milestone file list.

Unexpected staged files must be removed or explained before commit.

The Coder must not commit or push without explicit Product Owner authorization.

---

## 39. Step 15 — Documentation Updates

Potential updates:

- milestone prompt;
- milestone closeout;
- `MILESTONE_HISTORY.md`;
- `project_context_v7.md`;
- `project_architecture_v7.md`;
- `project_workflow_v7.md`;
- `coding_agent_rules_v7.md`;
- `canonical_parking_lot_v7.md`;
- v1.0 roadmap;
- new-chat intro;
- deployment guides;
- deployment milestone prompt and closeout.

When replacing a current global document version:

```text
create new version
review new version
stage new version
stage removal of superseded active version
verify exact add and removal paths
run whitespace check
commit together
```

Do not delete historical milestone prompts and closeouts merely because global documents were versioned.

Application milestone history does not need to absorb deployment milestone detail.

---

## 40. Step 16 — Arc Completion and Merge

A substantial feature branch should be merged only after:

- final milestone passes;
- closeout is complete;
- relevant global documentation is aligned;
- working tree is clean;
- branch is pushed;
- application behavior is acceptable.

A non-fast-forward merge may be used to preserve the arc as one visible unit.

Conceptual merge sequence:

```text
finish feature branch
→ update main
→ merge feature branch
→ inspect graph
→ push main
→ validate application from main
```

Do not begin the next unrelated arc before confirming the merge result.

An active deployment/documentation branch may remain open across related deployment milestones when explicitly approved.

---

## 41. Step 17 — Post-Merge Validation

Before declaring a major application arc closed, confirm:

```text
authoritative repository path is correct
current branch is main
working tree is clean
main contains the merge commit
origin/main matches local main
affected Development image is rebuilt when code changed
affected Development container is recreated or replaced
Development health passes
Development recovery status remains acceptable
targeted application smoke testing passes through the approved access path
Windows Source-access validation is performed when Windows-provider behavior changed
```

Exact commands should come from the maintained Development operator and recovery guides.

The obsolete Windows-host startup command is not the current runtime authority.

A Git merge may be correct even when a runtime command, environment issue, or operator procedure needs separate correction.

Post-merge runtime validation is therefore required for major arcs.

---

## 42. Step 18 — Branch Retention or Cleanup

Deleting a merged branch:

- does not remove merged commits from `main`;
- is optional;
- is organizational cleanup;
- should occur after merged-main validation.

Recommended practice:

```text
retain briefly after merge
validate main
delete when no longer useful as an active reference
```

Retaining merged branches is safe.

Too many stale branches may cause confusion.

New unrelated application work should begin from a new branch based on current `main`.

---

## 43. Step 19 — Next Milestone

ChatGPT proposes the next milestone and identifies its category:

- core feature;
- safety/guardrail;
- provenance validation;
- UX refinement;
- documentation;
- refactor/stabilization;
- deployment;
- validation-only;
- Parking Lot deferral.

The recommendation should explain why the milestone is logically next.

---

# Part VII — Provenance and Data-Integrity Workflow

## 44. Provenance Requires Explicit Scope

Milestones involving provenance must explicitly define:

- expected provenance behavior;
- Source Types in scope;
- Source Profile expectations;
- Source Endpoint expectations;
- Source-relative-path expectations;
- unique-file behavior;
- exact duplicate behavior;
- cross-Source duplicate behavior;
- repeated-run idempotency;
- failed/rejected behavior;
- skipped/deferred behavior;
- legacy-record behavior;
- database evidence;
- report evidence;
- migration or backfill policy.

Provenance must not be changed as an incidental side effect.

This section remains unchanged in principle pending the separate post-12.64 documentation reconciliation.

---

## 45. Provenance Evidence Standard

Provenance conclusions should be supported through one or more of:

```text
database records
API responses
Source Intake reports
run reports
controlled file hashes
Source Profile/Endpoint records
Source-relative paths
repeat-run comparisons
```

UI labels alone are not sufficient evidence of provenance correctness.

Intake summary counts alone are not sufficient evidence of provenance correctness.

---

## 46. Provenance Validation-Only Work

A provenance retest should normally begin as validation-only.

The prompt should define:

- controlled test files;
- known SHA-256 values;
- Source configuration;
- expected Asset count;
- expected Vault-file count;
- expected provenance count;
- expected Source relationships;
- expected repeat behavior;
- expected cross-Source behavior;
- cleanup of test data, when safe and explicitly approved.

When the retest discovers a defect:

```text
record exact evidence;
do not silently repair;
classify impact;
propose the smallest scoped fix milestone.
```

---

## 47. Migration and Backfill Considerations

Any milestone affecting:

- provenance tables;
- Source identity;
- Asset relationships;
- canonical fields;
- ingestion behavior;
- exact duplicate behavior;
- historical Source records;

must consider:

- current Development/Test/Production data;
- forward-only compatibility;
- migration requirements;
- backfill requirements;
- recomputability;
- rollback;
- legacy records;
- historical record protection.

Coder should raise these issues during reconnaissance or escalation.

---

# Part VIII — Cost-Aware Agentic Coding

## 48. Core Cost-Control Principles

- Keep durable rules in `coding_agent_rules_v7.md`.
- Keep prompts focused on the milestone delta.
- Use reconnaissance closeouts as roadmaps.
- Avoid rereading all global documents for small work.
- Identify likely files and systems when known.
- Use targeted inspection after reconnaissance.
- Split broad risky work.
- Stop broad exploration when the implementation path is established.
- Do not reduce safety checks merely to save tokens.
- Do not repeat explanations already available in standing documents.
- Use deployment guides and closeouts instead of rediscovering settled runtime facts.

---

## 49. Default Context Pattern

For most implementation prompts:

```text
Before coding:
1. Read docs/context/coding_agent_rules_v7.md.
2. Read this milestone prompt.
3. Read the approved reconnaissance closeout, if listed.
4. Inspect the targeted code paths.
5. Read broader context or deployment documents only when affected behavior remains unclear.
```

---

## 50. When Full Context Is Justified

Broader context reading is justified when work touches:

- architecture;
- provenance;
- Source identity;
- ingestion;
- Vault;
- cleanup;
- schema;
- migrations;
- credential/session handling;
- cross-cutting UI workflow;
- deployment;
- backup/recovery;
- environment isolation;
- promotion or rollback;
- broad runtime changes.

---

## 51. When to Split a Milestone

Split when:

- backend, frontend, migration, and destructive work are mixed;
- safety is not understood;
- reconnaissance may change the plan;
- User testing should precede the next stage;
- implementation would span unrelated systems;
- failure would be expensive;
- validation and repair should remain separate;
- live operation should be approved separately;
- Development and Test mutation would otherwise be mixed;
- promotion, rollback, and Production concerns would otherwise be conflated.

A milestone should not be split mechanically when one bounded implementation can be completed safely.

The workflow favors efficient grouping when risk is low.

---

## 52. Cost-Aware Stopping Rule

The Coder should stop searching when:

- required files are identified;
- existing authority is understood;
- persistence impact is known;
- implementation plan is stable;
- validation is defined;
- further search is unlikely to affect the plan.

The Coder should continue investigation when:

- provenance remains ambiguous;
- failure behavior is unknown;
- data migration risk exists;
- an authority boundary is unclear;
- cleanup or destructive scope is uncertain;
- existing tests contradict assumptions;
- runtime and tracked contract disagree;
- shared-host impact is unclear;
- required environment identity is unproven.

---

# Part IX — Git Discipline

## 53. Read-Only Git Reconnaissance

Expected before coding in the authoritative Linux repository:

```bash
git branch --show-current
git status --short
git log --oneline --decorate -5
```

Additional read-only commands may include:

```bash
git diff --name-only
git diff --stat
git diff
git ls-files
git branch --all
git rev-parse HEAD
git rev-parse '@{upstream}'
```

---

## 54. Exact Staging

Specific-file staging is the default.

Required verification:

```bash
git diff --cached --name-only
git diff --cached --stat
git diff --cached --check
```

The expected file list should be stated before commit.

Do not commit unexplained files.

When replacing a versioned global document, verify the exact old-file removal and new-file addition.

---

## 55. Logical Commit Grouping

Prefer separate commits for:

```text
initial prompt
material prompt Q&A
prior-milestone fix
unrelated maintenance
current implementation and closeout
reconnaissance prompt and closeout evidence
global documentation alignment
merge commit
tag or version update
```

Do not mix unrelated systems because they happen to be dirty simultaneously.

---

## 56. Branch Lifecycle

Recommended application branch lifecycle:

```text
updated main
→ clean tree
→ new descriptive feature branch
→ committed prompt
→ milestone work
→ validation
→ documentation alignment
→ merge to main
→ main runtime validation
→ optional branch deletion
```

Substantial application arcs should normally use a feature branch.

An approved deployment/documentation branch may continue across related deployment milestones.

Small documentation-only changes may be performed on the current approved branch when that matches project practice and the User approves.

---

# Part X — Runtime and Deployment Workflow

## 57. Environment and Terminal Identification

Every operational command block should identify where it runs.

Supported labels include:

```text
VS Code Remote SSH / Linux terminal
Windows PowerShell
Windows Development Operator
server-side Development operator
server-side Test operator
browser / Developer Tools
Synology DSM
Portainer
Cockpit
```

Do not provide an unlabeled command when running it in the wrong environment could create confusion or risk.

The authoritative repository is operated from the Linux terminal.

Windows PowerShell remains appropriate for Windows-specific Source access, SSH tunnels, and Windows operator tasks.

---

## 58. Current Development Runtime Workflow

Current Development authority:

```text
Host: henderson-server1
Repository: /home/chuck/projects/photo-organizer-dev
Compose project: photo-organizer-dev
Frontend: 127.0.0.1:13000
Backend: 127.0.0.1:18001
PostgreSQL: unpublished
Redis: unpublished
Storage mode: local
```

Current operator paths:

```text
scripts/operator/development/photo_organizer_dev_operator.sh
scripts/operator/windows/PhotoOrganizer-Development-Operator.ps1
```

Development source behavior:

```text
repository edit
→ rebuild affected image
→ recreate or replace affected container
→ health check
→ targeted validation
```

Development source is not bind-mounted into running containers.

A restart alone does not activate repository edits.

Routine start deliberately performs no build, pull, or container replacement.

Detailed command syntax belongs in the maintained Development operator and recovery guides.

---

## 59. Current Test Runtime Workflow

Current Test authority:

```text
Host: henderson-server1
Compose project: photo-organizer-test
Frontend: 127.0.0.1:13001
Backend: 127.0.0.1:18002
PostgreSQL: unpublished
Redis: unpublished
Storage mode: local
Protected configuration: /home/chuck/.config/photo-organizer/test.env
Release state: /home/chuck/.local/state/photo-organizer/test/release.json
```

Test characteristics:

- immutable full-SHA backend and frontend images;
- separately recorded image IDs;
- separate PostgreSQL, Redis, storage, networks, configuration, and release state;
- no runtime Source bind mounts;
- routine start restarts the preserved candidate;
- routine start does not rebuild or replace the candidate;
- Test is operated through the server-side Test operator;
- browser access uses an explicit SSH tunnel.

Current limitations:

```text
candidate replacement not implemented
rollback not implemented
Production promotion not implemented
Windows Test operator not implemented
```

Do not use ad hoc Docker commands to bypass these missing workflows.

---

## 60. Deployment and Operational Milestones

Deployment milestones should consider:

- Windows versus Linux host behavior;
- authoritative repository location;
- Docker services;
- Compose project identity;
- PostgreSQL placement;
- Redis placement;
- application storage;
- NAS mounts;
- Vault paths;
- permissions;
- Source identity providers;
- backup;
- restore;
- service supervision;
- promotion;
- rollback;
- logging;
- health checks;
- network access;
- secrets;
- release manifests;
- image identity;
- shared-host protection;
- exact stop conditions.

Deployment reconnaissance and implementation should normally be separate unless scope is narrow and already understood.

A deployment prompt must explicitly state whether the Coder may:

- run Docker commands;
- inspect live containers;
- start or stop services;
- build or pull images;
- create or remove containers;
- inspect or mutate volumes;
- inspect or mutate databases;
- access the NAS;
- read protected configuration;
- alter firewall, SSH, mount, or system services.

Silence is not authorization.

---

## 61. NAS and Storage Authority

Current NAS contract:

```text
Server mount: /mnt/nas/photo-organizer
Share source: //192.168.1.171/PhotoOrganizer
Protocol: CIFS / SMB 3.1.1
```

Current NAS role:

- durable-storage infrastructure;
- backup infrastructure;
- future archive/Production storage candidate.

Current NAS role is not:

- Development application-storage authority;
- Test application-storage authority;
- Development PostgreSQL storage;
- Test PostgreSQL storage;
- Development Redis storage;
- Test Redis storage;
- editable Git repository.

NAS access, permission changes, mount changes, and data mutation require explicit authorization.

Protected NAS credentials must not be printed or committed.

---

## 62. Production Boundary

Current Linux Production is not implemented.

Legacy Windows Production scripts, examples, and generic Compose artifacts remain tracked.

They are not the current approved Linux Production contract.

No milestone should infer that Production exists merely because Development and Test are operational.

Production work requires explicit design and validation for:

```text
Compose project
configuration
secrets
networking
storage authority
Vault
database
Redis
release identity
promotion
rollback
backup
restore
service supervision
cutover
```

---

# Part XI — Communication Rules

## 63. ChatGPT Communication

ChatGPT should:

- be decisive;
- explain important tradeoffs;
- avoid unnecessary complexity;
- preserve scope;
- anticipate implementation questions;
- give Coder-ready instructions;
- keep repastable answers self-contained;
- use exact filenames;
- use one complete prompt block;
- use one complete Git command block;
- label command execution environment;
- distinguish fact from assumption;
- recommend validation evidence;
- identify escalation triggers;
- avoid agreeing merely because the User suggested an idea;
- recommend against an approach when architecture or evidence indicates a better option;
- avoid treating current Test or Production capabilities as more complete than they are.

---

## 64. Coder Communication

Coder should:

- ask focused questions;
- challenge incorrect assumptions;
- report observed code reality;
- state when evidence is incomplete;
- report deviations;
- report validation honestly;
- identify the environment inspected or changed;
- use the required closeout filename;
- avoid broad unsolicited proposals;
- escalate before material scope expansion;
- state whether evidence is direct, inferred, or reconstructed.

---

## 65. User Communication

User should:

- provide product intent;
- validate real behavior;
- bring questions back to ChatGPT;
- save prompts exactly;
- approve live operations;
- confirm completion;
- share screenshots and output when useful;
- avoid committing before reviewing staged files;
- decide when to retain or delete branches;
- initiate documentation checkpoints at natural arc boundaries;
- confirm which terminal or tool is being used when troubleshooting environment-specific commands.

---

# Part XII — Scope and Safety Discipline

## 66. Scope Rules

- Each milestone must remain tightly scoped.
- New ideas normally move to the Parking Lot.
- Related low-risk work may be grouped deliberately.
- Unrelated systems should not be combined.
- Validation should match scope.
- No milestone should silently become a broader redesign.
- No validation-only milestone should silently become implementation.
- No UI milestone should alter backend authority incidentally.
- No compatibility work should be added solely to preserve disposable test data without approval.
- No Development milestone should silently mutate Test.
- No Test milestone should silently create Production behavior.
- No deployment milestone should silently alter application semantics.

---

## 67. Safety Rules

- Do not modify original Source media.
- Keep Vault immutable.
- Keep Source Intake authoritative.
- Keep cloud acquisition staging-only.
- Do not broaden cleanup.
- Do not change provenance without explicit scope.
- Do not change Source identity without explicit scope.
- Do not trust frontend execution values.
- Do not silently migrate identity versions.
- Do not perform destructive Git actions without authorization.
- Do not run live operations beyond approved limits.
- Do not mutate Docker, database, NAS, secrets, mounts, services, or deployment state without authorization.
- Do not expose application, PostgreSQL, or Redis publicly.
- Do not use ad hoc Test replacement or rollback commands.
- Preserve Development/Test isolation.
- Fail closed when identity, environment, authority, or data safety is unclear.

---

# Part XIII — Documentation Checkpoints and Chat Continuation

## 68. Documentation Checkpoint

A major documentation checkpoint is appropriate:

- after a major application arc;
- after architecture changes;
- after deployment milestones materially change runtime state;
- after branch merge;
- before a new development phase;
- before starting a continuation chat;
- before Production deployment work.

Checkpoint documents may include:

```text
project_context_v7.md
project_architecture_v7.md
project_workflow_v7.md
coding_agent_rules_v7.md
MILESTONE_HISTORY.md
canonical_parking_lot_v7.md
v1.0 roadmap
new-chat intro
deployment guides
latest application or deployment closeout
```

---

## 69. Chat and Context Health

A new continuation chat should be considered:

- after a major documentation refresh;
- after a large milestone arc;
- when current documents are ready to become the source of truth;
- when attachment reliability declines;
- when responses slow substantially;
- when settled decisions are repeatedly re-questioned;
- when answers become generic or inconsistent;
- when project state has materially changed.

Do not wait for severe degradation when a natural documentation boundary already exists.

---

## 70. Continuation Package

A continuation chat should begin with current copies of:

```text
project_context_v7.md
project_architecture_v7.md
project_workflow_v7.md
coding_agent_rules_v7.md
MILESTONE_HISTORY.md
canonical_parking_lot_v7.md
v1.0 release roadmap
latest relevant application milestone prompt
latest relevant application milestone closeout
latest relevant deployment milestone prompt
latest relevant deployment milestone closeout
short current-branch and Git-state summary
current Development/Test environment summary when relevant
```

The new chat should treat these documents as primary context.

Old chat recollection is secondary.

---

# Part XIV — Key Principles and Success Criteria

## 71. Key Principles

- Milestone-driven development
- Separation of design and implementation
- Reconnaissance as implementation roadmap
- Targeted implementation after reconnaissance
- Human-in-the-loop validation
- Validation-only work remains non-mutating
- Provenance claims require evidence
- Incremental system evolution
- Local-first architecture
- Non-destructive data handling
- Source and provenance preservation
- Backend-authoritative execution
- Correctness before optimization
- Safety before automation
- Clean Git history
- Clean branch lifecycle
- Exact prompt and closeout naming
- One closeout per milestone
- Specific-file staging
- Documentation based on actual behavior
- Cost-aware coding-agent use
- Explicit escalation before unsafe scope expansion
- Reliable post-merge validation
- Portable project context across chats and tools
- Authoritative Linux repository
- Explicit terminal and environment labeling
- Development/Test isolation
- Immutable Test release identity
- Product Owner authority over Git and live mutation
- Separate application and deployment histories

---

## 72. Success Criteria

This workflow is successful when:

- milestones are delivered predictably;
- the Coder knows exactly what to implement;
- architecture and authority boundaries remain clear;
- reconnaissance closeouts become useful implementation roadmaps;
- implementation does not repeat unnecessary broad reconnaissance;
- clarification loops are shorter;
- escalations happen before unsafe expansion;
- provenance and data-integrity conclusions are supported by evidence;
- validation-only milestones remain non-mutating;
- documentation overhead remains proportionate;
- prompt and closeout naming stays consistent;
- repeated boilerplate is reduced;
- coding-agent cost decreases without reducing quality;
- Git commits are logically grouped;
- staged files match expected files;
- unrelated work is not mixed;
- feature branches are merged cleanly;
- merged `main` is runtime-validated;
- Development edits are correctly rebuilt and applied;
- Test candidate identity is preserved;
- Development and Test mutable state remain isolated;
- Docker, database, NAS, and deployment changes occur only with explicit authority;
- commands run in the correct terminal and environment;
- regressions are minimized;
- global documents describe current truth;
- project state remains portable across chats;
- User confidence increases with each milestone;
- the system moves steadily toward safe v1.0 Production use.
