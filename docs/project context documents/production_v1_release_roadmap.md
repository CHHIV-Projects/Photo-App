# PRODUCTION_V1_RELEASE_ROADMAP.md

# Photo Organizer — Production v1.0 Release Roadmap

## 1. Purpose

This document defines the release roadmap for **Photo Organizer Production v1.0**.

The project has reached a transition point:

```text
from continuous feature/milestone development
to production release readiness
```

The goal of v1.0 is not to complete every long-term feature. The goal is to produce a stable, safe, single-user production release that can confidently ingest and organize the real local and iCloud photo archive.

This roadmap consolidates:

- user v1.0 requirements
- punch list requirements
- coder technical gap analysis
- architecture/context updates
- deferred parking lot items
- required milestone tracks before v1.0 sign-off

Primary current-state references:

- `PROJECT_CONTEXT.md`
- `ARCHITECTURE_ROADMAP.md`
- `WORKFLOW.md`
- `MILESTONE_HISTORY.md`
- `Parking_Lot_v4.md`
- `Coder response 12.45.2.md`

---

## 2. Production v1.0 Definition

Photo Organizer v1.0 is a **single-user, local-first, NAS-backed production release** that can safely ingest, deduplicate, preserve, display, search, and organize large local and iCloud photo libraries through controlled operator workflows.

v1.0 must provide:

- clean production database
- clean production workspace / release package
- NAS-backed storage readiness
- safe local source ingestion
- safe iCloud ingestion
- non-repeat iCloud acquisition or acceptable checkpoint/until-found strategy
- verified staging cleanup
- non-destructive file handling
- clear provenance
- reliable reports and operational status
- consistent HEIC/media display
- usable Photo Review / Workbench / Admin workflows
- Collections as a high-level organization layer
- deterministic metadata/provenance-based search and filtering
- clean launch and shutdown experience

v1.0 does **not** require every advanced future feature, commercial-grade UI polish, full automation, multi-user support, or multi-cloud account support.

---

## 3. v1.0 Guiding Principle

Production v1.0 should be:

```text
safe enough, stable enough, understandable enough, and clean enough
to ingest and manage the real production archive.
```

This means:

- correctness over automation
- operator clarity over hidden behavior
- non-destructive storage over convenience
- clean production state over carrying test history forward
- local-first architecture over cloud dependency
- controlled workflows over silent background magic

---

## 4. v1.0 Scope

## 4.1 In Scope

Production v1.0 includes:

```text
single-user operation
NAS-backed storage/deployment path
development vs production separation
clean production database
clean production workspace/release package
safe local source ingestion
safe iCloud ingestion
non-repeat iCloud acquisition / checkpoint / until-found equivalent
verified iCloud staging cleanup
HEIC thumbnails/previews across UI
Live Photo motion companion filtering
Photo Review as primary viewing/organizing surface
Photo Detail as low-level inspection surface
Workbench correction tools
Admin ingestion/operations area
Collections
Event ↔ Album integration
Place/address correction
metadata / EXIF / provenance search facets
multi-select Photo Review actions
demotion / visibility controls
controlled background jobs
clean launcher/start/stop experience
```

---

## 4.2 Explicitly Out of Scope for v1.0

The following are not required for v1.0:

```text
multi-user support
multiple cloud accounts
multiple user profiles
commercial-grade UI polish
Live Photo playback
full video playback
advanced video thumbnail workflow
face suggestion algorithm overhaul
learning from larger merged face clusters
ignored cluster recovery
duplicate suggestion methodology redesign
semantic AI search
landmark recognition
automatic scheduled NAS iCloud sync
credential/session manager
external sharing
mobile app
role-based access control
full one-click automation of all intake/enrichment steps
```

Some of these may remain in the parking lot for v1.1+.

---

## 5. Release Pillars

## Pillar 1 — Production Ingestion Safety

v1.0 must allow safe ingestion of large real-world libraries.

Required:

