# CANONICAL_PARKING_LOT v4 — Photo Organizer

## Purpose

Track deferred, future, and refinement work while maintaining:

- focus on active milestones
- architectural clarity
- system evolution visibility
- clean separation between active roadmap and deferred ideas

This document is:

- decision-oriented
- de-duplicated
- structured by system area
- limited to incomplete or intentionally deferred work

Completed items have been removed.

---

# 1. Near-Term Promotion Candidates

These are the strongest candidates for upcoming milestones after documentation refresh and punchlist review.

---

## ICL-001 — iCloud Acquisition Until-Found / Checkpoint Strategy

### Summary

Improve iCloud acquisition completeness beyond fixed `recent_count`.

### Current Issue

Current iCloud acquisition asks `icloudpd` for a fixed recent window, such as:

```text
recent_count = 25
```

If those recent files were already downloaded, staged, ingested, or later cleaned up, the system may re-download the same recent files and still not know whether additional unacquired files exist beyond the fixed window.

### Desired

Support acquisition logic such as:

```text
download/check recent items until N consecutive already-known items are found
```

or:

```text
maintain checkpoint by cloud asset ID / added date / provenance state
```

### Future Questions

- Can `icloudpd --until-found` solve this directly?
- Does `icloudpd` maintain enough local state for reliable incremental acquisition?
- Should Photo Organizer maintain its own acquisition checkpoint?
- Should “known” mean:
  - staged file exists
  - provenance exists
  - Vault asset exists
  - cloud asset ID seen
- How should Admin report:
  - recent window checked
  - likely caught up
  - incomplete / unknown completeness

### Importance

High.

This directly affects production iCloud use, especially after staging cleanup.

---

## SRC-001 — Source Registry Archive / Inactive Source Lifecycle

### Summary

Provide a safe way to retire old test sources without deleting provenance history.

### Current Issue

Development and testing created multiple source labels and iCloud staging folders.

Hard-deleting source registry rows could damage provenance explainability if rows are referenced by ingested assets.

### Desired

Allow source records to be marked:

```text
active
inactive
archived
test/deprecated
```

instead of deleted.

### Future Questions

- Should sources have `is_active`, `status`, or `archived_at`?
- Should archived sources remain visible in provenance views?
- Should inactive sources be hidden from acquisition/intake dropdowns?
- Should source deletion ever be allowed if provenance exists?
- How should old test iCloud sources be labeled?

### Importance

High.

Needed before source registry grows confusing.

---

## SRC-002 — Test Source Cleanup and De-Cluttering

### Summary

Clean up historical test source folders and source registry clutter created during iCloud development.

### Current Issue

Several test folders and labels exist under:

```text
storage/exports/icloud/
```

Many were created during direct iCloud / PyiCloud / icloudpd testing.

### Desired

- identify test-only source labels
- identify test-only staging folders
- determine which folders contain already-ingested files
- delete safe local staging files where appropriate
- mark test sources inactive/archived once source lifecycle support exists
- preserve provenance explainability

### Importance

High after source archive/inactive model exists.

---

## SRC-003 — Unified Source Profile and Intake Workflow

### Summary

The current ingestion workflow is architecturally safe but too clumsy for end-state production use.

Today, cloud ingestion still exposes multiple technical steps:

```text
1. Create/register source
2. Run iCloud Acquisition
3. Prepare Source Intake
4. Run Source Intake
5. Clean up staged files
```

This is acceptable for development but not ideal for daily use.

### Desired

Create a unified **Source Profile** model.

A source profile should represent both:

```text
where files come from
how files should be acquired or scanned
```

### Proposed Concepts

#### Source Type

```text
local_folder
external_drive
cloud
scan_batch
other
```

#### Cloud Type

```text
icloud
onedrive
google_photos
dropbox
other
```

#### Example iCloud Source Profile

```text
Source Label: chuck_icloud
Source Type: cloud
Cloud Type: icloud
Account Username: chhendersoniv@gmail.com
Acquisition Method: icloudpd
Root/Staging Path: storage/exports/icloud/chuck_icloud/
```

#### Example Local Folder Source Profile

```text
Source Label: chuck_pc
Source Type: local_folder
Root Path: D:\Photos\
```

