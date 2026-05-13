# PROJECT_WORKFLOW.md

## Purpose

Define the working collaboration model between:

- **User (Project Owner)**

- **ChatGPT (Architect / Planner)**

- **Coder (Implementation in VS Code)**

This workflow ensures:

- clear separation of responsibilities

- consistent milestone delivery

- controlled system evolution

- minimal ambiguity during development

- portability across chats and sessions

---

## Roles

### User (Project Owner)

- defines goals and priorities

- reviews system behavior

- tests completed work

- reports results and feedback

- makes final decisions

---

### ChatGPT (Architect)

- designs system architecture and milestones

- writes structured prompts (.md) for implementation

- anticipates likely coder clarification questions

- answers coder questions clearly and decisively, while ensuring alignment with current system behavior and architecture

- interprets results and adjusts direction

- proposes next milestones

---

### Coder (Implementation)

- implements features in codebase

- follows milestone prompts exactly

- asks clarification questions before coding

- provides summary of changes after completion

- validates functionality locally

---

## Standard Workflow Cycle

### Step 1 — Milestone Definition

ChatGPT generates a structured milestone prompt:

- written as a `.md` document

- includes:
  
  - goal
  
  - scope
  
  - requirements
  
  - constraints
  
  - validation checklist
  
  - deliverables

ChatGPT should anticipate common clarification questions within the prompt.

User reviews and approves.

---

### Step 2 — Handoff to Coder

User provides the `.md` milestone prompt to coder.

Coder:

- reviews prompt

- inspects current codebase

- identifies ambiguities or decisions

---

### Step 2.5 — Codebase Reconnaissance (NEW)

For complex milestones, the coder should:

- inspect relevant existing systems and code paths
- identify:
  - conflicts with current implementation
  - missing data structures
  - implicit assumptions in prompt vs reality
- confirm:
  - where changes will occur
  - whether migration/backfill is required
- return structured observations before implementation if needed

Purpose:

- avoid incorrect assumptions
- reduce rework
- ensure prompt aligns with actual system state

---

### Step 3 — Clarification Loop

Coder asks targeted questions.

User brings questions back to ChatGPT.

ChatGPT:

- provides clear, decisive answers

- avoids introducing new scope

- maintains architectural alignment

- coder may challenge prompt assumptions if they conflict with current system behavior

User sends finalized answers to coder.

---

### Step 4 — Implementation

Coder:

- implements milestone according to prompt

- keeps changes tightly scoped

- avoids modifying unrelated systems

- ensures no regression to existing functionality

---

### Step 5 — Code Summary / Coder Response Artifact

Coder returns and places in the workspace a structured closeout document:

`docs/prompts/Coder response <milestone>.md`

or equivalent project-approved location/naming.

The response should include:

- milestone title and date
- scope completed
- files modified/added
- implementation summary
- tests/build results
- validation results
- deviations from prompt, if any
- known limitations or follow-up items
- whether Definition of Done was met

This coder response becomes part of the project record and may be used to update:

- `MILESTONE_HISTORY.md`
- `PROJECT_CONTEXT.md`
- `PROJECT_ARCHITECTURE.md`
- Parking Lot items

If the workspace convention uses a different exact path, preserve the actual convention.

---

### Step 6 — User Testing

User:

- runs system locally

- tests real workflows

- validates expected behavior

- identifies issues or unexpected results

---

### Step 7 — Feedback Loop

User reports:

- test results

- observations

- screenshots (if helpful)

- usability notes

ChatGPT:

- evaluates results

- confirms milestone completion OR

- identifies fixes or adjustments

---

### Step 8 — Completion, Commit, and Documentation

If milestone passes:

- ChatGPT provides git commit syntax

- User commits milestone

Additionally (critical for continuity):

- update system documentation when needed:
  
  - `PROJECT_CONTEXT.md`
  
  - `PROJECT_ARCHITECTURE.md`
  
  - `MILESTONE_HISTORY.md`

Additionally, update or preserve relevant project artifacts when needed:

- `PROJECT_CONTEXT.md`
- `PROJECT_ARCHITECTURE.md`
- `MILESTONE_HISTORY.md`
- `project_workflow.md`
- `Parking_Lot_v*.md`
- milestone prompt files under `docs/prompts/`
- `docs/prompts/Coder response <milestone>.md`

