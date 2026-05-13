# Milestone 12.45.0 — Refresh PROJECT_ARCHITECTURE_v3.md After iCloud Ingestion Arc

## Goal

Update `project_architecture_v3.md` so it accurately reflects the system after milestones **12.19–12.44.1**, especially the completed iCloud ingestion arc, Source Registry / Source Intake operational model, Admin operational controls, display preview work, Live Photo support, video metadata handling, and iCloud staging cleanup.

This should be a documentation/architecture refresh milestone, not a code milestone.

The updated architecture document should describe the system’s **current architecture and forward roadmap**, not old future assumptions.

---

## Context

`PROJECT_CONTEXT.md` has now been refreshed. `PROJECT_ARCHITECTURE.md` still reads like it was last updated around 12.18 / early Phase 5.

It correctly captures the broad vision, but several sections are stale.

Examples of outdated or incomplete framing:

```text
cloud ingestion is still treated as a future/current focus item
HEIC and Live Photo handling are still framed as upcoming format support
duplicate processing decoupling is still framed as an immediate promotion candidate
Admin system is described too generally
Source Registry / Source Intake architecture is underrepresented
iCloud acquisition and staging cleanup are not reflected as active architecture
NAS/Synology section is too brief
```

Milestones and coder responses from **12.19 through 12.44.1** are available in the workspace and should be used as source material.

---

## Primary Source Materials

Use:

```text
existing PROJECT_ARCHITECTURE.md
updated PROJECT_CONTEXT.md
milestone prompts from 12.19–12.44.1
coder responses from 12.19–12.44.1
current code structure if needed
```

If recent coder responses conflict with older roadmap statements, prefer the recent completed implementation unless code inspection says otherwise.

---

## Core Requirement

Revise `PROJECT_ARCHITECTURE.md` so it clearly distinguishes:

```text
implemented current architecture
current operational hardening phase
true future roadmap items
parking lot / deferred items
```

Do not turn the architecture roadmap into a full milestone history.

Do not include detailed debugging history.

Do not include long implementation logs.

Focus on architecture state and roadmap direction.

---

# Required Updates

---

## 1. Current State Summary

The current summary is directionally good but should be updated to include the post-12.44.1 operational systems.

Add current-state capabilities such as:

```text
Source Registry and Source Intake operational model
Admin-controlled iCloud acquisition using icloudpd
iCloud staging cleanup with provenance + Vault verification
Display Preview generation for HEIC/HEIF/TIFF/content mismatch cases
Live Photo pairing, including icloudpd _HEVC.MOV naming
MOV/MP4/M4V video metadata trust handling
Admin background job controls for duplicate, face, preview, Live Photo, and geocoding workflows
```

The current document says:

```text
The system is no longer a prototype — it is a functionally complete archival platform.
```

This is reasonable, but I recommend softening it slightly to reflect ongoing operational hardening.

Suggested wording:

```text
The system is no longer a prototype — it is a functional archival platform moving into operational hardening, scale validation, and workflow simplification.
```

---

## 2. System Evolution Note

Keep the current idea that the system evolved from pipeline-centric to workflow-centric, but broaden it.

The shift is no longer only about Photo Review and duplicate adjudication.

It now also includes Admin operational workflows:

```text
Source Registry
Source Intake
iCloud Acquisition
iCloud Staging Cleanup
Background processing controls
```

Suggested update:

```markdown
## System Evolution Note

The system has evolved from a primarily pipeline-centric architecture to a layered architecture where user workflow surfaces and Admin operational controls are now the primary interaction model.

Photo Review, duplicate adjudication, Source Intake, iCloud Acquisition, and Admin background controls expose the underlying pipelines in safer, more operator-directed ways.

The architecture continues to preserve strict system boundaries: acquisition acquires, Source Intake ingests, Vault preserves, and DB/provenance explain.
```

---

## 3. Development Phases

The phase structure is still useful, but Phase 5 needs the most work.

---

### Phase 1 — Data Integrity

Likely fine.

Keep as complete.

---

### Phase 2 — Identity & Pipeline Stability

Likely fine, but you may add:

```text
source/provenance stability
safe ingestion foundations
```

Only if needed.

---

### Phase 3 — Organization & Presentation

Current document says remaining minor gaps include:

```text
event reassignment
album-event integration
UI consistency refinement
```