### Desired End-State Workflow

Operator selects:

```text
Chuck iCloud
```

Then clicks:

```text
Run Intake
```

System performs the appropriate workflow:

#### For iCloud

```text
1. Run cloud acquisition via icloudpd.
2. Download into staging folder.
3. Run Source Intake.
4. Report acquisition + intake results together.
5. Offer or perform verified cleanup of successfully ingested staging files.
```

#### For Local Folder

```text
1. Scan local folder.
2. Run Source Intake.
3. Report results.
```

### Importance

High.

This is likely one of the most important usability redesigns before production daily use.

---

## OPS-001 — Unified Acquisition + Intake Workflow History

### Summary

Create a unified operational view showing acquisition runs and their related Source Intake runs.

### Current State

Acquisition and Source Intake are separate systems.

### Desired

Admin can see:

```text
iCloud acquisition run
→ staged files
→ Source Intake run
→ new/skipped/failed/deferred
→ cleanup result
→ post-intake jobs
```

### Future Questions

- Should Source Intake run records reference acquisition run IDs?
- Should Admin show a timeline of acquisition → intake → cleanup → enrichment?
- Should this become a generalized workflow dashboard for all source types?
- How should reports be linked?

### Importance

High for operational trust and troubleshooting.

---

## PX-016 — Undated Asset Discovery

### Summary

Add explicit discovery tools for assets missing reliable capture dates.

### Problem

There is no clean user-facing way to locate assets missing `captured_at` or having unknown/low date trust.

### Desired

- explicit “Undated” filter
- optional timeline bucket for undated / unknown-date assets
- Photo Review filter integration
- metadata completeness workflow

### Importance

High-impact usability improvement.

---

## PX-018 — Manual Date Trust Override / Physical Media Detection

### Summary

Allow the user to manually override capture-time trust, especially for photos of physical media.

### Problem

Some assets have valid digital EXIF timestamps but are actually photos of:

```text
slides
printed photos
documents
albums
negatives
```

The system may classify these as high trust because the camera timestamp is valid, but the timestamp reflects digitization date, not original capture date.

### Desired

Allow manual override from Photo Review:

```text
High → Low
High → Unknown
Low → High, if user confirms correctness
```

### Design Considerations

- preserve original EXIF metadata
- do not rewrite source files
- show both system trust and user override
- allow optional notes/reason later
- potential future AI suggestions only, never automatic changes

### Importance

High for timeline correctness.

---

# 2. iCloud / Cloud Acquisition Track

---

## ICL-002 — iCloud Credential / Session Manager

### Summary

Design a longer-term credential/session strategy for iCloud acquisition.

### Current State

Photo Organizer currently does not store:

```text
Apple ID password
2FA code
iCloud session cookies
iCloud auth tokens
```

Authentication is handled externally by `icloudpd`.

### Desired

Define whether Photo Organizer should ever manage or inspect iCloud authentication/session state.

### Future Questions

- Should Photo Organizer ever manage iCloud sessions directly?
- Can `icloudpd` session status be checked safely?
- Where are session files stored?
- Can sessions be separated per Apple ID?
- How should this work on NAS?
- Should Admin show authentication status?
- Should password/2FA entry in UI remain permanently out of scope?

### Importance

Medium-high before scheduled/NAS operation.

---

## ICL-003 — Admin iCloud Authentication Status

### Summary

Show whether `icloudpd` is authenticated and ready before running acquisition.

### Current State

Admin can launch iCloud Acquisition. If authentication is missing or expired, backend returns errors such as:

```text
AUTH_REQUIRED
SESSION_EXPIRED
```

### Desired

Admin displays:

```text
iCloud session ready
authentication required
session expired
last successful auth/run
```

### Future Questions

- Is there a safe `icloudpd` command to validate auth without downloading?
- Can session status be checked per username/account?
- Can auth status be refreshed without exposing secrets?

### Importance

Medium.

---

## ICL-004 — Multi-iCloud Account Support

### Summary

Define how multiple iCloud accounts should be represented and operated.

### Current Assumption

Normal production use:

```text
1 iCloud account/library = 1 stable iCloud source
```

Example:

```text
Source Label: chuck_icloudpd
Apple ID: chhendersoniv@gmail.com
Root Path: storage/exports/icloud/chuck_icloudpd/
```

