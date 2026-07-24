# PROJECT_WORKFLOW.md

## Purpose

Define the working collaboration model between:

- **User / Project Owner**

- **ChatGPT / Architect and Planner**

- **Coder / Implementation in VS Code or similar coding agent**

This workflow exists to keep development:

- milestone-driven

- safe

- understandable

- well documented

- portable across chats and tools

- resistant to mixed commits and scope drift

- cost-aware when using AI coding agents

The project uses AI tools, but the User remains the final product owner and decision maker.

---

## Roles

### User / Project Owner

The User:

- defines goals and priorities

- decides product behavior

- reviews proposed milestone scope

- saves milestone prompts into the repository

- provides prompts to coder

- brings coder questions back to ChatGPT

- tests completed work locally

- reports real-world behavior, screenshots, issues, and usability feedback

- confirms milestone completion before final commit

- manages git commits unless explicitly delegating a git action

- maintains or approves project documentation organization

---

### ChatGPT / Architect and Planner

ChatGPT:

- helps design system architecture and milestone sequence

- writes structured milestone prompts for implementation

- names prompt and closeout files explicitly

- anticipates likely coder clarification questions

- answers coder questions clearly and decisively

- keeps answers aligned with current system behavior and architecture

- interprets coder closeouts and user testing feedback

- identifies whether a milestone is complete or needs follow-up

- recommends git staging/commit structure

- proposes next milestones

- keeps scope controlled and avoids adding unrelated work mid-milestone

- recommends updates to global documentation when workflow or architecture changes

- writes delta-focused prompts that reference standing coding-agent rules when appropriate

ChatGPT should not rely on chat memory alone when current repository documents or closeouts are available.

---

### Coder / Implementation

Coder:

- implements milestone prompts in the codebase

- follows `docs/context/CODING_AGENT_RULES.md`

- performs codebase reconnaissance before coding when needed

- performs git preflight before coding

- stops and classifies dirty working-tree files before coding when unexpected files are present

- asks clarification questions before implementing uncertain behavior

- keeps changes tightly scoped to the approved milestone

- avoids modifying unrelated systems

- validates functionality locally

- creates one milestone closeout document after implementation

- reports deviations, validation results, known limitations, and recommended next steps

Coder should not run git write commands such as commit, push, reset, rebase, merge, tag, checkout, or stash unless explicitly authorized.

---

## Documentation Organization

### Core Project Documents

The system should remain representable through:

```text
PROJECT_CONTEXT.md
PROJECT_ARCHITECTURE.md or ARCHITECTURE_ROADMAP.md
MILESTONE_HISTORY.md
PROJECT_WORKFLOW.md
CODING_AGENT_RULES.md
Parking Lot documents
milestone prompt and closeout files
```

These documents enable:

- transition to new chats

- onboarding future contributors

- reducing reliance on chat history

- maintaining architectural consistency

- preserving product decisions and implementation history

---

### Milestone Documentation Location

Project milestone documentation is organized under:

```text
docs/milestones/
```

Milestone parent folders may use the pattern:

```text
XXX.XXX_short_description/
```

Example:

```text
docs/milestones/012.062_icloud_source_profile_run_planning/
```

Where:

- `012.062` represents milestone `12.62`

- the description identifies the milestone arc

- sub-milestones such as `12.62.1`, `12.62.2`, etc. live inside the same parent folder

The User may decide exact folder placement while the documentation structure evolves.

---

## Prompt and Closeout Naming Standard

### Required Filename Pattern

Every milestone prompt must explicitly state the exact required prompt filename and closeout filename.

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

- no spaces in filenames

- use lowercase snake case for the name portion

- the closeout must use the same basename as the prompt

- replace `_prompt.md` with `_closeout.md`

- do not invent a separate closeout name

- do not create a separate report file unless explicitly requested

### Milestone Arc Numbering

A new milestone arc should normally start at:

```text
xx.xx.0
```

Follow-up prompts, subprompts, addenda that become implementation actions, or approved secondary actions should increment:

```text
xx.xx.1
xx.xx.2
xx.xx.3
```

Example:

```text
12.75.0_source_identity_design_prompt.md
12.75.1_source_identity_device_probe_prompt.md
12.75.2_source_identity_ui_review_prompt.md
```

Broader changes to the overall `12.xx.x` numbering system should be discussed separately before changing the convention.

---

## Prompt File Lifecycle

### Initial Prompt Commit

The initial prompt file should be committed before handoff to coder.

Purpose:

- preserve the baseline instruction set

- allow coder to start from a known repository state

- reduce ambiguity when using different coding agents

- keep prompt history durable outside the chat