This ensures the system state remains portable across sessions.

---

### Step 9 — Next Milestone

ChatGPT:

- proposes next milestone

- ensures logical progression

- maintains architectural consistency

- distinguishes between:
  
  - core feature development
  
  - system refinement

---

### Step 10 — Chat / Context Health and Continuation

At major documentation boundaries, especially after large milestone arcs, User and ChatGPT should decide whether to continue in the current chat or start a continuation chat.

Recommended continuation points:

- after major documentation refreshes
- after large milestone arcs
- when attachment handling becomes unreliable
- when responses slow noticeably
- when the assistant begins re-asking settled context
- when answers become generic or inconsistent
- when project state has changed enough that updated docs should become the new source of truth

Continuation chats should begin with current copies of:

- `PROJECT_CONTEXT.md`
- `PROJECT_ARCHITECTURE.md`
- `MILESTONE_HISTORY.md`
- `project_workflow.md`
- Parking Lot
- any current milestone prompt/coder response needed for continuity

The purpose is to preserve context quality and reduce the risk of architectural drift.

---

### Prompt Types

#### Milestone Types

Milestones generally fall into one of the following categories:  

- **New System** — introduces new models or workflows  

- **Extension** — builds on existing systems  

- **Refactor / Stabilization** — modifies behavior or performance  

- **UX / Interaction** — improves usability without changing core logic  

- **Design-First** — requires analysis before implementation (no immediate coding)  

Each type may require different levels of:  

- codebase reconnaissance  
- migration/backfill planning  
- clarification depth

---

## Prompt Structure Standard

All milestone prompts follow a consistent format:

- Title

- Goal

- Context

- Scope

- Out of scope

- Backend requirements

- Frontend requirements

- Validation checklist

- Deliverables

- Definition of done

This ensures:

- coder clarity

- repeatability

- minimal interpretation errors

---

## Migration / Backfill Considerations

For milestones that modify:  

- data models  
- canonical fields  
- grouping logic  

the system must consider:  

- existing data state  

- whether backfill is required  

- whether changes are:  

- forward-only  

- recomputable  

- destructive or non-destructive  

Coder should raise these questions during clarification phase.

---

## Performance Awareness

Milestones must consider:  

- impact on ingestion time  
- query efficiency  
- scalability with large datasets  

Expensive operations should:  

- be identified explicitly  
- be candidates for background processing  

Example:  

- duplicate lineage (moved toward background processing)

---

## Communication Rules

### ChatGPT

- does not assume preferences not discussed

- asks clarifying questions when needed

- anticipates common implementation questions

- keeps scope controlled per milestone

- avoids unnecessary complexity

---

### Coder

- does not expand scope without approval

- asks questions before implementing uncertain logic

- follows prompt structure

- reports deviations explicitly

---

### User

- validates behavior, not just code

- provides clear, structured feedback

- prioritizes real-world usability

- confirms milestone completion before moving forward

---

## Scope Discipline Rules

- each milestone must remain tightly scoped

- new ideas discovered during implementation:
  
  - are deferred to Parking Lot
  
  - are not added mid-milestone

- avoid mixing multiple systems in one milestone unless explicitly designed

---

## Key Principles

- **Milestone-driven development**

- **Separation of design and implementation**

- **Human-in-the-loop validation**

- **Incremental system evolution**

- **Local-first architecture**

- **Non-destructive data handling**

- **Design for correctness before optimization**

---

## System State Continuity

The system must always be representable through:

- `PROJECT_CONTEXT.md` (current state)

- `PROJECT_ARCHITECTURE.md` (direction)

- `MILESTONE_HISTORY.md` (change log)

- `PROJECT_WORKFLOW.md` (change log)

These documents enable:

- transition to new chats

- onboarding new contributors

- maintaining architectural consistency

---

## Success Criteria

This workflow is successful when:

- milestones are delivered cleanly and predictably

- regressions are minimized

- architecture remains consistent

- system complexity grows in a controlled manner

- documentation reflects actual system state

- user confidence increases with each milestone

- 
