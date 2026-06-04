# PROJECT_WORKFLOW.md

## Purpose

Define the working collaboration model between:

- **User / Project Owner**
- **ChatGPT / Architect and Planner**
- **Coder / Implementation in VS Code**

This workflow ensures:

- clear separation of responsibilities
- consistent milestone delivery
- controlled system evolution
- minimal ambiguity during development
- durable documentation that is easy to find
- portability across chats, sessions, and future contributors

---

## Roles

### User / Project Owner

The User:

- defines goals and priorities
- reviews proposed milestone scope
- provides milestone prompts to coder
- brings coder questions back to ChatGPT
- tests completed work locally
- reports real-world behavior, screenshots, issues, and usability feedback
- makes final product and workflow decisions
- confirms milestone completion before commit/tag
- maintains or approves the project documentation organization

---

### ChatGPT / Architect and Planner

ChatGPT:

- designs system architecture and milestone sequence
- writes structured milestone prompts for implementation
- anticipates likely coder clarification questions
- answers coder questions clearly and decisively
- keeps answers aligned with current system behavior and architecture
- interprets coder results and user testing feedback
- identifies whether a milestone is complete or needs follow-up
- proposes next milestones
- keeps scope controlled and avoids adding unrelated work mid-milestone
- recommends documentation updates when project workflow or architecture changes

---

### Coder / Implementation

Coder:

- implements milestone prompts in the codebase
- performs codebase reconnaissance before coding when needed
- asks clarification questions before implementing uncertain behavior
- keeps changes tightly scoped to the approved milestone
- avoids modifying unrelated systems
- validates functionality locally
- produces one milestone closeout document after implementation
- reports deviations, validation results, known limitations, and recommended next steps

---

## Documentation Organization

### Current Milestone Documentation Model

Project milestone documentation is organized under:

```text
docs/milestones/
```

Milestone parent folders use the pattern:

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
- sub-milestones such as `12.62.1`, `12.62.2`, etc. live inside the same milestone parent folder

---

### Prompt and Closeout Files

Going forward, each prompt/action should generally have:

```text
prompt file
closeout file
```

The User may decide exact placement while reorganizing folders, but ChatGPT prompts should provide suggested file names.

Recommended pattern:

```text
12.62.7_guided_icloud_source_intake_handoff_prompt.md
12.62.7_guided_icloud_source_intake_handoff_closeout.md
```

If a prompt has follow-up answers or lock-ins, append them to the same prompt file under headings such as:

```markdown
## Original Prompt

## Coder Questions / Answers Round 1

## Coder Questions / Answers Round 2

## Final Lock-ins
```

This keeps coder’s pre-coding instruction set in one place.

---

### Single Closeout Document Standard

Coder should create **one closeout document only** per prompt/action.

Do **not** create separate:

```text
docs/operations/...
docs/prompts/Coder response ...
```

unless explicitly requested.

The closeout document replaces both the older operations document and coder response document.

The closeout should include:

1. milestone title and date
2. scope completed
3. operational behavior
4. files changed
5. API / data model changes, if applicable
6. safety boundaries preserved
7. validation performed
8. deviations from prompt
9. known limitations
10. recommended next milestone

---

### Prompt Storage

The User may paste ChatGPT milestone prompts into the milestone folder manually.

ChatGPT should not assume exact folder placement while the documentation structure is being reorganized.

Instead, ChatGPT should include suggested naming only, for example:

```text
Suggested milestone parent folder:
012.062_icloud_source_profile_run_planning

Suggested prompt filename:
12.62.7_guided_icloud_source_intake_handoff_prompt.md

Required closeout filename:
12.62.7_guided_icloud_source_intake_handoff_closeout.md
```

---

## Standard Workflow Cycle

### Step 1 — Milestone Definition

ChatGPT generates a structured milestone prompt.

The prompt is written as reusable Markdown and includes:

- title
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
- requested closeout filename and content

ChatGPT should anticipate common implementation questions within the prompt when possible.

The User reviews and approves the milestone prompt.

