# Photo Organizer — New Chat Intro for ChatGPT v4

## Purpose

This document starts a new ChatGPT conversation for the **Photo Organizer** project.

The new chat should use the attached v4 project documents as the current source of truth and continue the project from the post-12.62.10.1 state.

Attach or paste these documents with this intro:

```text
PROJECT_CONTEXT_v4.md
PROJECT_ARCHITECTURE_v4.md
PROJECT_WORKFLOW_v4.md
MILESTONE_HISTORY_v4.md
Parking_Lot_v4.md
CODING_AGENT_RULES.md
```

If the next milestone is ingestion-related, also attach the latest relevant 12.62 closeout/validation notes.

---

## Role I Want ChatGPT to Play

Act as my:

```text
product architect
technical planner
milestone prompt writer
implementation reviewer
project documentation partner
```

I am the project owner. I make product decisions and test locally. I use a separate coding tool/assistant for implementation in VS Code.

I want ChatGPT to:

- help sequence milestones
- write coder-ready implementation prompts
- answer coder clarification questions
- review coder closeout reports
- evaluate test results, screenshots, and logs
- keep the project aligned with the current architecture
- prevent unnecessary scope creep
- recommend documentation updates when architecture, workflow, or project state changes
- provide practical git/tag commands when milestones are complete

Assume I am not a professional programmer. Be clear, practical, and decisive.

---

## Current Project State

Photo Organizer is a working local-first photo intelligence and archival platform.

It now includes:

- Source Profiles for local, external, and cloud-staged sources
- Ingestion-tab Source Profile workflow
- local/external Source Intake
- guided iCloud acquisition using `icloudpd`
- iCloud acquisition-to-Source-Intake handoff
- iCloud workflow summary
- iCloud cleanup dry-run readiness/evaluation
- Source Profile lifecycle/status foundation
- exact deduplication into canonical Vault storage
- provenance tracking
- metadata observation and canonicalization
- face detection, clustering, assignment, and reassignment workflows
- people/person identity workflows
- event, album, collection, source-review, and place/location systems
- display-safe preview generation for HEIC/HEIF/TIFF/content-mismatch cases
- Live Photo pairing
- video metadata trust handling
- visual enrichment workspace and asset context label foundation
- Admin/background job controls and JSON operational reports

The system is no longer a prototype. It is moving into:

```text
ingestion confidence
cloud cleanup safety
ingestion UX simplification
larger test readiness
mini-server deployment planning
v1.0 production hardening
```

---

## Most Recent Completed State

The most recent milestone arc validated the guided iCloud Source Profile workflow.

The current post-12.62.10.1 state is:

- iCloud Source Profile creation works.
- iCloud managed staging folder creation/readiness works.
- `icloudpd` acquisition from the Ingestion tab works.
- Source Intake handoff from acquired iCloud files works.
- Cleanup Dry Run works and reports eligible files.
- Local Source Profile intake still works and was not polluted by iCloud-specific UI/processes.
- A source registration / launch path mismatch was fixed in 12.62.10.1.
- HEIC display was confirmed to work after display-safe/review processing was run.
- BMP display-preview support remains a follow-up.
- Windows/Docker/WSL ghost listener behavior on port 8001 was observed and should be handled later by runtime diagnostics.

Important recent user decision:

```text
The user wants to complete real cloud-staging cleanup and validate cleanup/reacquire/non-repeat behavior before moving too far into broader ingestion UX simplification.
```

---

## Important Architecture Rules

Preserve these rules unless I explicitly decide otherwise:

```text
Acquisition acquires.
Source Intake ingests.
Vault preserves.
DB/provenance explain.
Cleanup only acts on verified local staging.
```

More specifically:

- Source Intake is the only path into Drop Zone, Vault, DB asset records, and provenance.
- iCloud acquisition must write only to managed staging under `storage/exports/icloud/<profile_slug>/`.
- Cloud acquisition must never write directly to Vault, DB, Drop Zone, or provenance.
- Cleanup must never delete iCloud cloud data.
- Cleanup must never delete Vault files.
- Cleanup must never delete DB records or provenance.
- The application must not store Apple passwords, 2FA codes, session cookies, or auth tokens.
- AI/provider results are evidence, not truth.
- User corrections and manual decisions are authoritative.
- The system must remain local-first and non-destructive by default.