- local source intake
- iCloud acquisition + intake
- registered source identity
- source run controls
- deterministic skip-known behavior
- failed/deferred handling
- clear run reports
- controlled intake limits
- operator-controlled runs
- no silent destructive actions
- verified staging cleanup
- ability to ingest tens of thousands of assets across multiple sessions

---

## Pillar 2 — NAS-Backed Deployment and Release Separation

v1.0 must support a production deployment distinct from the development workspace.

Required:

- NAS-backed Vault/storage plan
- Docker/database/cache plan
- dev/prod configuration separation
- dev/prod database separation
- dev/prod storage root separation
- release version/tag process
- backup/restore process
- production launcher/start/stop procedure

---

## Pillar 3 — Clean Production Database and Workspace

v1.0 must not use the current development database as production.

Required:

- clean DB initialization
- schema setup/migration process
- no trial iCloud sources in production DB
- no experimental ingestions in production DB
- no manipulated test data in production DB
- clean production source setup
- clean production workspace/release package
- separation of runtime artifacts from development notes/prompts/logs/tests

---

## Pillar 4 — Reliable Media Display

All important media must be viewable consistently.

Required:

- HEIC/HEIF thumbnails work everywhere
- display previews used consistently
- TIFF/content-mismatch preview support remains functional
- Live Photo stills display normally
- Live Photo motion companions are identifiable and hideable/filterable
- duplicate review surfaces show large enough previews
- portrait/landscape images are not misleadingly cropped in review contexts

---

## Pillar 5 — Coherent UI Structure

v1.0 should organize the UI around:

```text
Photo Review = main viewing/organizing workspace
Photo Detail = low-level asset inspection workspace
Workbench = specialized correction tools
Admin = operations/configuration/logs
```

v1.0 does not require commercial-grade polish, but the UI should no longer feel like scattered development tabs.

---

## Pillar 6 — Organization Model

v1.0 must support organization through:

```text
people
events
albums
collections
places
metadata/provenance facets
visibility/demotion state
```

Collections are required.

---

## Pillar 7 — Search and Discovery

v1.0 must support deterministic search/filtering across major archival dimensions:

```text
person
time/date
date trust
album
collection
event label
place/location label
geographic location
camera / EXIF
source / provenance
media type
Live Photo
video
visibility / demotion
```

Natural-language semantic search is not required for v1.0.

---

## 6. Current Technical State Summary

Coder technical review confirmed that the system already has strong foundations:

Already implemented or close:

- Source Registry
- Source Intake
- iCloud acquisition via `icloudpd`
- iCloud staging cleanup
- non-destructive Vault/provenance architecture
- exact SHA-256 dedupe
- Live Photo pairing
- video metadata trust handling
- Admin operational cards
- duplicate group/suggestion pagination
- base album CRUD and asset membership

Partially implemented:

- production start/stop
- dev/prod deployment separation
- clean DB initialization
- HEIC preview usage across all surfaces
- Photo Review as primary workspace
- Admin run visibility/history

Clearly missing or incomplete:

- non-repeat iCloud acquisition strategy
- true Collections model above albums/events
- Event ↔ Album integration
- Photo Review multi-select batch actions
- unified acquisition/intake/cleanup history
- dedicated Admin Ingestion tab
- production packaging/launcher
- workspace/release cleanup process

---

## 7. Major Technical Risks

Coder identified these major risks:

```text
iCloud repeat-download behavior after staging cleanup
current Album implementation already uses collections tables
HEIC preview inconsistency across API surfaces
production release contamination from dev/test artifacts
Collections/Event/Album integration data-model complexity
NAS permissions/path behavior differing from Windows
```

These risks drive the milestone order below.

---

# 8. v1.0 Release Tracks

## Track A — Production Deployment / Runtime Baseline

### Goal

Define and implement the minimum acceptable production runtime model.

### Required Outcomes

- dev/prod environment profiles
- production config pattern
- production storage root settings
- production DB settings
- start/stop scripts
- health checks
- browser auto-open
- minimized/suppressed command window behavior where practical
- log location
- troubleshooting steps

### Minimum v1.0 Launcher

A scripted launcher with desktop shortcut/icon is acceptable.

Required:

```text
start Docker/services/backend/frontend in correct order
perform readiness checks
open app automatically
minimize/suppress command windows where practical
provide clean stop/shutdown script
document logs/troubleshooting
```

A packaged desktop shell or installer can wait until after v1.0.

### Likely Milestone

```text
12.46 — Production Runtime Baseline and Launcher Design
```

---

## Track B — Clean Production DB / Workspace / Release Package

### Goal

Define and implement a clean production release boundary.

### Required Outcomes

- clean production DB initialization process
- schema ensure/migration process
- production source creation flow
- release package manifest
- runtime-required file list
- development/test artifact separation
- storage folder initialization
- production bootstrap checklist

### Key Requirement

Do **not** promote the current development DB as production.

### Required Production DB State

```text
empty or clean schema
no test sources
no trial iCloud sources
no experimental ingestion runs
no manipulated validation records
only real production records after production intake begins
```

### Likely Milestone

```text
12.47 — Clean Production Bootstrap and Release Package
```

---

## Track C — iCloud Non-Repeat Acquisition / Checkpoint Strategy

### Goal

Prevent or mitigate repeated iCloud downloads after staging cleanup and avoid forcing the operator to keep increasing `recent_count`.

### Current Issue

Fixed-window acquisition can re-download recently cleaned files because `icloudpd` skip-existing depends on files still being present in staging.

### Required Outcome

Operator should not need to repeatedly download the same recent files or keep increasing `recent_count` to know whether new files exist.

### Possible Strategies

```text
icloudpd --until-found
recent + checkpoint
known-threshold stop
provenance-based known detection
cloud asset ID checkpoint if available
```

### Minimum Acceptable v1.0

If `icloudpd --until-found` is reliable, use it.

If not, a `recent + checkpoint + known-threshold stop` strategy is acceptable.

UI/reporting must explain whether acquisition is:

```text
caught up
partial
recent window checked only
unknown
```

### Likely Milestone

```text
12.48 — iCloud Non-Repeat Acquisition Strategy
```

Design-first, then implementation.

---

## Track D — HEIC / Display Preview Consistency

### Goal

Fix HEIC/media display across all major UI surfaces.

### Required Outcomes

HEIC thumbnails/previews must work in:

```text
Face Review
People
Unassigned Faces
Albums
Events
Timeline
Places
Duplicate Groups
Duplicate Suggestions
Photo Detail
Photo Review
Presentation mode
```

### Technical Direction

Coder identified a likely central fix:

```text
enforce one backend image-url builder contract that returns display preview URL when available
```

Audit all API surfaces that build image URLs.

### Likely Milestone

```text
12.49 — Centralized Display Preview URL Contract
```

---

## Track E — Workbench Naming / Layout / Basic UX Cleanup

### Goal

Make the Workbench usable and less development-oriented.

### Required Outcomes

- rename `Review` to `Face Review`
- rename `Photos` to `Photo Detail`
- improve global screen-width usage
- reduce obvious unused whitespace
- bounded scroll/pagination for long lists
- Face Review cluster pagination/next controls
- Unassigned Faces create-cluster bug fixed
- larger/clearer duplicate preview layouts
- HEIC thumbnails fixed through Track D

### Deferred Beyond v1.0

- face suggestion algorithm overhaul
- learning from larger clusters
- ignored cluster recovery
- commercial-grade design polish

### Likely Milestone

```text
12.50 — Workbench Naming and Layout Cleanup
```

---

## Track F — Photo Review as Main Organizing Workspace

### Goal

Make Photo Review the primary surface for viewing and organizing.

### Required Outcomes

- universal search/filter expansion
- thumbnail spacing/layout cleanup
- image click opens presentation mode
- Open Detail button opens Photo Detail
- demoted/not-demoted toggle
- hide/filter Live Photo motion companions
- multi-select framework
- batch demotion / restore
- add selected photos to album
- create album from selected photos
- add selected photos to collection
- create collection from selected photos

### v1.0 Minimum Batch Actions

Required:

```text
multi-select
batch demote/restore
add to existing album
create album from selection
add to existing collection
create collection from selection
```

