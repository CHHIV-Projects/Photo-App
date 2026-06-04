# Milestone 12.45.2 — PRODUCTION_V1_REQUIREMENTS.md

# Photo Organizer — Production v1.0 Requirements

## 1. Purpose

This document defines what must be true before Photo Organizer can be called **Production v1.0**.

The project has reached a point where the core engine is powerful, but development has become an open-ended sequence of milestones. Production v1.0 establishes a clear release target:

```text
Stable enough, safe enough, clean enough, and usable enough to ingest and organize the real production photo archive.
```

This document is not a milestone history and not a parking lot.

It defines:

- what v1.0 means
- what is required for v1.0
- what is explicitly out of scope
- what must be technically reviewed by coder
- what must be accepted by the user before release
- which future items remain deferred

---

## 2. Definition of Production v1.0

Photo Organizer v1.0 is a **single-user, local-first, NAS-backed production release** that can safely ingest, deduplicate, preserve, display, search, and organize large local and iCloud photo libraries through controlled operator workflows.

v1.0 must provide:

- non-destructive storage
- clear provenance
- reliable ingestion reporting
- safe local and iCloud intake
- clean production database
- clean production workspace/release package
- NAS-backed storage readiness
- usable review and curation interface
- controlled Admin operations
- consistent display of modern photo formats
- clean startup and shutdown experience

v1.0 does **not** mean every future intelligence, automation, sharing, or UI-polish feature is complete.

v1.0 means the system is ready for real production use by the owner.

---

## 3. v1.0 Product Scope

### Included in v1.0

Production v1.0 includes:

```text
single-user operation
NAS-backed storage and deployment plan
clean production database
clean production workspace / release package
safe local source ingestion
safe iCloud ingestion
non-repeat iCloud acquisition / until-found or equivalent strategy
verified iCloud staging cleanup
non-destructive archival storage
HEIC thumbnails and display previews working across UI
Live Photo preservation and motion companion filtering
Photo Review as primary viewing/organizing workspace
Photo Detail as low-level inspection workspace
Workbench tools for face/event/album/place/duplicate correction
Admin operations for ingestion, sources, cleanup, logs, and background jobs
Collections as a higher-level organizing layer above albums and events
metadata / EXIF / provenance-based search and filtering
manual controlled runs for large libraries
clean launcher/start/stop experience
```

### Excluded from v1.0

The following are explicitly **not required** for v1.0:

```text
multi-user support
multiple cloud accounts
multiple user profiles
commercial-grade UI polish
Live Photo playback
full video playback experience
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
```

Some excluded items may still exist partially, but they are not release blockers.

---

## 4. Release Pillars

Production v1.0 is organized around seven release pillars.

---

### Pillar 1 — Production Ingestion Safety

The system must confidently and safely ingest large real-world libraries.

Required:

- local folder ingestion
- iCloud acquisition and intake
- source registry / source identity
- source intake run controls
- deterministic skip-known behavior
- clear failed/deferred handling
- clear run reports
- operator-controlled ingestion limits
- no silent destructive actions
- verified cleanup of temporary staging files
- ability to ingest tens of thousands of assets safely over multiple sessions

---

### Pillar 2 — NAS-Backed Deployment and Release Separation

The system must support a production deployment distinct from the development workspace.

Required:

- NAS-backed Vault/storage plan
- Docker-based database/cache plan
- local development version remains separate
- production version can be promoted from tested development versions
- production config is distinct from development config
- release/tag/version process is defined
- backup/restore strategy exists before large production ingestion

---

### Pillar 3 — Clean Production Database and Workspace

v1.0 must not use the current development database as production.

Required:

- clean production database initialization
- schema setup/migration process
- removal of test ingestions, trial sources, and manipulated records from production state
- clean workspace/release package
- separation of runtime data, logs, prompts, test scripts, and production code
- clear production folder structure
- clear dev/archive folder structure

---