Review whether event reassignment is still a gap. If event reassignment UI/API was already implemented in 12.2, adjust wording.

Suggested:

```text
Remaining / future refinements:
- album-event integration
- UI consistency refinement
- deeper collection workflows
```

Do not list completed items as remaining gaps.

---

### Phase 4 — Data Quality & User Workflows

This section is mostly fine.

It describes 12.1–12.18. Keep it mostly intact.

---

### Phase 5 — Operational Hardening & Real-World Scale

This section needs a substantial rewrite.

Current Phase 5 says focus is:

```text
ingestion stabilization
cloud ingestion
duplicate processing decoupling
format handling
performance and scalability
UX refinement
```

But many of these have now been implemented or substantially advanced.

Replace the current Phase 5 section with something like:

```markdown
### Phase 5 — Operational Hardening & Real-World Scale (Current)

Focus:

- productionizing Source Registry and Source Intake workflows
- iCloud acquisition using icloudpd
- verified staging cleanup after ingestion
- background/admin-controlled processing jobs
- acquisition completeness strategy beyond fixed recent windows
- source lifecycle management, including inactive/archive source support
- workflow simplification toward unified Source Profiles
- NAS readiness and deployment planning
- punchlist/usability refinement

This phase marks the transition from prototype completeness to real-world operational robustness.

Delivered so far:

- Drop Zone / Source Intake stabilization
- background duplicate processing
- Source Registry and source label improvements
- iCloud export intake design and trial
- icloudpd evaluation and adoption as preferred acquisition adapter
- Admin iCloud acquisition UI
- guided acquisition-to-intake handoff
- verified iCloud staging cleanup
- HEIC/HEIF/TIFF display preview support
- Live Photo pairing, including icloudpd `_HEVC.MOV` naming
- MOV/MP4/M4V video metadata trust handling
- stale-run recovery for selected background jobs

Current remaining focus:

- iCloud until-found / checkpoint completeness strategy
- Source Registry archive / inactive source lifecycle
- unified Source Profile and Intake Workflow design
- production-scale iCloud intake validation
- NAS deployment planning
- punchlist/usability cleanup
```

---

### Phase 6 — Platform Expansion

This can remain future-facing.

Consider adding:

```text
scheduled source profile intake
multi-account cloud workflows
```

But keep Phase 6 concise.

---

## 4. Milestone Reality Section

The current document has a good **Milestone 11 Summary**, but now the roadmap needs a **Milestone 12 Summary** too.

Add a new section after Milestone 11:

```markdown
## 4A. Milestone 12 Reality Summary

Milestone 12 transformed the system from a functional archival prototype into an operationally controlled ingestion and curation platform.

Major delivered areas:

- metadata canonicalization and observation-driven metadata handling
- duplicate adjudication and canonical/demotion workflows
- event stabilization and user-protection direction
- place/location/geocoding system
- Photo Review and unified filtering/search
- Source Registry and Source Intake stabilization
- Drop Zone / batch staging controls
- background duplicate processing
- display preview generation for HEIC/HEIF/TIFF/mismatch cases
- Live Photo pairing and Admin pairing workflow
- video metadata trust handling for MOV/MP4/M4V
- iCloud acquisition using icloudpd
- Admin iCloud acquisition UI
- acquisition-to-intake handoff
- verified iCloud staging cleanup
- Admin operational controls for multiple background jobs

Milestone 12 is now primarily entering documentation consolidation, punchlist cleanup, and operational hardening.
```

Renumbering is optional. If you prefer not to add “4A,” add it as Section 3.5 or Section 4 before Architectural Priorities.

---

## 5. Architectural Priorities

The existing priorities are good but need additional post-iCloud architecture priorities.

---

### A. Provenance as a First-Class System

Keep this, but update future refinement.

Add:

```text
Cloud-native provenance identifiers remain a future refinement, especially iCloud remote asset IDs.
```

Suggested:

```markdown
Future refinement:

- richer cloud-native provenance, including remote iCloud asset identifiers when available
- separation of ingestion provenance, metadata observations, and cloud acquisition history
```

---

### B. Identity Preservation

Keep.

---

### C. Canonical Asset Model

Keep, but consider mentioning:

```text
visibility/demotion and canonical selection are now active duplicate workflows.
```

---