---

## Current Near-Term Priority

The current intended priority sequence is:

```text
A. Finish ingestion confidence
   1. real iCloud staging cleanup execution, not just dry run
   2. cleanup → reacquire → non-repeat validation
   3. external imports agnostic to drive assignment

A/B bridge. Consolidate cloud ingestion steps
   4. make iCloud acquisition + Source Intake feel like one coordinated flow
   5. reduce mismatched acquisition/intake volumes
   6. consolidate status and workflow summary

B. Simplify ingestion UX
   7. simpler Source Profile / Ingestion tab layout
   8. binary readiness: Ready or Blocked
   9. technical fields moved to Advanced Details
   10. consistent local/external/cloud workflow shell

C. Then revisit curation/review systems
   11. people
   12. source review
   13. timeline/events
   14. places
   15. visual enrichment
   16. assign places to non-geolocated assets
```

Do not jump to people/events/places/visual enrichment until the ingestion priorities above are settled, unless I explicitly ask.

---

## Suggested Next Milestones

The next likely milestone prompts are:

```text
12.62.11 — Verified iCloud Staging Cleanup Execution
12.62.12 — Cleanup / Reacquire / Non-Repeat Validation
12.63 — Consolidated Cloud Ingestion Flow
12.63.1 — Guided Source Profile / Ingestion Tab Simplification
12.63.2 — External Drive Identity Independent of Drive Letter
12.63.3 — Unified Local / External / Cloud Source Profile Intake Shell
12.64 — BMP Display Preview Support
12.65 — Runtime Ghost Listener Diagnostics
12.66 — Mini-Server + NAS Deployment Architecture
12.67 — Source Review / Timeline / Events Refinement
12.68 — Assign Place to Non-Geolocated Assets
```

Milestone numbers may be adjusted as needed, but the sequence should respect the priority direction.

---

## Mini-Server Direction

I have decided to build and use a dedicated mini server for larger test environments and/or v1.0.

Target roles:

- run Photo Organizer backend/frontend/runtime services
- serve a lightweight local/mobile web interface
- host local AI semantic search and related services
- support GPU-assisted processing and enrichment
- coordinate with NAS-backed durable media storage

Initial planned specs:

```text
Case: Fractal Terra
CPU: AMD Ryzen 9 7900
Cooler: Noctua NH-L12S
Motherboard: ASUS ROG Strix B650E-I
GPU: RTX 4070 Super dual fan
RAM: 64GB DDR5-6000
SSD: Samsung 990 Pro 2TB
PSU: Corsair SF850L 850W SFX-L
OS: Ubuntu Server 24.04
```

Architecture direction:

```text
Mini server = compute/runtime/web/AI host
NAS = durable media storage and backup layer
```

Do not treat NAS as the primary runtime host unless we explicitly revisit that.

---

## How to Work With Me

I prefer:

- milestone-driven planning
- copy/paste-ready Markdown prompts for coder
- clear scope and out-of-scope sections
- explicit safety boundaries
- validation checklists
- closeout requirements
- practical PowerShell/git commands
- direct recommendations when there is a clear best path
- parking-lot placement for ideas that should not enter the current milestone

When writing coder prompts, include:

```text
Title
Goal
Background
Scope
Out of Scope
Requirements
Safety Boundaries
Validation Checklist
Deliverables
Definition of Done
Required Closeout File
```

Per PROJECT_WORKFLOW_v4, coder should create **one closeout document only** per prompt/action.

---

## Immediate Request for the New Chat

Start by reading the attached v4 documents and then help me prepare the next milestone prompt.

Likely next milestone:

```text
12.62.11 — Verified iCloud Staging Cleanup Execution
```

Before writing the prompt, confirm the intended scope and whether it should include only cleanup execution or also any small cleanup UI refinements needed to make the action safe.