Recommended commit message:

```text
Docs: add <milestone> <short name> prompt
```

Example:

```text
Docs: add 12.75.0 source identity design prompt
```

---

### Prompt Addenda and Coder Q&A

If coder asks questions or ChatGPT provides clarification, append the Q&A to the same prompt file.

Recommended headings:

```markdown
## Original Prompt

## Coder Questions / Answers Round 1

## Coder Questions / Answers Round 2

## Final Lock-ins
```

Minor clarifications do not require a separate git commit each time.

It is acceptable for the active prompt file to remain modified during active implementation if:

- the prompt was already committed once before handoff

- the dirty file is only the active milestone prompt

- the User confirms the prompt modifications are expected

---

### When Prompt Addenda Should Be Committed Immediately

A prompt update should be committed before implementation continues if it materially changes:

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

- handoff to a different coder/session after a long pause

Recommended commit message:

```text
Docs: update <milestone> prompt with Q&A
```

---

### Final Prompt State

At final milestone commit, the prompt file should reflect the final instruction state, including material Q&A, addenda, and lock-ins.

The final milestone commit should generally include:

```text
implementation files
final prompt file
one closeout file
```

---

## Single Closeout File Standard

Coder should create exactly one human-authored closeout document per milestone/action.

Do not create separate:

```text
report.md
operations.md
coder_response.md
```

unless explicitly requested.

The closeout should contain all relevant implementation detail, validation, reporting, live-test addenda, deviations, and recommendations.

Application-generated runtime reports are allowed. Examples:

```text
JSON run reports
cleanup reports
import reports
logs
screenshots
diagnostic exports
```

These are runtime artifacts, not milestone closeout documents. They should be referenced from the closeout when relevant.

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

---

## Standing Coding-Agent Rules

A standing coding-agent rules document should be maintained at:

```text
docs/context/CODING_AGENT_RULES.md
```

Purpose:

- hold durable implementation rules

- reduce repeated safety boilerplate in milestone prompts

- make coding-agent sessions more consistent

- reduce coding-agent cost by allowing shorter delta-focused prompts

- preserve project safety boundaries

Milestone prompts should reference this file instead of repeating every standing rule.

However, safety-critical or destructive milestones should still repeat the most important safety rules directly in the milestone prompt.

---

# Standard Workflow Cycle

## Step 1 — Milestone Definition

ChatGPT generates a structured milestone prompt.

For most implementation milestones, prompts should be delta-focused:

```text
standing rules + current milestone delta
```

rather than restating the entire project architecture.

The prompt should include:

- milestone number and title

- exact required prompt filename

- exact required closeout filename

- goal

- background/context

- scope

- out of scope

- backend requirements, if applicable

- frontend requirements, if applicable

- validation checklist

- safety boundaries

- deliverables

- definition of done

- reference to `docs/context/CODING_AGENT_RULES.md`

- specific prior context files or closeouts to read only when needed

For future prompts, ChatGPT should include a section like:

```markdown
## Required File Names

Prompt file:

```text
12.75.0_example_prompt.md
```

Required closeout file:

```text
12.75.0_example_closeout.md
```

Create one closeout document only.  
Do not create a separate report file.

```
The User reviews and approves the milestone prompt.

---

## Step 2 — Save and Commit Prompt Before Handoff

The User saves the prompt in the repository using the exact filename specified in the prompt.

The initial prompt file should be committed before coder handoff.

Recommended process:

```powershell
git status --short
git add "<exact_prompt_filename>"
git diff --cached --name-only
git commit -m "Docs: add <milestone> <short name> prompt"
git push
```

This creates a durable baseline instruction set.

---

## Step 3 — Handoff to Coder

The User provides the milestone prompt to coder.

Coder:

- reads `docs/context/CODING_AGENT_RULES.md`

- reads the milestone prompt

- performs git preflight

- inspects relevant code paths

- reads broader context documents only when needed

- identifies ambiguities, risks, or decisions

- asks clarification questions before coding if needed

---

## Step 3.5 — Git Preflight and Dirty-Tree Classification