Optional if time allows:

```text
assign selected photos to event
bulk date trust edit
bulk place edit
bulk user tags
```

### Likely Milestone

```text
12.51 — Photo Review Batch Actions and Core Filters
```

May need to split into multiple milestones.

---

## Track G — Organization Model: Collections, Albums, Events, Places

### Goal

Complete the v1.0 organization model.

---

## G1 — Collections

Collections are required for v1.0.

### Definition

Collections are high-level user-defined containers above albums and events.

A collection may include:

```text
individual photos
albums
events
```

A photo may belong to more than one collection.

Linked albums and linked events are **live references**.

If photos are later added to a linked album or event, those photos automatically appear in the collection.

Collection views must de-duplicate resolved photos so the same asset is displayed only once.

### v1.0 Required Operations

- create collection
- edit collection name/description
- add/remove individual photos
- link/unlink album
- link/unlink event
- view resolved collection photos
- de-duplicate resolved collection asset list
- filter/search by collection
- add selected Photo Review assets to collection
- create collection from selected photos

### Technical Warning

Coder identified a schema ambiguity:

```text
current Albums are already backed by collections / collection_assets tables
```

Therefore Collections require a design-first milestone.

### Likely Milestone

```text
12.52 — Collections and Album/Event Linking Design
```

Then implementation milestone(s).

---

## G2 — Event ↔ Album Integration

v1.0 requires:

- create album from event
- add event photos to album
- link event to collection
- event merge/label workflows remain understandable
- event target dropdowns prioritize labeled events
- one-photo events can be hidden/excluded

---

## G3 — Place Address Editing

v1.0 requires:

- edit/correct low-level address fields
- preserve user-defined place labels
- search/filter by place/geography
- do not alter GPS silently

Example:

```text
3 Via Espiritu → 5 Via Espiritu
```

---

## G4 — Tags / Metadata / Provenance Facets

v1.0 does not require a heavy free-form tag system.

Minimum requirement:

```text
Expose deterministic metadata/provenance-derived facets for search, filtering, and organization.
```

Candidate facets:

```text
source label
source folder/path
camera make/model
file/media type
date/year/month
date trust
place/location label
event label
album membership
collection membership
Live Photo
video
demoted/visible status
```

### Likely Milestones

```text
12.52 — Collections / Album / Event Design
12.53 — Collections Implementation
12.54 — Event/Album/Place Organization Improvements
12.55 — Metadata/Provenance Search Facets
```

---

## Track H — Admin Ingestion UX and Operational History

### Goal

Make Admin operations cohesive and understandable.

### Required Outcomes

- dedicated Admin Ingestion area/tab
- Source Registry, local intake, iCloud acquisition, cleanup grouped together
- bounded source lists/tables
- source status visible
- current/latest runs visible
- report access
- unified acquisition/intake/cleanup history minimum support
- guided next action after each step

### v1.0 Minimum

One coherent guided flow is required.

Full one-click automation is not required.

Minimum acceptable flow:

```text
Admin → Ingestion
  choose source/profile
  if local: run Source Intake
  if iCloud: run acquisition/check, then Source Intake, then cleanup
  show status/results in one area
```

### Likely Milestone

```text
12.56 — Admin Ingestion Workspace and Operational History
```

---

## Track I — Production-Scale Validation

### Goal

Validate v1.0 with representative real-world data before release sign-off.

### Required Validation

- clean production-like DB
- NAS-backed or NAS-simulated storage path
- local source test with large file count
- iCloud source test with meaningful recent batch
- HEIC display validation across core surfaces
- Live Photo pairing and motion hiding validation
- Source Intake reports validation
- iCloud cleanup validation
- no duplicate Asset creation for repeated runs
- Vault integrity check
- startup/shutdown validation
- backup/restore sanity check if available

### Suggested Initial Acceptance Target

Exact counts can be finalized later, but a v1.0 release candidate should be tested with:

```text
at least one large local source
at least one iCloud source
HEIC + JPG + MOV + Live Photo samples
repeat intake/acquisition runs
cleanup after intake
```