### D. Time as a Navigation Layer

Keep.

Add that video now has video-specific date trust:

```text
Video container metadata is part of capture-time trust handling.
```

---

### E. Local-First Scalability

Keep.

Maybe add:

```text
cloud acquisition is optional and feeds local-first storage; cloud services do not become system-of-record.
```

---

### F. Separation of User vs System Layers

Keep.

---

### G. Processing Decoupling

Update to reflect that some decoupling has already happened.

Current text says the system “must evolve” toward background processing. Revise to:

```markdown
### G. Processing Decoupling

The system is evolving from ingestion-time heavy processing toward Admin-controlled background processing.

Implemented or partially implemented:

- duplicate processing as an Admin/background process
- display preview generation
- Live Photo pairing
- face processing
- place geocoding
- stale-run recovery for selected background jobs

Future candidates:

- suggestion generation refinement
- post-intake enrichment orchestration
- scheduled source/profile processing
- additional intelligence tasks
```

---

### H. Format-Aware Asset Handling

Update this significantly.

Current text says the system must support HEIC, Live Photos, and video. These are now partially implemented.

Suggested replacement:

```markdown
### H. Format-Aware Asset Handling

The system preserves original media formats and supports format-specific handling.

Implemented:

- HEIC/HEIF display preview generation
- TIFF and content-mismatch display preview handling
- Live Photo still/MOV pairing, including icloudpd `_HEVC.MOV` companion naming
- Live Photo and Live Photo Motion badges
- MOV/MP4/M4V video-native metadata trust handling using QuickTime/container dates

Still deferred:

- Live Photo playback
- Live Photo motion companion hiding/filtering
- video playback and thumbnail UX
- broader legacy camcorder format support
```

---

### Add New Priority: I. Cloud Acquisition Boundary

Add a new priority section:

```markdown
### I. Cloud Acquisition Boundary

Cloud acquisition is a download/staging concern, not an ingestion concern.

Rules:

- icloudpd is the preferred iCloud acquisition adapter.
- Raw PyiCloud remains experimental/diagnostic.
- Cloud acquisition writes only to `storage/exports/icloud/<source_label>/`.
- Source Intake remains the only path into Drop Zone, Vault, DB, and Provenance.
- One stable iCloud source per iCloud account/library is the production rule.
- `account_username` is non-secret source metadata.
- Passwords, 2FA codes, session cookies, and auth tokens are not stored by the application.
- Local iCloud staging cleanup is allowed only after provenance + Asset + Vault verification.
```

---

### Add New Priority: J. Unified Source Profile Model

Add this as a future architectural priority.

```markdown
### J. Unified Source Profile Model

The system should evolve from separate operator steps:

```text
Source Registry
→ Cloud Acquisition
→ Source Intake
→ Cleanup
```

toward a unified Source Profile model where the operator selects a source/profile and runs intake.

A Source Profile should describe:

- source type: local folder, external drive, cloud, scan batch
- cloud type when applicable: iCloud, OneDrive, Google Photos, etc.
- account username when applicable
- root/staging path
- acquisition method
- cleanup policy
- intake defaults

Source Intake remains the ingestion authority, but cloud acquisition and cleanup should eventually become implementation details behind a unified operator workflow.

```
---

## 6. Parking Lot Integration Strategy

This section is stale.

Current “Immediate Promotion Candidates” includes:

```text
ingestion stabilization
background duplicate processing
cloud ingestion
HEIC support
```

These are now implemented or substantially implemented.

Replace with current candidates.

Suggested:

```markdown
## 5. Parking Lot Integration Strategy

Features move from parking lot to roadmap when they:

- solve real workflow friction
- improve data correctness
- unlock multiple downstream capabilities
- reduce operator risk or confusion
- improve production-scale reliability

### Immediate Promotion Candidates

- iCloud acquisition until-found / checkpoint strategy
- Source Registry archive / inactive source support
- unified Source Profile and Intake Workflow design
- acquisition + intake run history
- production-scale iCloud intake validation
- documentation and punchlist cleanup

### Mid-Term Candidates

- NAS deployment design
- scheduled acquisition / operational orchestration
- Live Photo motion companion filtering
- video thumbnails/playback
- cloud-native iCloud provenance identifiers
- post-intake enrichment workflow

### Long-Term Candidates

- multi-account cloud source management
- semantic search and tagging expansion
- landmark/location intelligence
- album-event integration
- optional sharing / access control
```