### Desired

Support multiple iCloud accounts safely without mixing source folders or account sessions.

### Future Questions

- Can `icloudpd` support multiple accounts/sessions on the same machine cleanly?
- Does each Apple ID need separate session storage?
- Should each source require a bound account username?
- How does Admin prevent wrong-account/wrong-source use?

### Importance

Medium.

---

## ICL-005 — Cloud-Native iCloud Provenance

### Summary

Extend provenance to include iCloud-specific remote identity.

### Current State

Current provenance is based on Source Intake concepts:

```text
ingestion_source_id
source_relative_path
asset SHA
ingestion run
```

For iCloud acquisition, `source_relative_path` points to the local staged file downloaded by `icloudpd`.

### Desired

Capture additional cloud-native provenance where available:

```text
remote iCloud asset ID
Apple ID / account identity
icloudpd run ID
download timestamp
download method
original iCloud filename
Live Photo resource relationship
```

### Future Questions

- Does `icloudpd` expose stable cloud asset IDs in a usable report/log?
- Can remote IDs be mapped to downloaded filenames?
- Should remote IDs live on Provenance or a cloud provenance table?
- How should Live Photo still/MOV resources share cloud identity?
- How should edited/original versions be represented?

### Importance

Medium-high for future cloud synchronization.

---

## ICL-006 — iCloudPD Advanced Options

### Summary

Expose safe advanced `icloudpd` options.

### Candidate Options

```text
--until-found
--album
--folder-structure
--skip-videos / include videos
Live Photo related flags
size/original options
```

### Future Questions

- Which flags are safe?
- Which flags could mutate or delete cloud data?
- Which flags affect folder layout/provenance?
- Should advanced flags be per-source defaults?
- Should Admin expose them or keep them config-only?

### Importance

Medium.

---

## ICL-007 — iCloud Album / Favorites / People Metadata Import

### Summary

Import iCloud organizational metadata beyond files.

### Possible Metadata

```text
album membership
favorites
people labels
shared library info
edited/original variants
```

### Future Questions

- Does `icloudpd` expose album/favorite metadata?
- Does raw PyiCloud expose this better?
- Should cloud albums become local collections?
- How should changes over time be handled?

### Importance

Lower priority than acquisition correctness.

---

# 3. Source Registry / Ingestion / Operations

---

## IN-001 — Drop Zone Reprocessing Behavior

### Summary

Define how Drop Zone contents should be handled if a run is interrupted or files remain after partial processing.

### Desired

- safe retry behavior
- operator visibility into pending/rejected/deferred files
- no accidental duplicate staging
- deterministic cleanup rules

### Importance

Medium.

---

## IN-002 — Provenance vs Ingestion Run Separation

### Summary

Clarify and, if needed, refactor separation between durable provenance and ingestion run history.

### Concept

```text
provenance = durable source truth
ingestion run = historical processing event
```

### Desired

- provenance remains stable
- run records remain audit/history
- cleanup and reprocessing use the correct concept

### Importance

Medium.

---

## IN-003 — Large Source Progress / Completion Reporting

### Summary

Improve progress reporting for large local or cloud source folders.

### Problem

Large sources may contain thousands of files, and operators need clearer progress visibility.

### Desired

Show:

```text
total eligible files
already ingested
remaining
failed/deferred
last intake date
source completeness estimate
```

### Importance

Medium-high for large real-world imports.

---

## OPS-002 — Operational Report Browser / Viewer

### Summary

Provide Admin UI access to operational reports under `storage/logs/`.

### Current State

Reports are written for many jobs, but often require opening JSON files manually.

### Desired

Admin report browser for:

```text
Source Intake
iCloud Acquisition
iCloud Cleanup
Duplicate Processing
Display Preview Generation
Live Photo Pairing
Face Processing
Place Geocoding
```

### Importance

Medium.

---

## OPS-003 — Automatic Post-Intake Enrichment Chain

### Summary

Optionally run enrichment jobs after Source Intake.

### Current Workflow

Operator manually runs jobs such as:

```text
Display Preview Generation
Live Photo Pairing
Duplicate Processing
Face Processing
Place Geocoding
```