### Likely Milestone

```text
12.57 — Production v1.0 Trial Runbook and Validation
```

---

# 9. Coder Gap Analysis Answers Incorporated

## 9.1 Launcher

Decision:

```text
scripted launcher with shortcut/icon is acceptable for v1.0
packaged desktop shell can wait
```

## 9.2 Collections

Decision:

```text
Collections required for v1.0
photos + albums + events only initially
albums/events are live references
places/saved searches can wait
```

## 9.3 iCloud Non-Repeat

Decision:

```text
recent + checkpoint + known-threshold stop is acceptable
if icloudpd --until-found is unreliable
```

## 9.4 Run History Retention

Decision:

```text
retain acquisition/intake/cleanup/report history long enough for audit/troubleshooting
no aggressive pruning in v1.0
```

## 9.5 Batch Actions

Decision:

```text
Photo Review is primary place for batch organization actions
Album/Event/Collection pages may keep overlapping actions
```

## 9.6 Production Validation

Decision:

```text
representative production-scale validation required before v1.0 sign-off
exact asset count target to be finalized
```

## 9.7 Albums vs Collections Schema

Decision:

```text
design-first milestone required
do not blindly rebrand current album-backed collections tables
```

## 9.8 Dev/Prod Separation

Decision:

```text
one repo with profile-based runtime separation is acceptable
if dev/prod DB, storage, and config are safely separated
```

---

# 10. Proposed v1.0 Milestone Sequence

This sequence may be adjusted after implementation reconnaissance.

## 12.46 — Production Runtime Baseline and Launcher Design

- dev/prod profiles
- start/stop scripts
- health checks
- browser auto-open
- NAS path assumptions
- runtime logs

## 12.47 — Clean Production Bootstrap and Release Package

- clean DB initialization
- schema/migration startup
- release package manifest
- runtime vs dev/test artifact separation
- production source seed flow

## 12.48 — iCloud Non-Repeat Acquisition Strategy

- design-first until-found/checkpoint decision
- integrate selected strategy
- reporting clarity
- repeat-run validation after cleanup

## 12.49 — Centralized Display Preview URL Contract

- audit all UI/API image surfaces
- fix HEIC thumbnail inconsistency
- enforce preview URL use
- duplicate preview improvement foundation

## 12.50 — Workbench Naming and Layout Cleanup

- Review → Face Review
- Photos → Photo Detail
- global width/layout pass
- cluster list pagination
- Unassigned Faces bug
- bounded lists/tables

## 12.51 — Photo Review Batch Actions and Core Filters

- multi-select
- demote/restore
- album/collection actions
- Live Photo motion filter
- presentation-on-click
- key search/filter expansion

## 12.52 — Collections / Album / Event Design

- resolve current album/collections table ambiguity
- define true Collections model
- define live album/event references
- define resolved asset dedupe
- define migration strategy

## 12.53 — Collections Implementation

- DB/model/API/UI
- direct photo membership
- album/event links
- resolved photo view
- collection search/filter

## 12.54 — Event / Album / Place Organization Improvements

- event-to-album
- event-to-collection
- labeled event merge target improvements
- hide one-photo events
- low-level place address editing

## 12.55 — Metadata / EXIF / Provenance Search Facets

- source/provenance search
- EXIF/camera facets
- event/album/collection/place facets
- media type/date trust/visibility facets

## 12.56 — Admin Ingestion Workspace and Operational History

- dedicated Ingestion tab
- local/cloud guided intake flow
- bounded source tables
- unified acquisition/intake/cleanup status/history
- report access

## 12.57 — Production v1.0 Trial Runbook and Validation

- clean DB trial
- NAS/simulated NAS storage
- local + iCloud ingestion tests
- repeat-run validation
- cleanup validation
- display validation
- release sign-off checklist

---

# 11. Deferred Beyond v1.0

The following remain post-v1.0 unless later promoted:

```text
multi-user support
multiple cloud accounts
credential/session manager
scheduled unattended NAS iCloud acquisition
Live Photo playback
full video playback
advanced video thumbnails
semantic AI search
landmark recognition
face suggestion algorithm overhaul
ignored cluster recovery
duplicate suggestion methodology redesign
commercial-grade UI redesign
external sharing
mobile app
role-based access control
```