### Pillar 4 — Reliable Media Display

All production-relevant media must be viewable consistently.

Required:

- HEIC/HEIF thumbnails work everywhere
- display previews are used consistently across UI surfaces
- TIFF/mislabeled image preview support remains functional
- Live Photo stills display normally
- Live Photo motion companion MOVs are identifiable and optionally hidden/filtered
- duplicate review surfaces show sufficiently large, uncropped previews
- portrait/landscape thumbnails should not be misleadingly cropped in review contexts

---

### Pillar 5 — Coherent UI Structure

The UI should be organized around clear user roles:

```text
Photo Review = main viewing and organizing surface
Photo Detail = low-level inspection surface
Workbench = specialized correction tools
Admin = operations and configuration
```

v1.0 does not need commercial-grade polish, but it must be understandable and not clumsy enough to cause mistakes.

---

### Pillar 6 — Organization Model

v1.0 must support real-world organization across:

```text
people
events
albums
collections
places
metadata/provenance tags
visibility/demotion state
```

Collections are required for v1.0.

---

### Pillar 7 — Search and Discovery

v1.0 must support search/filtering across major archival dimensions:

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

---

## 5. Production Deployment Requirements

### 5.1 NAS-Backed Storage

The production system must support NAS-backed storage.

Required decisions:

- where Vault lives
- where previews live
- where exports/staging live
- where logs/reports live
- where database files live
- where Docker volumes live
- how backups/snapshots are handled

Expected direction:

```text
Vault: NAS-backed storage
Database/cache: Docker-managed, potentially NAS/server-hosted
Frontend/backend: production launcher or service wrapper
Development machine: remains separate from production release
```

### 5.2 Development vs Production Separation

There must be a clear distinction between:

```text
development environment
production environment
historical/test artifacts
runtime production data
```

Required:

- development DB and production DB separated
- development storage and production storage separated
- production config file(s) separated from development config
- production startup does not depend on historical prompt/test folders
- tested development changes can be promoted to production versions

### 5.3 Version Promotion

v1.0 should establish a release promotion pattern:

```text
develop/test locally
commit/tag version
validate release checklist
promote to production workspace
run production startup
confirm health
```

Future versions may follow:

```text
v1.0
v1.1
v1.2
...
```

---

## 6. Clean Production Database Requirements

The current development database contains test records, trial ingestions, experimental iCloud sources, failed runs, and validation artifacts.

v1.0 must use a clean production database.

Required:

- initialize clean production DB
- apply current schema/migrations
- create only real production sources
- avoid carrying over test sources unless intentionally migrated
- avoid carrying over trial ingestion runs
- avoid carrying over manipulated test data
- validate first production ingestion end-to-end

Production DB acceptance criteria:

```text
no test source clutter
no trial iCloud sources
no obsolete run records
no experimental adapter artifacts
only real production assets after production intake begins
schema matches current application expectations
```

Open technical question for coder:

```text
What is the cleanest supported way to initialize a production DB with current schema?
```

---

## 7. Clean Production Workspace / Release Package Requirements

The current workspace contains development artifacts such as:

```text
test scripts
experimental scripts
prompt files
coder responses
logs
trial exports
temporary reports
manual notes
debug artifacts
old staging folders
```

v1.0 must define a clean production workspace.

Required production package contents:

```text
backend application code
frontend application code/build
Docker configuration
startup/shutdown scripts
production config templates
schema/migration/init scripts
operator docs
empty required storage folder structure
```

Should not be required in production runtime package:

```text
historical prompts
coder responses
experimental PyiCloud scripts
old reports
test exports
temporary validation scripts
development-only notes
```

These may remain in the development workspace or documentation archive.

Open technical question for coder:

```text
Which current files/scripts are required for production runtime, and which are development/test artifacts?
```

---

## 8. Startup / Shutdown / Launcher Requirements

Production v1.0 must provide a clean start/stop experience.