---

## 7. Constraints for Future Work

Keep existing constraints and add cloud/source constraints.

Add:

```markdown
- Source Intake remains the ingestion authority.
- Cloud acquisition must not write directly to Vault, DB, Drop Zone, or Provenance.
- iCloud staging cleanup may delete only verified local staging files, never iCloud or Vault files.
- Source identity must remain stable and auditable.
- Credential/session handling must remain explicit and secure.
- Admin automation should be guided and explainable, not silent.
```

---

## 8. Long-Term Vision

This is still good. Add mention that the system now includes operational/admin workflows and cloud acquisition into a local-first archive.

Suggested addition:

```markdown
The long-term architecture should support local and cloud sources through a unified source/profile model while preserving the local Vault as the durable archival truth.
```

---

## 9. NAS / Synology Section

The NAS section is too brief.

Current section only says planned migration for vault, database/cache, and background processing.

Replace with:

```markdown
## 8. NAS / Synology Direction

Planned migration to NAS-backed deployment remains a major platform step.

Target roles:

- Vault storage on NAS-backed filesystem
- PostgreSQL and Redis via Docker
- long-running background/admin jobs
- backup/snapshot strategy
- potential always-on iCloud acquisition support

Design considerations:

- icloudpd helper environment must be deployable on the target host
- iCloud authentication/session handling remains external/manual for now
- scheduled unattended acquisition is deferred
- local workstation may remain a development and optional processing node
- network-mounted Vault paths must preserve deterministic ingestion and provenance behavior
```

---

# Specific Stale Items to Remove or Reclassify

Do not leave these as future/current focus if already implemented:

```text
cloud ingestion as a broad future item
HEIC support as immediate candidate
Live Photo handling as mid-term candidate
background duplicate processing as immediate candidate
ingestion stabilization as immediate candidate
video handling as unsupported
```

Instead, reclassify as:

```text
implemented foundational support, with remaining hardening/UX items
```

Examples:

```text
iCloud acquisition implemented; until-found/checkpoint completeness deferred
HEIC preview implemented; broader media UX deferred
Live Photo pairing implemented; playback/filtering deferred
Video metadata trust implemented; playback/thumbnails deferred
Duplicate processing background/admin-controlled; further UX/performance refinement deferred
```

---

# Suggested Document Structure

The current structure can stay mostly intact.

Recommended final structure:

```text
1. Current State Summary
2. Development Phases
3. Milestone Reality
   - 11.x Summary
   - 12.x Summary
4. Architectural Priorities
5. Parking Lot Integration Strategy
6. Constraints for Future Work
7. Long-Term Vision
8. NAS / Synology Direction
```

The exact numbering is flexible, but avoid awkward markdown levels like:

```text
###### Phase 5
```

Use consistent heading levels:

```markdown
### Phase 5 — ...
```

---

# Style Requirements

- Keep this as a roadmap, not a detailed context file.
- Do not duplicate all of `PROJECT_CONTEXT.md`.
- Avoid milestone-by-milestone narration except for high-level milestone reality summaries.
- Prefer architectural current state and direction.
- Keep deferred items concise.
- Use clear headings and consistent markdown.
- Remove stale future statements.
- Do not include debugging details.

---

# Validation / Closeout

After updating `PROJECT_ARCHITECTURE.md`, provide a short coder response including:

1. Files changed
2. Major sections updated
3. Stale items removed or reclassified
4. New current architecture items added
5. Remaining uncertainties
6. Recommendation for next documentation file to update, likely:
   - `MILESTONE_HISTORY.md`
   - `WORKFLOW.md`
   - parking lot document

---

# Definition of Done

12.45.0 is complete when:

- Phase 5 reflects current operational hardening rather than old future plans
- iCloud acquisition is represented as active architecture
- Source Registry / Source Intake model is represented as active architecture
- iCloud staging cleanup is represented as active architecture
- HEIC/TIFF preview support is current
- Live Photo pairing status is current
- MOV/MP4 video metadata trust handling is current
- Admin background controls are current
- true remaining roadmap items are separated from implemented capabilities
- NAS section reflects current deployment direction and icloudpd considerations
- stale parking lot promotion candidates are updated