---

# 12. Open Questions Before Final v1.0 Plan Lock

These should be resolved as the roadmap begins.

1. What is the exact production host model?
   
   - PC runs app with NAS storage?
   - NAS runs database/backend?
   - hybrid?

2. What is the minimum acceptable NAS validation before v1.0?

3. What is the minimum acceptable launcher?
   
   - shortcut + scripts?
   - hidden/minimized terminal?
   - app-like browser window?
   - later desktop shell?

4. What is the minimum production-scale asset count for sign-off?

5. Should Collections implementation happen before Photo Review batch actions, or should batch selection framework come first?

6. Should Admin Ingestion workspace come before or after iCloud non-repeat?

7. Do we need a formal backup/restore milestone before first production ingestion?

---

# 13. v1.0 Release Acceptance Criteria

Production v1.0 can be accepted when the user can:

## Deployment

- start app cleanly
- stop app cleanly
- confirm dev/prod separation
- confirm clean production DB
- confirm NAS-backed or production-intended storage

## Ingestion

- run local source intake safely
- run iCloud acquisition/intake safely
- avoid repeated iCloud downloads or use accepted checkpoint/until-found strategy
- clean verified staging files
- review reports
- repeat runs without duplicate Asset creation

## Display

- view HEIC assets across major surfaces
- review duplicates visually
- hide Live Photo motion companions
- inspect media details

## Organization

- use Photo Review as main browsing surface
- use Photo Detail for low-level inspection
- create/use albums
- create/use collections
- link albums/events into collections
- use place/address corrections
- search/filter by key metadata/provenance/organization facets

## Operations

- use Admin Ingestion area
- see source/run status
- access reports/logs
- understand next steps
- recover from failed/deferred runs

## Safety

- confirm no original files are destructively modified
- confirm Vault files are preserved
- confirm cleanup affects only verified local staging copies
- confirm demotion/visibility is reversible
- confirm source/provenance integrity

---

# 14. Immediate Next Step

Start the next chat with this roadmap and the current core documentation bundle.

Then proceed with:

```text
12.46 — Production Runtime Baseline and Launcher Design
```

or, if preferred, first run a brief planning pass:

```text
12.46 — v1.0 Release Plan Finalization and Track Ordering
```

The recommended next step is to begin with runtime/deployment because it affects DB, workspace, NAS paths, launcher expectations, and production validation.