Before coding, coder should report:

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
only the active milestone prompt is modified with expected Q&A/addenda
```

If other dirty files exist, coder must stop before coding and classify them.

Classification should identify whether each dirty file is:

```text
A. required prior-milestone follow-up/fix
B. unrelated work
C. accidental/noise
D. required for the current milestone
```

Coder should not revert, commit, or stage anything unless explicitly authorized.

Purpose:

- avoid mixed commits

- prevent unrelated changes from entering the milestone

- catch unfinished prior work

- preserve clean milestone history

---

## Step 4 — Codebase Reconnaissance

For complex or safety-sensitive milestones, coder should perform reconnaissance before implementation.

Reconnaissance is required for milestones involving:

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

- broad UI workflow changes

Coder should inspect relevant systems and identify:

- current behavior

- conflicts with the prompt

- missing data structures

- hidden assumptions

- migration or backfill needs

- likely files/functions to change

- risk of breaking existing behavior

- tests or validation to run

- clarification questions or blockers

When asked for reconnaissance only, coder should not edit files.

---

## Step 5 — Clarification Loop

Coder asks targeted questions.

User brings questions back to ChatGPT.

ChatGPT:

- provides clear, decisive answers

- avoids introducing unnecessary new scope

- maintains architectural alignment

- respects current implementation facts surfaced by coder

- may revise decisions if coder identifies a real conflict

- keeps answers concise enough for User to paste back to coder

User may append ChatGPT’s answers to the same prompt file under Q&A/addenda headings.

Prompt addenda do not require a separate git commit for every exchange unless the change materially affects scope, safety, schema, provenance, Vault behavior, cleanup, live operations, or handoff continuity.

---

## Step 6 — Implementation

Coder implements the milestone according to:

- original prompt

- approved clarification answers

- final lock-ins

- `CODING_AGENT_RULES.md`

Coder should:

- keep changes tightly scoped

- avoid modifying unrelated systems

- preserve existing behavior unless explicitly changed

- avoid speculative enhancements

- document deviations if unavoidable

- not perform unrelated cleanup or formatting

- not run git write commands unless authorized

---

## Step 7 — Closeout Document

After implementation, coder creates one closeout document using the exact required filename from the prompt.

Example:

```text
12.75.0_source_identity_workflow_alignment_closeout.md
```

The closeout should use the single closeout structure defined above.

Do not create a separate report file unless the prompt explicitly requests it.

---

## Step 8 — User Testing

User:

- runs the system locally

- tests real workflows

- validates expected behavior

- checks edge cases

- captures screenshots if useful

- identifies unexpected behavior or usability concerns

Testing should focus on behavior, not only whether code compiled.

For live workflows, User may run approved local/live validation after coder closeout but before final milestone commit.

If live validation produces new information, append it to the closeout before final commit.

---

## Step 9 — Feedback Loop

User reports:

- test results

- observations

- screenshots

- usability notes

- error messages

- suspected regressions

ChatGPT:

- evaluates results

- confirms milestone completion, or

- identifies fixes, follow-up milestones, or scope adjustments

If minor defects are discovered, ChatGPT may recommend:

- immediate patch

- small `.1` follow-up milestone

- Parking Lot item

- deferral until usage testing confirms priority

If a live validation issue requires a small fix, it should be committed as part of the current milestone or as a clearly named follow-up fix, depending on scope.

---

## Step 10 — Completion, Commit, and Documentation

If the milestone passes, ChatGPT provides specific git syntax.

The default is specific-file staging, not `git add .`.

Recommended pattern:

```powershell
git status --short
git diff --name-only
git diff --stat

git add <specific milestone file 1>
git add <specific milestone file 2>
git add <specific milestone closeout>
git add <specific milestone prompt if modified>

git status --short
git diff --cached --name-only
git diff --cached --stat