---

### Step 2 — Handoff to Coder

The User provides the milestone prompt to coder.

The prompt may be saved in the milestone folder using the agreed naming convention.

Coder:

- reviews the prompt
- inspects the current codebase
- identifies ambiguities, risks, or decisions
- asks clarification questions before coding if needed

---

### Step 2.5 — Codebase Reconnaissance

For complex milestones, coder should perform reconnaissance before implementation.

Coder should inspect relevant existing systems and code paths and identify:

- conflicts with current implementation
- missing data structures
- hidden assumptions in the prompt
- migration or backfill needs
- likely files/functions to change
- risk of breaking existing behavior

Coder should return structured observations before coding when needed.

Purpose:

- avoid incorrect assumptions
- reduce rework
- ensure prompt aligns with actual code state
- detect prompt-vs-reality divergence early

---

### Step 3 — Clarification Loop

Coder asks targeted questions.

User brings questions back to ChatGPT.

ChatGPT:

- provides clear, decisive answers
- avoids introducing new scope
- maintains architectural alignment
- respects current implementation facts surfaced by coder
- may revise decisions if coder identifies a real conflict
- keeps answers concise enough for User to paste back to coder

User sends finalized answers to coder.

If there are multiple rounds of questions, the User may append ChatGPT’s answers to the same milestone prompt file.

---

### Step 4 — Implementation

Coder implements the milestone according to:

- original prompt
- approved clarification answers
- final lock-ins

Coder should:

- keep changes tightly scoped
- avoid modifying unrelated systems
- preserve existing behavior unless the milestone explicitly changes it
- avoid speculative enhancements
- document deviations if unavoidable

---

### Step 5 — Closeout Document

After implementation, coder creates one closeout document.

Recommended closeout filename:

```text
<milestone>_<short_description>_closeout.md
```

Example:

```text
12.62.7_guided_icloud_source_intake_handoff_closeout.md
```

The closeout document should include:

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

This single closeout replaces the prior two-document model.

---

### Step 6 — User Testing

User:

- runs system locally
- tests real workflows
- validates expected behavior
- checks edge cases
- captures screenshots if useful
- identifies unexpected behavior or usability concerns

Testing should focus on behavior, not only whether code compiled.

---

### Step 7 — Feedback Loop

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
- parking-lot item
- defer until usage testing confirms priority

---

### Step 8 — Completion, Commit, and Documentation

If milestone passes:

ChatGPT provides git syntax:

```bash
git status

git add .

git commit -m "Milestone <number>: <summary>"

git tag v0.<milestone>

git push origin main

git push origin v0.<milestone>
```

User commits and tags the milestone.

Documentation updates may include:

- milestone prompt file
- milestone closeout file
- `MILESTONE_HISTORY.md`
- `PROJECT_CONTEXT.md`
- `PROJECT_ARCHITECTURE.md`
- `PROJECT_WORKFLOW.md`
- Parking Lot files

Not every milestone requires every global document to be updated.

Major workflow, architecture, or system-state changes should be reflected in the relevant global documents.

---

### Step 9 — Next Milestone

ChatGPT proposes the next milestone.

ChatGPT should distinguish between:

- core feature development
- safety/guardrail work
- UX refinement
- documentation-only planning
- refactor/stabilization
- testing/polish milestones

ChatGPT should explain why the proposed next milestone is logically next.

---

### Step 10 — Chat / Context Health and Continuation

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
- `PROJECT_ARCHITECTURE.md`
- `MILESTONE_HISTORY.md`
- `PROJECT_WORKFLOW.md`
- Parking Lot
- current milestone prompt and closeout if relevant

The purpose is to preserve context quality and reduce architectural drift.

---

## Prompt Types

Milestones generally fall into these categories:

- **New System** — introduces new models or workflows
- **Extension** — builds on existing systems
- **Refactor / Stabilization** — modifies behavior, structure, or performance
- **UX / Interaction** — improves usability without changing core logic
- **Design-First / Reconnaissance** — analyzes and plans before implementation
- **Safety / Guardrail** — prevents unsafe state, destructive behavior, or race conditions
- **Documentation / Workflow** — updates project practices or durable documentation