```
---

Now the continuation prompt for the next chat:

````markdown
# New Chat Continuation Prompt — Photo Organizer Production v1.0 Planning

You are helping me continue development of my local-first AI Photo Organizer project.

## Your Role

You are the **architect / planner / prompt generator**.

I am the **project owner / tester / decision maker**.

Coder is **GitHub Copilot in VS Code**, responsible for implementation.

Your job is to:

- maintain architecture consistency
- help define milestones
- write precise `.md` prompts for coder
- review coder questions/responses
- classify scope and parking lot items
- protect the non-destructive architecture
- keep the project moving toward Production v1.0

## Current Project Direction

We are transitioning from open-ended milestone development to defining and implementing **Production v1.0**.

Production v1.0 means:

```text
single-user
local-first
NAS-backed
clean production database
clean production workspace/release package
safe large-library ingestion
safe iCloud ingestion
non-destructive storage
clear provenance
reliable reports
usable Photo Review / Workbench / Admin workflows
clean launcher/start/stop experience
```

The system already has strong foundations:

- Source Registry
- Source Intake
- iCloud acquisition through `icloudpd`
- iCloud staging cleanup
- exact dedupe
- provenance
- metadata canonicalization
- Live Photo pairing
- video metadata trust
- HEIC/TIFF display preview generation
- Admin background job controls

The main v1.0 work is now release readiness, workflow cohesion, media display consistency, UI cleanup, organization model completion, and production deployment.

## Documents I Am Attaching

I am attaching the current core documents:

```text
PROJECT_CONTEXT.md
ARCHITECTURE_ROADMAP.md
WORKFLOW.md
MILESTONE_HISTORY.md
Parking_Lot_v4.md
PRODUCTION_V1_RELEASE_ROADMAP.md
```

I may also attach a sample prior milestone prompt so you can maintain the same prompt style.

Use these documents as the source of truth.

## Important Workflow

We use milestone-driven development.

Typical cycle:

```text
1. ChatGPT creates milestone prompt
2. I give prompt to coder
3. Coder does pre-coding reconnaissance and asks questions
4. I bring questions back to ChatGPT
5. ChatGPT answers decisively
6. Coder implements
7. Coder writes "Coder response xx.xx.md"
8. ChatGPT reviews response
9. I test and commit/tag
10. We move to next milestone
```

Coder response files are stored in the workspace, typically:

```text
docs/prompts/Coder response <milestone>.md
```

## Current Status

We just completed the documentation refresh arc:

```text
12.45 — PROJECT_CONTEXT refresh
12.45.0 — ARCHITECTURE_ROADMAP refresh
12.45.1 — WORKFLOW refresh
12.45.2 — Production v1.0 requirements / technical gap analysis
```

We now need to begin the v1.0 release roadmap.

## Production v1.0 Release Tracks

The proposed v1.0 milestone tracks are:

```text
12.46 — Production Runtime Baseline and Launcher Design
12.47 — Clean Production Bootstrap and Release Package
12.48 — iCloud Non-Repeat Acquisition Strategy
12.49 — Centralized Display Preview URL Contract
12.50 — Workbench Naming and Layout Cleanup
12.51 — Photo Review Batch Actions and Core Filters
12.52 — Collections / Album / Event Design
12.53 — Collections Implementation
12.54 — Event / Album / Place Organization Improvements
12.55 — Metadata / EXIF / Provenance Search Facets
12.56 — Admin Ingestion Workspace and Operational History
12.57 — Production v1.0 Trial Runbook and Validation
```

The next expected milestone is probably:

```text
12.46 — Production Runtime Baseline and Launcher Design
```

But before writing a coding prompt, please first review the attached docs and confirm whether 12.46 is the right next step or whether we should do a short planning/ordering milestone first.

## Key v1.0 Requirements

v1.0 requires:

- NAS-backed storage/deployment path
- dev/prod separation
- clean production database
- clean production workspace/release package
- safe large local source ingestion
- safe iCloud ingestion
- non-repeat iCloud acquisition / until-found or equivalent
- verified staging cleanup
- HEIC thumbnails/previews everywhere
- Live Photo motion companion hiding/filtering
- Photo Review as main viewing/organizing surface
- Photo Detail as low-level inspection surface
- Workbench cleanup
- Admin Ingestion area
- Collections
- Event ↔ Album integration
- Place/address editing
- metadata / EXIF / provenance search facets
- multi-select Photo Review actions
- clean launcher/start/stop experience

## Important Architecture Rules

Do not violate these:

- Vault is immutable canonical storage.
- Source Intake is the ingestion authority.
- Cloud acquisition writes only to exports staging.
- iCloud staging cleanup deletes only verified local staging files.
- Do not delete from iCloud.
- Do not delete from Vault.
- Do not store Apple ID password, 2FA, session cookies, or auth tokens.
- Account username is non-secret source metadata only.
- Identity and curation remain human-controlled.
- Prefer deterministic/explainable rules over opaque automation.
- Do not introduce silent destructive behavior.

## Immediate Request

Please review the attached documents and help me decide the first milestone in the Production v1.0 roadmap.

If you agree with 12.46, prepare a milestone prompt for:

```text
12.46 — Production Runtime Baseline and Launcher Design
```

This should likely be design-first or implementation-light, because we need to decide:

- development vs production runtime profiles
- NAS role vs PC role
- storage paths
- Docker/backend/frontend startup order
- launcher options
- shutdown approach
- health checks
- log locations
- production config separation
- what counts as minimum acceptable v1.0 launch UX

Do not rush into code if design decisions are needed first.