git commit -m "Milestone <number>: <summary>"
git push
```

Avoid:

```powershell
git add .
```

unless the User has reviewed the full dirty tree and explicitly approves staging all changes.

If dirty files are unrelated, commit them separately or leave them unstaged.

Logical commit grouping should be preserved:

```text
prompt commit
prior-milestone follow-up fix commit
unrelated maintenance commit
current milestone implementation/closeout commit
documentation alignment commit
```

Do not mix unrelated systems in one milestone commit.

---

## Step 11 — Documentation Updates

Documentation updates may include:

- milestone prompt file

- milestone closeout file

- `MILESTONE_HISTORY.md`

- `PROJECT_CONTEXT.md`

- `PROJECT_ARCHITECTURE.md` or `ARCHITECTURE_ROADMAP.md`

- `PROJECT_WORKFLOW.md`

- `CODING_AGENT_RULES.md`

- Parking Lot files

Not every milestone requires global documentation updates.

Major workflow, architecture, or system-state changes should be reflected in the relevant global documents.

When replacing old document versions with new versions, commit both the add and removal together.

Example:

```powershell
git add docs/context/project_workflow_v5.md
git rm docs/context/project_workflow_v4.md
git commit -m "Docs: update project workflow"
```

---

## Step 12 — Next Milestone

ChatGPT proposes the next milestone.

ChatGPT should distinguish between:

- core feature development

- safety/guardrail work

- UX refinement

- documentation-only planning

- refactor/stabilization

- testing/polish milestones

- Parking Lot deferrals

ChatGPT should explain why the proposed next milestone is logically next.

---

## Step 13 — Chat / Context Health and Continuation

At major documentation boundaries, especially after large milestone arcs, User and ChatGPT should decide whether to continue in the current chat or start a continuation chat.

Recommended continuation points:

- after major documentation refreshes

- after large milestone arcs

- after folder/documentation reorganization

- when attachment handling becomes unreliable

- when responses slow noticeably

- when the assistant begins re-asking settled context

- when answers become generic or inconsistent

- when project state has changed enough that updated docs should become the new source of truth

Continuation chats should begin with current copies of:

- `PROJECT_CONTEXT.md`

- `PROJECT_ARCHITECTURE.md` or `ARCHITECTURE_ROADMAP.md`

- `MILESTONE_HISTORY.md`

- `PROJECT_WORKFLOW.md`

- `CODING_AGENT_RULES.md`

- Parking Lot

- current milestone prompt and closeout if relevant

---

# Cost-Aware Agentic Coding Workflow

The project uses AI coding agents in VS Code or similar tools. Because agentic coding can consume significant usage credits, prompts should reduce unnecessary context loading, broad repo wandering, and failed implementation attempts.

## Core Cost-Control Principles

- Keep durable rules in `docs/context/CODING_AGENT_RULES.md`.

- Keep milestone prompts focused on the current delta.

- Do not paste all global context into every prompt.

- Do not ask the coding agent to read every project document for every small task.

- Provide likely relevant files/systems when known.

- Use reconnaissance-first for risky or uncertain work.

- Split broad risky work into smaller prompts.

- Preserve one closeout document per milestone.

- Avoid repeated broad repository searches without a reason.

---

## Default Context Pattern

For most implementation prompts:

```text
Before coding:
1. Read docs/context/CODING_AGENT_RULES.md.
2. Read this milestone prompt.
3. Inspect the relevant code paths listed below.
4. Read PROJECT_CONTEXT / PROJECT_ARCHITECTURE only if the affected behavior is unclear.
```

---

## When Full Context Is Still Justified

A longer prompt or broader context read is justified when the milestone touches:

- data model changes

- source identity semantics

- ingestion behavior

- provenance

- cleanup/deletion

- Vault logic

- cloud acquisition

- credential/session handling

- cross-cutting UI workflow redesign

- migration/backfill work

- deployment architecture

---

## Prompt Modes

### 1. Reconnaissance-Only Prompt

Use when implementation risk or code reality is uncertain.

Coder should not edit files.

Expected output:

```text
1. relevant files/services/routes/components
2. current behavior
3. proposed implementation plan
4. risks and safety concerns
5. migration/backfill needs, if any
6. tests or validation to run
7. clarification questions or blockers
```

### 2. Implementation-After-Reconnaissance Prompt

Use after User/ChatGPT approves the reconnaissance plan.

Coder should implement only the approved plan and report deviations.

### 3. Direct Small Implementation Prompt

Use for low-risk changes such as:

- small UI copy changes

- narrow display fixes

- small tests

- documentation updates

- isolated non-destructive bug fixes

Even direct implementation prompts should reference `CODING_AGENT_RULES.md`.

---

## When to Split a Milestone

Split a milestone when:

- it mixes backend, frontend, migrations, and destructive behavior

- safety verification is not yet understood

- codebase reconnaissance may change the implementation plan

- the prompt would require many unrelated systems

- user testing should happen before the next step

- failure would be expensive or risky to unwind

---

# Prompt Structure Standard

All milestone prompts should generally include enough information to implement the milestone without restating all standing project rules.

Preferred structure:

1. Title

2. Required file names

3. Goal

4. Background / context

5. Scope

6. Out of scope

7. Requirements

8. Safety boundaries

9. Testing / validation checklist

10. Deliverables

11. Definition of done

12. Required closeout filename/content

13. Recommended next milestone

For future prompts, ChatGPT should include these standing instructions:

```text
Read and obey docs/context/CODING_AGENT_RULES.md.
Create one closeout document only.
Do not create a separate report file.
Use the exact closeout filename specified in this prompt.
Do not run git write commands unless explicitly authorized.
```

For safety-sensitive prompts, ChatGPT should repeat the specific safety-critical rules directly in the prompt, even if they also exist in `CODING_AGENT_RULES.md`.

---

# Git Discipline

## Coder Git Reconnaissance

Coder should perform git reconnaissance before coding:

```powershell
git branch --show-current
git status --short
git log --oneline --decorate -5
```

If unexpected dirty files exist, coder should stop and classify them before coding.

Coder should not assume dirty files belong to the current milestone.

---

## Commit Hygiene

The User usually performs commits.

When ChatGPT provides git syntax, it should:

- stage specific files

- avoid `git add .` by default

- include verification commands before commit

- separate unrelated changes into separate commits

- include prompt and closeout files in the appropriate milestone commit

- call out untracked files explicitly

Recommended commit verification:

```powershell
git status --short
git diff --cached --name-only
git diff --cached --stat
```

---

## Logical Commit Grouping

Prefer separate commits for:

- prompt file

- prompt Q&A update if material

- prior-milestone follow-up fix

- unrelated maintenance work

- current milestone implementation and closeout

- documentation alignment

- tag/version updates

Do not mix unrelated systems in one commit simply because they are dirty at the same time.

---

# Migration / Backfill Considerations

For milestones that modify:

- data models

- canonical fields

- source identity

- ingestion behavior

- grouping logic

- provenance logic

- cleanup behavior

the system must consider:

- existing data state

- whether backfill is required

- whether changes are forward-only

- whether changes are recomputable

- whether changes are destructive or non-destructive

- how referenced historical records are protected

Coder should raise these questions during reconnaissance or clarification.

---

# Performance Awareness

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

---

# Communication Rules

## ChatGPT

ChatGPT should:

- not assume preferences not discussed

- ask clarifying questions when needed

- anticipate common implementation questions

- keep scope controlled per milestone

- avoid unnecessary complexity

- preserve architectural consistency

- produce coder-ready instructions

- name prompt and closeout files explicitly

- prefer delta-focused prompts that reference standing coding-agent rules

- repeat safety-critical rules directly for destructive or high-risk milestones

- incorporate coder question answers into the milestone prompt record when requested

- recommend specific-file git staging when committing

---

## Coder

Coder should:

- not expand scope without approval

- ask questions before implementing uncertain logic

- challenge prompt assumptions if code reality differs

- follow prompt structure, `CODING_AGENT_RULES.md`, and final lock-ins

- report deviations explicitly

- create one closeout document only

- use the exact closeout filename specified in the prompt

- validate before reporting completion

- perform git preflight before coding

- stop and classify unexpected dirty files before coding

- avoid git write commands unless authorized

---

## User

User should:

- validate behavior, not just code

- provide structured feedback

- prioritize real-world usability

- bring coder questions back to ChatGPT

- confirm milestone completion before final commit

- decide when to reorganize or refresh project documentation

- save prompt files under the exact filename specified

- commit initial prompt files before coder handoff when practical

- keep prompt addenda in the same prompt file

---

# Scope Discipline Rules

- each milestone must remain tightly scoped

- new ideas discovered during implementation should be deferred to Parking Lot unless explicitly approved

- avoid mixing multiple systems in one milestone unless intentionally designed

- do not add cleanup, deletion, or automation behavior incidentally

- do not change provenance or source identity behavior without explicit planning

- do not mix unrelated dirty files into milestone commits

---

# Documentation Discipline Rules

Going forward:

- `CODING_AGENT_RULES.md` is the standing coding-agent rule set

- prompt and closeout files are the primary milestone records

- the prompt file must define the exact closeout filename

- one human-authored closeout file replaces separate report/operations/coder-response files

- documentation should reflect actual behavior, not intended behavior

- prompt files may include follow-up Q&A and final lock-ins

- closeout files should document what actually changed

- application-generated runtime reports may be referenced, but should not replace the closeout

- old documentation patterns may remain for historical milestones, but new milestones should use the simplified model

---

# Key Principles

- Milestone-driven development

- Separation of design and implementation

- Human-in-the-loop validation

- Incremental system evolution

- Local-first architecture

- Non-destructive data handling

- Source/provenance history preservation

- Design for correctness before optimization

- Safety before automation

- Clean git history

- Exact prompt/closeout naming

- Documentation that supports continuity without excessive overhead

- Cost-aware AI coding-agent usage through standing rules and delta-focused prompts

---

# Success Criteria

This workflow is successful when:

- milestones are delivered cleanly and predictably

- coder knows exactly what to implement

- clarification loops are shorter and more decisive

- documentation overhead is reduced

- prompt and closeout naming is consistent

- repeated prompt boilerplate is reduced through `CODING_AGENT_RULES.md`

- documentation still captures actual system behavior

- git commits are logically grouped and reviewable

- unrelated work is not accidentally mixed into milestone commits

- regressions are minimized

- architecture remains consistent

- project state remains portable across sessions

- user confidence increases with each milestone