Each type may require different levels of:

- codebase reconnaissance
- migration/backfill planning
- testing
- clarification
- closeout detail

---

## Prompt Structure Standard

All milestone prompts should generally include:

1. Title
2. Goal
3. Background / context
4. Scope
5. Out of scope
6. Requirements
7. Safety boundaries
8. Testing / validation checklist
9. Deliverables
10. Definition of done
11. Required closeout filename/content
12. Recommended next milestone

For future prompts, ChatGPT should include the new documentation instruction:

```text
Create one closeout document only.
Do not create separate operations and coder-response documents.
```

---

## Migration / Backfill Considerations

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

Coder should raise these questions during the clarification phase.

---

## Performance Awareness

Milestones must consider:

- ingestion time
- query efficiency
- background processing impact
- UI responsiveness
- scalability with large photo libraries
- disk/network implications for NAS/external/cloud workflows

Expensive operations should be identified explicitly and may be candidates for background processing.

Examples:

- duplicate lineage
- face processing
- visual enrichment
- iCloud acquisition
- source intake
- cleanup scans

---

## Communication Rules

### ChatGPT

ChatGPT should:

- not assume preferences not discussed
- ask clarifying questions when needed
- anticipate common implementation questions
- keep scope controlled per milestone
- avoid unnecessary complexity
- preserve architectural consistency
- produce coder-ready instructions
- incorporate coder question answers into the milestone prompt record when requested

---

### Coder

Coder should:

- not expand scope without approval
- ask questions before implementing uncertain logic
- challenge prompt assumptions if code reality differs
- follow prompt structure and final lock-ins
- report deviations explicitly
- create one closeout document only
- validate before reporting completion

---

### User

User should:

- validate behavior, not just code
- provide structured feedback
- prioritize real-world usability
- bring coder questions back to ChatGPT
- confirm milestone completion before moving forward
- decide when to reorganize or refresh project documentation

---

## Scope Discipline Rules

- each milestone must remain tightly scoped
- new ideas discovered during implementation should be deferred to Parking Lot unless explicitly approved
- avoid mixing multiple systems in one milestone unless intentionally designed
- do not add cleanup, deletion, or automation behavior incidentally
- do not change provenance or source identity behavior without explicit planning

---

## Documentation Discipline Rules

Going forward:

- prompt and closeout files are the primary milestone records
- closeout replaces separate operations/coder-response documents
- documentation should reflect actual behavior, not intended behavior
- prompt files may include follow-up Q&A and final lock-ins
- closeout files should document what actually changed
- old documentation patterns may remain for historical milestones, but new milestones should use the simplified model

---

## Key Principles

- Milestone-driven development
- Separation of design and implementation
- Human-in-the-loop validation
- Incremental system evolution
- Local-first architecture
- Non-destructive data handling
- Source/provenance history preservation
- Design for correctness before optimization
- Safety before automation
- Documentation that supports continuity without excessive overhead

---

## System State Continuity

The system should remain representable through:

- `PROJECT_CONTEXT.md` — current state
- `PROJECT_ARCHITECTURE.md` — architecture and direction
- `MILESTONE_HISTORY.md` — milestone change log
- `PROJECT_WORKFLOW.md` — collaboration and documentation workflow
- Parking Lot files — deferred ideas and future work
- milestone prompt/closeout files — detailed records for each milestone/action

These documents enable:

- transition to new chats
- onboarding new contributors
- maintaining architectural consistency
- reducing reliance on chat memory alone

---

## Success Criteria

This workflow is successful when:

- milestones are delivered cleanly and predictably
- coder knows exactly what to implement
- clarification loops are shorter and more decisive
- documentation overhead is reduced
- documentation still captures actual system behavior
- regressions are minimized
- architecture remains consistent
- project state remains portable across sessions
- user confidence increases with each milestone