User requirement:

```text
Packaged program icon to start program.
Suppress command screens.
Clean open and exit of program.
Open a single app/browser window or app-like browser tab.
Avoid obvious development-console feel.
```

Internal implementation may still use:

```text
Docker
backend service
frontend service
browser/webview
```

But operator experience should be:

```text
double-click Photo Organizer
→ required services start
→ UI opens
→ user works
→ clean shutdown available
```

Minimum acceptable v1.0:

- one launcher script or shortcut
- suppressed/minimized terminal windows where practical
- Docker/backend/frontend started in correct order
- browser opens to correct local URL
- shutdown script or UI-assisted shutdown documented
- clear troubleshooting instructions

Future post-v1.0:

- fully packaged desktop shell
- installer
- background service manager
- branded app window

---

## 9. Ingestion Requirements

### 9.1 Local Source Ingestion

Required:

- registered local sources
- deterministic source intake
- skip-known behavior
- controlled batch/source limits
- failed/deferred handling
- clear reports
- ability to ingest large folders over multiple sessions
- no duplicate Asset rows for identical files
- provenance preserved

### 9.2 iCloud Ingestion

Required:

- one stable iCloud source per iCloud account for v1.0
- `icloudpd` acquisition supported
- source has non-secret account username
- no password/2FA/session tokens stored by Photo Organizer
- acquisition downloads only to local staging
- Source Intake remains ingestion authority
- staging cleanup available after verified ingestion
- run reports visible/accessible
- non-repeat acquisition strategy implemented or equivalent mitigation

### 9.3 Non-Repeat Cloud Acquisition

Current fixed-window acquisition may re-download files after staging cleanup.

v1.0 requires a solution or minimum acceptable strategy.

Required goal:

```text
The operator should not have to keep increasing recent_count or repeatedly download the same recent files to determine whether new iCloud files exist.
```

Possible approaches:

```text
icloudpd --until-found strategy
Photo Organizer checkpoint
provenance-based known detection
cloud asset ID tracking if available
recent window + consecutive-known threshold
```

Minimum acceptable v1.0 behavior must be defined after technical review.

Coder must explicitly review:

```text
Can icloudpd --until-found solve the v1.0 non-repeat acquisition requirement?
If yes, what are the risks and required implementation steps?
If no, what alternative is recommended?
```

### 9.4 iCloud Staging Cleanup

Required:

- dry-run preview
- explicit operator-triggered cleanup
- delete only local staging files
- require provenance + Asset + Vault verification
- never delete iCloud originals
- never delete Vault files
- never delete DB/provenance/source records
- report skipped files and reasons
- source root remains usable

---

## 10. Media Display Requirements

### 10.1 HEIC Thumbnails and Previews

This is a v1.0 blocker.

HEIC thumbnails/previews must work consistently across:

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

This should be solved centrally, not page-by-page.

Requirement:

```text
All UI image surfaces must use display preview URLs when browser-native rendering is not reliable.
```

Coder must review:

```text
What shared thumbnail/image components exist?
Where are HEIC thumbnails still bypassing display preview URLs?
What is the lowest-risk centralized fix?
```

### 10.2 Duplicate Review Image Size

Required:

- Duplicate Groups and Duplicate Suggestions must show large enough images for real visual comparison
- portrait/landscape images should not be misleadingly cropped
- presentation/large preview option should be available or easy to access

### 10.3 Live Photo Motion Companion Filtering

Required:

- Live Photo stills remain visible
- motion companion MOV assets are preserved
- user can hide/filter Live Photo motion companion assets in normal browsing
- user can still access motion companion when needed

Playback is not required for v1.0.

### 10.4 Video

v1.0 requires video assets to be preserved and understandable.

Required:

- video metadata trust handling remains functional
- video assets can be identified/filtered
- video playback is not required for v1.0
- video thumbnails are not required unless needed for basic usability

---