### Desired

After Source Intake, Admin may offer:

```text
Run recommended post-intake jobs
```

or eventually an automated chain.

### Future Questions

- Which jobs should run after every intake?
- Should jobs run only for newly inserted assets?
- Should large runs defer heavy jobs?
- Should this be per-source configurable?

### Importance

Medium.

---

```
## OPS-004 — Launcher Already-Running / Port Conflict Handling### SummaryImprove startup scripts so they detect when Photo Organizer is already running and provide a clear operator message instead of failing confusingly or appearing to encounter a ghost listener.### Current ObservationDuring 12.48.1 validation, port `8001` appeared blocked because the program was already running in another terminal. Closing all terminals cleared the port and the app ran normally.### DesiredStartup should detect occupied ports such as `8001` and `3000` and report:```textPhoto Organizer may already be running.Close existing terminal/session or run stop script before starting again.
```

Optionally offer a safe stop/retry path.

### Importance

Medium.

This improves launcher reliability and operator clarity before v1.0 production use.

```
## Practical operator rule for nowBefore starting the app:```text1. Check whether another terminal is already running backend/frontend.2. If unsure, run stop_photo_organizer.ps1.3. Then start again.
```

---

# 4. Photo Review / General UX

---

## UX-001 — Photo-Centric Unified Correction Workspace

### Summary

Create a single photo-centric correction workspace.

### Desired

From one photo/detail surface, allow correction of:

```text
faces
events
metadata
duplicates
location
date trust
visibility/demotion
```

### Importance

High after stabilization.

---

## UX-002 — Multi-Surface UI Architecture

### Summary

Clarify and separate UI modes.

### Proposed Surfaces

```text
Viewer
Workbench
Admin
```

### Desired

- simple viewer for normal browsing
- workbench for correction/curation
- Admin for operational controls

### Importance

Medium-high.

---

## UX-003 — Auto-Advance Workflow

### Summary

After certain actions, automatically advance to the next item.

### Examples

```text
confirm duplicate
reject duplicate
assign face
mark date trust
demote asset
```

### Importance

Medium.

---

## UX-004 — Smart Filtering Expansion

### Summary

Expand filtering capabilities across Photo Review and related views.

### Candidate Filters

```text
undated
low date trust
missing location
has location
has faces
unassigned faces
demoted
Live Photo motion companion
video
specific media formats
```

### Importance

Medium-high.

---

## UX-005 — Person-Based Navigation

### Summary

Improve navigation from people/person records into photo review and face correction workflows.

### Desired

- person detail pages
- all photos for person
- unconfirmed faces for person
- related clusters/faces

### Importance

Medium.

---

```
## UX-007 — Collection Polish### SummaryDefer Collection UI/UX polish until the broader Source Review / Album / Collection workflow has more real usage and testing.### PurposeImprove the usability, navigation, and visual clarity of Collections after the core functionality is stable.### Candidate Improvements- Reusable shared Collection picker component.- Richer Collection detail view.- Better display of:  - direct assets in Collection  - Albums linked to Collection  - asset count  - album count- Direct navigation/preselection after creating or adding to a Collection.- Improved Collection search/filter UX.- Better visual distinction between Collections and Albums.- Collection membership removal workflows.- Duplicate Collection name conflict UX:  - use existing  - rename  - cancel- Better result messaging after:  - create Collection  - add assets to Collection  - link Album to Collection- Layout polish for Collections tab and Source Review Collection actions.### Out of Scope- Collection hierarchy / nested Collections- Google Vision- semantic search- source file cleanup- duplicate/canonical logic- ingestion changes### PriorityDeferred. Collections are currently functional enough for continued workflow development. Revisit after more real-world testing.
```

---

# 5. Face / Identity System

---

## ID-001 — Create Cluster from Face

### Summary

Allow user to create a new cluster/person workflow from an individual unassigned face.

---

## ID-002 — Friendlier Cluster Selection

### Summary

Improve UI for selecting or moving faces between clusters.

---

## ID-003 — Representative Faces

### Summary

Allow users to choose representative face thumbnails for people or clusters.

---

## ID-004 — Cluster Confidence Signals

### Summary

Show confidence/quality indicators for clusters and suggested identities.

---

## FW-001 — Bulk Face Actions

### Summary

Support bulk operations on selected faces.

---

## FW-002 — Suggested Cluster Improvements

### Summary

Improve cluster suggestions and assignment flow.

---

## FW-003 — Face Comparison Tool

### Summary

Allow side-by-side comparison of faces/clusters/person candidates.

---

## FW-004 — Suggestion Dismissal System

### Summary

Allow user to dismiss incorrect face/person suggestions.

---

# ## FW-005 — Large Image Face Assignment Mode

### Summary

Add a larger-image face assignment mode for photos where thumbnail/card overlays are too small to assign faces comfortably.  

### Desired Behavior

User can open a larger image view from Photo Review or Photo Detail, reveal face boxes, click a face, assign the face cluster to an existing or new person, then continue assigning additional faces.  

### Important

Normal Presentation mode should remain clean by default. Face assignment overlays should be optional or available through a dedicated assignment mode.  

### Candidate Designs

- Photo Detail face assignment  
- Presentation mode with optional assignment overlay  
- Dedicated Face Assignment View  

### Priority

High after basic Photo Review thumbnail assignment works.

---

FACE-005 — Backfill Protected Manually Unassigned Faces

---

## FACE-006 — Face Review Visual Polish and Cluster Thumbnail Cards

### Summary

Defer additional Face Review visual polish now that the core face workflows are functional and generally usable.

### Purpose

Improve Face Review scannability when reviewing many clusters.

### Candidate Improvements

- Add representative thumbnails to Face Review cluster cards if current cards remain too text-heavy.
- Improve cluster card summaries:
  - person name / unassigned / ignored
  - face count
  - cluster ID as secondary detail
  - selected state
  - reviewed / ignored status
- Improve visual state for merge-selected workflow:
  - selected clusters
  - default merge target
  - source clusters
  - clear-selection control
- Improve empty/loading/error states:
  - no clusters found
  - no ignored clusters
  - no person/alias search results
  - missing thumbnail fallback
- Improve card spacing, density, and layout consistency.

### Out of Scope

- Face recognition changes
- Reclustering changes
- Assignment semantics
- Merge logic changes
- Person alias model changes
- Provenance mining
- Collections/albums/events model

### Priority

Deferred. Face Review is currently acceptable. Revisit after provenance mining and collection/album/event direction are clearer.

---

# 6. Location / Places

---

## PL-001 — Location Intelligence Master Track

### Summary

Expand location intelligence beyond reverse geocoding.

### Includes

```text
geographic hierarchy refinement
user-defined places
landmark recognition
image-based inference
learned place recognition
```

### Importance

Long-term intelligence track.

---

## PL-002 — Location Filtering

### Summary

Add richer filters by:

```text
country
state
city
place
user_label
missing location
```

---

## PL-003 — Place Normalization

### Summary

Resolve inconsistent or duplicate place names.

---

## PL-004 — Missing Location Handling

### Summary

Define and expose behavior for assets without GPS/location.

---

## PL-005 — Provenance vs Location Reconciliation

### Summary

Resolve cases where source/provenance location and GPS/geocoded location imply different places.

---

# 7. Collections / Albums / Events

---

## CO-001 — Event ↔ Album Integration

### Summary

Enable event-to-album workflows.

### Desired

```text
create album from event
add event to album
preserve event/album independence
```

---

## CO-002 — Collections System Expansion

### Summary

Define whether albums, collections, smart collections, and saved filters should become a unified collection system.

---

## EV-001 — Event Date Range Consistency

### Summary

Ensure date range recalculation is consistent across:

```text
merge
assign
remove
manual correction
incremental clustering
```

---

# 8. Media / Video / Live Photo

---

## MV-001 — Live Photo Playback UI

### Summary

Add Apple-like or simplified playback for paired Live Photos.

### Current State

The system can:

```text
preserve still and MOV
pair Live Photo components
show Live Photo and Live Photo Motion badges
```

Playback is not implemented.

### Future Options

```text
simple play button
hover playback
press-and-hold behavior
mute/unmute
open MOV companion
Apple-like Live Photo preview
```

---

## MV-002 — Live Photo Motion Companion Filtering

### Summary

Allow UI to hide or filter Live Photo motion companion MOV files.

### Current State

MOV companions are visible as assets and tagged:

```text
Live Photo Motion
```

### Desired

Photo browsing may optionally hide motion companions unless explicitly requested.

### Future Questions

- Should companion MOVs be hidden by default?
- Should there be a filter: “Show Live Photo Motion files”?
- How does this affect search/counts?
- How should detail pages link still ↔ motion?

---

## MV-003 — Video Canonicalization Recompute Parity

### Summary

Bring video support into any remaining canonical metadata recompute paths that are still image-only.

### Current State

Video metadata extraction and trust handling exists, but some recompute paths may still be image-oriented.

### Desired

- identify image-only recompute paths
- ensure video canonicalization can be recomputed safely
- preserve deterministic behavior

---

## MV-004 — Video Strategy / Playback System

### Summary

Define full video handling strategy.

### Includes

```text
video playback
video thumbnails
video metadata display
video duplicates
video search/filtering
```

---

## MV-005 — Legacy Camcorder Format Support

### Summary

Evaluate support for older video formats.

### Candidate Formats

```text
AVI
MTS / M2TS / AVCHD
MPG / MPEG
3GP
DV
older MOV variants
```

### Importance

Deferred until representative samples are available.

---

# 9. Duplicate System

---

## DUP-001 — Hamming Distance Threshold Tuning

### Summary

Tune pHash Hamming distance thresholds for near-duplicate detection.

### Problem

Current threshold may miss real duplicates, especially cross-format or edited/cropped versions.

### Desired

- adjustable thresholds
- better candidate filters
- resolution/time/format-aware tuning
- quality/false-positive analysis

---

## DUP-002 — Duplicate Group Review Improvements

### Summary

Improve duplicate review usability.

### Includes

```text
larger preview
presentation mode
side-by-side comparison
faster confirm/reject workflow
```

---

## DUP-003 — Cross-Format Detection Gap

### Summary

Improve detection across HEIC/JPG/PNG/TIFF/video derivatives where pHash or metadata differs.

---

## DUP-004 — Cross-Format Auto Grouping

### Summary

Explore safe auto-grouping for likely cross-format duplicates.

---

## DUP-005 — Multi-Signal Duplicate Scoring

### Summary

Combine multiple signals beyond pHash.

### Candidate Signals

```text
pHash distance
capture time
dimensions
file size
camera model
metadata similarity
visual quality
source relationship
```

### Status

Observe real-world behavior before implementation.

---

## DUP-006 — Canonical Asset Locking

### Summary

Support optional canonical “lock” behavior where user-selected canonical assets are preserved.

### Problem

Automated duplicate recomputation can change canonical selection as new relationships are discovered.

### Desired

- distinguish system-selected vs user-selected canonical
- prevent silent replacement of locked canonical assets
- allow manual override
- keep behavior reversible and non-destructive

### Importance

High for user trust once duplicate workflows mature.

---

# 10. Demotion / Visibility

---

## DS-001 — Non-Duplicate Demotion

### Summary

Allow reversible demotion of non-duplicate unwanted assets.

### Examples

```text
screenshots
documents
mistakes
errors
temporary images
```

### Requirements

- single and batch demotion
- reversible
- hidden from normal views
- separate from duplicate demotion

---

## DS-002 — Demoted Asset Management

### Summary

Provide UI to view and restore demoted assets.

---

# 11. NAS / Deployment / Scheduling

---

## NAS-001 — NAS Deployment Readiness Plan

### Summary

Prepare system for Synology/NAS-backed deployment.

### Includes

```text
Vault path migration
Docker deployment layout
PostgreSQL / Redis hosting
icloudpd helper environment
background job execution
backup/snapshot strategy
```

---

## NAS-002 — Scheduled iCloud Acquisition

### Summary

Run iCloud acquisition automatically on NAS or always-on server.

### Desired

```text
daily recent acquisition
weekly larger scan
notify if auth expired
```

### Dependencies

```text
credential/session strategy
until-found/checkpoint strategy
source profile model
operational run history
```

---

```
NAS-003 — Production Bootstrap / NAS Runtime Validation### SummaryValidate the 12.47 production bootstrap foundation against the real NAS-backed production path before any real production archive ingestion.### Current State12.47 created the production runtime scaffold, including:```textproduction profile/config templatesproduction DB separationproduction launcher scriptsproduction storage bootstrap scriptproduction release manifestoperator bootstrap guide
```

However, production startup has not yet been fully tested against real NAS paths.

### Desired

Before first real production ingestion:

- create real `backend/.env.production`
- configure actual NAS Vault path
- run production storage bootstrap
- verify production DB initialization
- verify production launcher startup/shutdown
- verify health checks
- confirm dev/prod separation
- confirm no fallback to development config/storage
- confirm no real media ingestion occurs during validation

### Importance

High before first production archive ingestion.

This is a validation and safety checkpoint, not a feature expansion.

---

# 12. Intelligence / AI Long-Term

---

## AI-001 — Semantic Search Expansion

### Summary

Improve natural-language and semantic search over assets.

### Candidate Inputs

```text
object tags
scene tags
locations
people
events
metadata
future embeddings
```

---

## AI-002 — Landmark / Scene Intelligence

### Summary

Identify landmarks, venues, or meaningful scenes beyond reverse geocoding.

---

## AI-003 — Physical Media Detection Suggestions

### Summary

Use visual signals to suggest likely scanned/photographed physical media.

### Important Constraint

Suggestions only. Do not automatically change date trust.

---

## AI-004 — EXIF / Metadata Inference Assistance

### Summary

Explore assisted inference for missing dates or metadata.

### Constraint

Non-deterministic inference must remain clearly labeled and user-approved.

---

```
## SEARCH-004 — Photo Review Search Hierarchy and Search Bar Improvements### SummaryRevisit Photo Review search/filter behavior to support smarter hierarchical filtering and less rigid search behavior.### ProblemPhoto Review search remains too structured and does not yet feel like a flexible search system. Current dropdown/search behavior may not respect hierarchy between filters.Example issue:```textIf a specific Collection is selected,available Albums should be limited to Albums within that Collection.
```

### Desired Direction

Improve Photo Review search so filters are context-aware and hierarchical where appropriate.

### Candidate Improvements

- Collection-aware Album filtering:
  - selecting a Collection limits Album options to Albums linked to that Collection
  - standalone Albums remain available when no Collection is selected
- Review how Collection, Album, Event, Date, Person, Place, Source, and media filters interact.
- Define search hierarchy rules:
  - Collection → Albums
  - Album → Assets
  - Source → Provenance paths
  - Year → Month/date range
  - Person → assets/faces associated with that person
  - Place → GPS/place/landmark candidates
- Reexamine the free-text search bar.
- Make search bar less rigid and less dependent on hard-coded parsing.
- Support better plain-text search across available indexed fields:
  - filename
  - album name
  - collection name
  - person name / alias
  - source/provenance path
  - event label
  - place/tag fields when available
- Avoid incorrect assumptions such as treating unknown text as camera search.
- Consider clearer chips for active filters.
- Consider dependent dropdown behavior:
  - dropdown options update based on active higher-level filters.
- Consider “All / within selected Collection / standalone” behavior for Albums.

### Design Questions

- Should Collection be the highest-level filter in Photo Review?
- Should Albums shown in the Album dropdown depend on Collection selection?
- Should Date filters apply globally or only within current Collection/Album selection?
- How should Source Review provenance filters interact with Collection/Album filters?
- Should search bar search all text fields by default?
- Should structured prefixes still exist, such as:
  - `person:Mary`
  - `album:Christmas`
  - `source:Dad Files`
- How should future Google Vision place/landmark clues and future semantic/object clues be included?

### Out of Scope

- Full semantic search
- Google Vision implementation
- LLaMA/local model integration
- major database search redesign unless separately scoped
- changing ingestion/source behavior

### Priority

Deferred but important before production-level usability. Revisit after Source Review / Collections / Albums core workflows stabilize.

---

EXT-001 — External Drive Identity Should Be Device-Based, Not Drive-Letter-Based

Principle:
External drive Source Profiles should represent the physical/logical device, not the temporary Windows drive letter.

Future model:
Source Profile = External 1
Run path = current mount path + canonical subfolder
Provenance = source-profile-based, with observed mount/path retained as evidence
