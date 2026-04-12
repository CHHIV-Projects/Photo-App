**WORKFLOW.md**

**Purpose**

Define the working collaboration model between:

-   **User (Project Owner)**
-   **ChatGPT (Architect / Planner)**
-   **Coder (Implementation in VS Code)**

This workflow ensures:

-   clear separation of responsibilities
-   consistent milestone delivery
-   controlled system evolution
-   minimal ambiguity during development

**Roles**

**User (You)**

-   Defines goals and priorities
-   Reviews system behavior
-   Tests completed work
-   Reports results and feedback
-   Makes final decisions

**ChatGPT (Architect)**

-   Designs system architecture and milestones
-   Writes structured prompts (.md) for implementation
-   Answers coder questions
-   Interprets results and adjusts direction
-   Proposes next milestones

**Coder (Implementation)**

-   Implements features in codebase
-   Follows milestone prompts exactly
-   Asks clarification questions before coding
-   Provides summary of changes after completion
-   Validates functionality locally

**Standard Workflow Cycle**

**Step 1 — Milestone Definition**

ChatGPT generates a structured milestone prompt:

-   Written as a .md document
-   Includes:
    -   goal
    -   scope
    -   requirements
    -   constraints
    -   validation checklist
    -   deliverables

User reviews and approves.

**Step 2 — Handoff to Coder**

User provides the .md milestone prompt to coder.

Coder:

-   reviews prompt
-   inspects current codebase
-   identifies ambiguities or decisions

**Step 3 — Clarification Loop**

Coder asks targeted questions.

User brings questions back to ChatGPT.

ChatGPT:

-   provides clear, decisive answers
-   avoids introducing new scope
-   keeps alignment with architecture

User sends finalized answers to coder.

**Step 4 — Implementation**

Coder:

-   implements milestone according to prompt
-   keeps changes scoped
-   ensures no regression to existing functionality

**Step 5 — Code Summary**

Coder returns:

-   list of files modified/added
-   description of implementation
-   any deviations or assumptions
-   test results

**Step 6 — User Testing**

User:

-   runs system locally
-   tests key workflows
-   validates expected behavior
-   identifies issues or unexpected results

**Step 7 — Feedback Loop**

User reports back:

-   test results
-   observations
-   screenshots (if helpful)
-   usability notes

ChatGPT:

-   evaluates results
-   confirms milestone completion OR
-   identifies fixes / adjustments

**Step 8 — Completion and Commit**

If milestone passes:

-   ChatGPT provides git commit syntax
-   User commits milestone

**Step 9 — Next Milestone**

ChatGPT:

-   proposes next milestone
-   ensures logical progression
-   maintains architectural consistency

**Prompt Structure Standard**

All milestone prompts follow a consistent format:

-   Title
-   Goal
-   Context
-   Scope
-   Out of scope
-   Backend requirements
-   Frontend requirements
-   Validation checklist
-   Deliverables
-   Definition of done

This ensures:

-   coder clarity
-   repeatability
-   minimal interpretation errors

**Communication Rules**

**ChatGPT**

-   does not assume preferences not discussed
-   asks clarifying questions when needed
-   keeps scope controlled per milestone
-   avoids unnecessary complexity

**Coder**

-   does not expand scope without approval
-   asks questions before implementing uncertain logic
-   follows prompt structure

**User**

-   validates behavior, not just code
-   provides clear feedback
-   prioritizes real-world usability

**Key Principles**

-   **Milestone-driven development**
-   **Separation of design and implementation**
-   **Human-in-the-loop validation**
-   **Incremental system evolution**
-   **Local-first, controlled complexity growth**

**Success Criteria**

This workflow is successful when:

-   milestones are delivered cleanly and predictably
-   regressions are minimized
-   architecture remains consistent
-   system complexity grows in a controlled manner
-   user confidence increases with each milestone