## 11. UI / Workflow Requirements

## 11.1 Main UI Groupings

Production UI should be organized conceptually into:

```text
Workbench
Photo Review
Photo Detail
Admin
```

---

## 11.2 Workbench

Workbench contains specialized correction and management tools.

Current/expected tabs include:

```text
Face Review
People
Unassigned Faces
Albums
Timeline
Events
Places
Duplicate Groups
Duplicate Suggestions
```

### Face Review

Required:

- rename `Review` to `Face Review`
- create new person from Face Review
- merge/move clusters by Person where possible, not only random numeric cluster IDs
- improve default sort:
  - clusters with assigned persons first
  - then most-to-least significant/large clusters
- pagination or next button beyond 50 clusters
- cluster tile should have its own vertical scroll where appropriate
- HEIC thumbnails work
- use available screen width

Not v1.0 blockers unless later elevated:

```text
face suggestion algorithm improvement
learning from larger merged clusters
ignored cluster recovery
```

### People

Current People page may be redundant.

v1.0 requirement:

- either improve as a lightweight person management page, or integrate its key functionality into Face Review
- create person must be easy
- person-to-cluster relationships must be understandable
- HEIC thumbnails work
- use available screen width

Full page consolidation is not required for v1.0 if functionality is present.

### Unassigned Faces

v1.0 requirement:

- unassigned faces workflow must work reliably
- creating a new cluster/person from unassigned face must not make item disappear incorrectly
- may be merged into Face Review or retained as separate tab
- HEIC thumbnails work
- use available screen width

### Albums

v1.0 requirement:

- albums can be created, searched/listed, and viewed
- adding photos should be more effective through Photo Review multi-select and Photo Detail, not only the Albums tab
- album can be linked into Collections
- event-to-album integration exists
- HEIC thumbnails work
- use available screen width

### Events

v1.0 requirement:

- event grouping remains available
- event concept is documented in UI/operator docs
- merge target dropdown should prioritize or only show labeled events
- operator should be able to hide/exclude one-photo events
- event tiles should show full date/time range clearly
- events can be linked to Collections
- event-to-album integration exists
- HEIC thumbnails work
- use available screen width

### Timeline

v1.0 requirement:

- timeline must explain high/low/unknown date trust clearly
- timeline should focus on time navigation, not full photo detail
- clicking photo should allow navigation to Photo Detail if needed
- HEIC thumbnails work
- use available screen width

### Places

v1.0 requirement:

- user can edit/correct low-level address fields
- user labels remain supported
- HEIC thumbnails work
- use available screen width

### Duplicate Groups / Duplicate Suggestions

v1.0 requirement:

- image previews large enough for visual comparison
- image aspect ratio/cropping not misleading
- confirm/reject/split/demote/canonical workflow understandable
- HEIC thumbnails work
- use available screen width

Full duplicate methodology redesign is deferred beyond v1.0 unless a specific blocker is discovered.

---

## 11.3 Photo Review

Photo Review is the primary viewing and organizing area.

v1.0 requirements:

- HEIC thumbnails work
- use available screen width
- reasonable spacing between thumbnails
- universal search/filter across core facets
- hide/filter Live Photo motion companion MOV
- demoted/not-demoted toggle
- clicking image opens presentation mode
- Open Detail button goes to Photo Detail
- multi-select photos
- batch demotion
- add selected photos to existing album
- create album from selected photos
- add selected photos to existing collection
- create collection from selected photos
- assign selected photos to existing event where appropriate
- filter/search by:
  - person
  - time/date
  - album
  - collection
  - event label
  - place/location label
  - geolocation/geographic fields
  - EXIF/camera
  - source/provenance
  - media type
  - date trust
  - demotion/visibility

Date trust should be available, but it should not clutter the normal viewing workflow.

---

## 11.4 Photo Detail

Rename current `Photos` tab/concept to:

```text
Photo Detail
```

Purpose:

```text
low-level information and correction surface for each photo/asset
```

v1.0 requirements:

- metadata/provenance display
- event assignment tile
- album membership tile
- collection membership tile
- duplicate/near-duplicate tile
- face assignment/correction tile
- place/location tile
- ability to click face and assign/create person/cluster directly if practical
- event assignment should prioritize labeled events
- duplicate controls should support visual inspection, not just filenames
- HEIC thumbnails/previews work
- use available screen width

---

## 11.5 Admin

Admin is the operational control area.

v1.0 requirements:

- dedicated Ingestion area/tab
- more elegant local/cloud ingestion workflow
- Source Registry manageable but not overwhelming
- Source Intake visible and controlled
- iCloud Acquisition visible and controlled
- iCloud staging cleanup visible and controlled
- background jobs visible and controlled
- logs/reports accessible
- known sources displayed in bounded tile/table with scroll/pagination
- avoid giant unbounded lists
- operator can understand what to run next

v1.0 does not require fully unified one-click source profiles if minimum safe workflow is acceptable, but the UI should be much less clumsy than current development workflow.

---

## 12. Organization Model Requirements

## 12.1 Albums

Albums are user-curated photo sets.

v1.0 requirements:

- create album
- view album
- search/list albums
- add/remove photos
- add selected photos from Photo Review
- link album to Collection
- create album from Event

---

## 12.2 Events

Events are time/provenance-based groupings.

v1.0 requirements:

- view events
- label events
- merge events
- hide/filter one-photo events
- create album from event
- add event to collection
- search/filter by labeled event

---

## 12.3 Collections

Collections are required for v1.0.

Collections are high-level user-defined containers above albums and events.

A collection may include:

```text
individual photos
albums
events
```

Collection membership is many-to-many. A photo may belong to more than one collection.

Linked albums and linked events are **live references**.

If photos are later added to a linked album or event, those photos automatically appear in the collection.

Collection views must de-duplicate resolved photos so the same asset is displayed only once.

Collections are intended for:

```text
broad organization
provenance-based grouping
family/archive grouping
sharing/export preparation
large thematic grouping
```

Example:

```text
Collection: Dad's Photos
  - directly added photos
  - linked albums
  - linked events
```

v1.0 required collection operations:

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

---

## 12.4 Places

v1.0 requirements:

- display place labels
- display geocoded hierarchy
- user-defined place label
- user-editable low-level address fields
- search/filter by location label and geography

---

## 12.5 Tags / Metadata Facets

v1.0 should support metadata/provenance-driven search facets.

This does not necessarily require a heavy new free-form tagging system.

Minimum requirement:

```text
Expose metadata and provenance-derived facets for search/filtering and organization.
```

Candidate facets:

```text
source label
source folder / provenance path
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

Future expansion may convert these into richer user-visible tags.

---

## 13. Search / Discovery Requirements

v1.0 search should work across:

```text
person
face/person presence
time/date
date trust
album
collection
event label
place label
geographic location
EXIF/camera
source/provenance
media type
visibility/demotion
Live Photo / video
```

The goal is not natural-language AI search for v1.0.

The goal is reliable deterministic search/filtering across known system fields.

---

## 14. Safety and Non-Destructive Requirements

v1.0 must preserve the system’s core safety rules:

- no destructive overwrite of originals
- Vault remains immutable canonical storage
- DB/provenance explain asset origin
- Source Intake is ingestion authority
- cloud acquisition never writes directly to Vault/DB/provenance
- iCloud staging cleanup deletes only verified local staging copies
- no deletion from iCloud
- no deletion from Vault during cleanup
- no deletion of DB/provenance/source registry records during cleanup
- manual identity work is preserved
- demotion is reversible
- date trust overrides do not rewrite original metadata
- editing/cropping that changes pixels should create derivative asset, not overwrite original

---

## 15. Admin / Operations Requirements

v1.0 Admin must support:

```text
source management
source intake
iCloud acquisition
iCloud staging cleanup
background duplicate processing
display preview generation
Live Photo pairing
face processing
place geocoding
report/log review
system status
```

Admin should reduce operator confusion.

Required:

- bounded source tables/lists with scroll/pagination
- clear next-step guidance
- clear current/latest run status
- clear failed/deferred counts
- report paths or report viewer
- no hidden destructive operations
- no silent automation

---

## 16. Acceptance Criteria

v1.0 is acceptable when the user can:

### Deployment

- start the production app cleanly
- stop the production app cleanly
- distinguish production from development
- confirm NAS-backed storage/configuration
- confirm clean DB initialization

### Ingestion

- register/use production local source
- register/use production iCloud source
- run controlled local intake
- run controlled iCloud acquisition/intake
- avoid repeated cloud downloads or have a clear until-found/checkpoint solution
- clean verified staging files safely
- review run reports

### Display

- view HEIC assets consistently across all major UI areas
- review duplicates with adequate visual size
- browse Photo Review without Live Photo motion companion clutter

### Organization

- use Photo Review as main browsing surface
- use Photo Detail for low-level asset inspection
- create/use albums
- create/use collections
- link albums/events to collections
- edit place/address labels
- search/filter by people, time, place, event, album, collection, EXIF/provenance

### Safety

- confirm no originals are destructively modified
- confirm Vault files are preserved
- confirm staging cleanup does not affect Vault/iCloud/DB/provenance
- confirm demotion and visibility controls are reversible

---

## 17. v1.0 Required Milestone Tracks

The following tracks likely need to become concrete milestones.

### Track A — Production Deployment / NAS

- NAS storage layout
- Docker/runtime layout
- production config
- launcher/startup/shutdown
- backup/restore
- development vs production separation

### Track B — Clean DB / Clean Workspace

- production DB initialization
- schema setup
- production source setup
- workspace cleanup/release package
- test artifact separation

### Track C — Ingestion / iCloud Non-Repeat

- until-found/checkpoint design
- iCloud acquisition improvement
- local/cloud source workflow cleanup
- source profile minimum implementation or simplified equivalent
- staging cleanup integration

### Track D — Media Display

- HEIC thumbnails everywhere
- shared preview URL handling
- duplicate preview improvements
- Live Photo motion companion filter

### Track E — UI Layout / Workbench Cleanup

- use available screen width
- rename Review to Face Review
- rename Photos to Photo Detail
- improve Face Review operations
- fix Unassigned Faces workflow
- bounded scroll/pagination where needed

### Track F — Photo Review Main Workspace

- search/filter expansion
- multi-select
- demotion toggle
- add to album/collection/event
- presentation mode behavior
- thumbnail spacing/layout

### Track G — Organization Model

- Collections
- Event ↔ Album integration
- Place address editing
- metadata/provenance facets

### Track H — Admin Operations

- dedicated Ingestion area
- source tables bounded
- report/log review
- guided workflow clarity
- run history minimum support

---

## 18. Referenced Parking Lot Items

The following parking lot items are directly relevant to v1.0.

### Required or likely required for v1.0

```text
ICL-001 — iCloud Acquisition Until-Found / Checkpoint Strategy
SRC-003 — Unified Source Profile and Intake Workflow
OPS-001 — Unified Acquisition + Intake Workflow History
PX-016 — Undated Asset Discovery
PX-018 — Manual Date Trust Override / Physical Media Detection
UX-001 — Photo-Centric Unified Correction Workspace
UX-004 — Smart Filtering Expansion
CO-001 — Event ↔ Album Integration
CO-002 — Collections System Expansion
MV-002 — Live Photo Motion Companion Filtering
NAS-001 — NAS Deployment Readiness Plan
```

### Deferred beyond v1.0 unless later promoted

```text
ICL-002 — iCloud Credential / Session Manager
ICL-004 — Multi-iCloud Account Support
ICL-005 — Cloud-Native iCloud Provenance
ICL-007 — iCloud Album / Favorites / People Metadata Import
MV-001 — Live Photo Playback UI
MV-004 — Video Strategy / Playback System
AI-001 — Semantic Search Expansion
AI-002 — Landmark / Scene Intelligence
DUP-005 — Multi-Signal Duplicate Scoring
```

---

## 19. Open Product Questions

These are product-level questions for User + ChatGPT.

1. What is the minimum acceptable implementation of Unified Source Profile for v1.0?
2. Does v1.0 require full one-click intake, or is a cleaner guided multi-step intake acceptable?
3. How much of Collections must be implemented before v1.0?
4. Should Collections support only photos/albums/events initially, or also places/saved searches?
5. Does Photo Review need all listed batch operations before v1.0, or can some be staged?
6. What exact UI layout improvements are required versus preferred?
7. Is video playback definitely post-v1.0?
8. Is Live Photo playback definitely post-v1.0?
9. What is the minimum launcher/packaging acceptable for v1.0?

---

# Coder Technical Review Instructions

## Purpose

Coder should not rewrite product goals.

Coder should review this document against the current codebase and produce a technical gap analysis.

## Required Coder Output

Create:

```text
docs/prompts/Coder response 12.45.2.md
```

or equivalent project-approved location.

The response should include:

1. Requirements already satisfied
2. Requirements partially satisfied
3. Requirements not implemented
4. Likely implementation tracks
5. Technical risks
6. Missing technical details
7. Suggested milestone breakdown
8. Any requirements that conflict with current architecture
9. Any requirements that should be split into design-first milestones
10. Any requirements that may be much larger than they appear

## Coder Review Questions

Coder should explicitly answer the following.

### Deployment / NAS

1. What is currently required to start backend, frontend, Docker, and browser?
2. What would be needed for a clean production launcher?
3. Which paths/configs are currently hardcoded or development-specific?
4. What is needed to support NAS-backed Vault reliably?
5. What scripts/configs are production-required versus development/test only?

### Clean DB / Workspace

6. How can a clean production DB be initialized with the current schema?
7. Are there schema ensure/migration scripts that must run?
8. Which current workspace folders/files are runtime-required?
9. Which files are test/experimental/historical artifacts?
10. What cleanup/release package process is recommended?

### Ingestion

11. What is current status of local source ingestion for large folders?
12. What is current status of iCloud acquisition/intake?
13. What is needed to implement non-repeat iCloud acquisition / until-found behavior?
14. Can `icloudpd --until-found` satisfy this requirement?
15. What are the risks of fixed-window acquisition after staging cleanup?

### Media Display

16. Where are thumbnails/images rendered across the UI?
17. Which surfaces currently do not use display preview URLs correctly?
18. What is the best central fix for HEIC thumbnails everywhere?
19. What is required for larger duplicate review previews?
20. What is required to hide/filter Live Photo motion companions?

### UI / Workbench

21. What is needed to rename Review → Face Review?
22. What is needed to rename Photos → Photo Detail?
23. What is needed to improve width/layout usage globally?
24. What is needed to add pagination/next behavior for face clusters?
25. What is needed to fix Unassigned Faces create-cluster behavior?

### Photo Review

26. What search/filter capabilities already exist?
27. Which requested search/filter facets are missing?
28. What is required for multi-select actions?
29. What is required for presentation-mode-on-click?
30. What is required for batch add to album/collection/event?

### Organization Model

31. What is current Album/Event/Place model state?
32. What is needed for Event ↔ Album integration?
33. What is needed for Collections as first-class model?
34. What schema would Collections require?
35. What is needed to support live album/event references in Collections?
36. How should resolved collection assets be de-duplicated?

### Search / Metadata / Tags

37. What deterministic metadata/provenance facets already exist?
38. What can be searched today?
39. What would be needed for EXIF/provenance-based search facets?
40. Should “tags” be stored tags, derived facets, or both?

### Admin / Operations

41. What Admin cards already exist?
42. What would be needed for a dedicated Ingestion tab?
43. What source lists need bounded rows/scroll/pagination?
44. What run history/report visibility exists today?
45. What is needed for a unified acquisition/intake/cleanup history?

## Review Constraints

Coder should not implement anything during this review.

Coder should not scope-creep beyond technical gap analysis.

Coder should flag large items clearly.

Coder should identify quick wins separately from large architecture work.

---

## Definition of Done for 12.45.2

This requirements document is complete when:

- User agrees it reflects production v1.0 expectations
- Coder has reviewed it for technical accuracy and gaps
- requirements are classified into implementation tracks
- obvious post-v1.0 items are separated
- the next milestone path toward v1.0 can be created

# Product/Owner Answers to Coder Questions — Production v1.0

## 1. Launcher expectation

For v1.0, a scripted launcher with a desktop shortcut/icon is acceptable.

Minimum acceptable:
- starts Docker/services/backend/frontend in correct order
- performs readiness/health checks
- opens the app automatically
- suppresses or minimizes command windows where practical
- provides a clean stop/shutdown script
- has clear troubleshooting/log location

A fully packaged desktop shell or installer can be post-v1.0.

## 2. Collections v1 scope

Collections are required for v1.0.

Collections v1 should include:
- direct photo membership
- linked albums
- linked events
- live references for linked albums/events
- resolved collection view deduplicated by asset
- search/filter by collection
- Photo Review action to add selected photos to collection / create collection from selection

Places and saved searches can wait.

## 3. iCloud non-repeat strategy

Yes, “recent + checkpoint + known-threshold stop” is acceptable for v1.0 if `icloudpd --until-found` proves unreliable or insufficient.

But v1.0 must solve the operator problem:
- user should not need to keep increasing recent_count
- user should not repeatedly download the same recent files after staging cleanup without a clear catch-up strategy
- UI/reporting must explain whether acquisition is caught up, partial, or unknown

## 4. Cleanup/report history retention

For v1.0, retain source-level cleanup/acquisition/intake history in DB long enough to support audit and troubleshooting.

No aggressive pruning for v1.0.

A future policy can define report retention/pruning.

## 5. Batch organization actions location

Photo Review should be the primary place for batch organization actions in v1.0.

Album/Event/Collection pages may keep overlapping actions, but the main operator workflow should be:
- find/filter photos in Photo Review
- select multiple photos
- add/demote/organize from there

## 6. Production-scale validation target

We need a defined production trial before v1.0 sign-off.

Initial proposed validation:
- clean production-like DB
- NAS-backed or NAS-simulated storage path
- local source test with thousands of files if available
- iCloud source test with meaningful recent batch
- verify no duplicate Asset creation
- verify HEIC display across core surfaces
- verify staging cleanup
- verify reports and provenance
- verify app start/stop

Exact asset count can be finalized once we know available test data.

## 7. Albums vs Collections schema

Do not simply rebrand current tables blindly.

Because current “albums” are backed by `collections` / `collection_assets`, we need a design-first milestone.

Goal:
- preserve existing album behavior
- introduce true higher-level Collections cleanly
- avoid confusing semantic debt
- support live album/event references

Coder should propose safest model:
- migrate/rename existing tables, or
- add explicit new tables, or
- preserve current tables but clarify API/domain naming

No implementation until design is approved.

## 8. Dev/prod separation

For v1.0, one repo with profile-based runtime separation is acceptable if it is clean and safe.

Required:
- separate dev/prod env files
- separate dev/prod DB
- separate dev/prod storage roots
- clear launcher/profile selection
- no accidental production use of dev DB/storage
- clean release package or release manifest

A completely separate repo/workspace copy can be considered, but is not required if profile separation is robust.