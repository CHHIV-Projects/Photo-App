**CANONICAL_PARKING_LOT.md — Photo Organizer**

**Purpose**

This document tracks non-critical but strategically important enhancements identified during development.

These items are intentionally deferred to:

- maintain focus
- avoid scope creep
- preserve milestone quality

They represent:

- future features
- system evolution ideas
- architectural improvements

This document also preserves:

- design thinking
- behavioral rules
- edge-case discoveries
- system constraints observed during implementation

**1. Identity & Clustering System (ID)**

**ID-001 — Create New Cluster from Face**

Allow creation of a new cluster directly from an unassigned face.

- user selects a face
- system creates a new cluster
- face becomes the seed
- cluster appears in review

**ID-002 — Friendlier Cluster Target Selection**

Replace raw cluster ID input with:

- searchable dropdown
- metadata (person name, face count)
- reduced user error

**ID-003 — Representative Faces**

Identify best faces using:

- clarity
- frontal angle
- lighting

Used for:

- thumbnails
- identity reference

**ID-004 — Cluster Confidence Signals**

Introduce indicators:

- mixed cluster detection
- confidence scoring
- highlight clusters needing review

**ID-005 — Cluster Merge & Identity Preservation**

Merging must preserve:

- identity consistency
- manual assignments
- user corrections

System must avoid:

- silent overwrites
- loss of human decisions

**2. Face Workflow System (FW)**

**FW-001 — Bulk Face Actions**

Support multi-select:

- move
- assign
- remove

**FW-002 — Suggested Cluster for Face**

Use embedding similarity:

- cosine similarity
- nearest neighbors

**FW-003 — Face Comparison Tool**

Side-by-side comparison to assist decisions.

**FW-004 — Suggestion Dismissal System**

Allow:

- dismiss suggestions
- reject candidates

Persist feedback to prevent re-suggestion.

**FW-005 — Human-Guided Workflow Principle**

AI assists but does not replace:

- manual assignment
- human validation
- correction workflows

**3. Media & Viewing System (MV)**

~~MV-001 — Full Image Viewer~~

~~Display:~~

- ~~full image~~
- ~~face boxes~~
- ~~assigned people~~

**MV-002 — Face Zoom / Preview**

Click face → enlarged preview.

**MV-003 — Thumbnail Normalization**

Ensure consistent:

- cropping
- padding
- sizing

**MV-004 — Thumbnail Persistence Limitation**

Current behavior:

- thumbnails sourced from review folders
- not moved or regenerated on cluster changes
- cluster reassignment may cause missing thumbnails

System must:

- gracefully fallback to placeholders

**MV-005 — Video Asset Handling Strategy**

The system currently treats the archive primarily as an image-first system, while video assets introduce different technical and UX requirements.

---

## Problem

Video assets differ materially from photos in areas such as:

* metadata extraction
* previews/thumbnails/poster frames
* playback
* rotation/orientation handling
* duplicate logic
* content understanding
* event participation
* review workflows

Without an explicit strategy, video behavior may remain inconsistent or underdeveloped compared to photos.

---

## Desired Behavior

Define a first-class video asset strategy covering:

* ingestion and metadata extraction
* poster frame / thumbnail generation
* playback support in UI
* event/timeline participation
* provenance handling
* duplicate and near-duplicate treatment
* future tagging/intelligence options

---

## Key Questions for Future Design

* what metadata should be normalized for videos?
* how should thumbnails/poster frames be generated and stored?
* should videos support full playback in the UI?
* how should duplicate detection work for videos?
* should face/object/scene systems apply to videos, and if so how?
* how should edited/derived video assets be handled later?

---

## Requirements

* preserve local-first architecture
* treat videos as true assets, not second-class attachments
* avoid forcing image-specific assumptions onto video workflows
* keep ingestion and provenance behavior auditable

---

## Constraints

* video processing may be significantly heavier than image processing
* content understanding for video may require future sampling or specialized pipelines
* UI support must balance usability with performance

---

## Notes

This should likely become a dedicated future milestone or milestone track rather than a small add-on.

The goal is to ensure video handling is intentionally designed rather than gradually accumulating ad hoc behavior.

**4. Photo Interaction & UX System (PX)**

~~PX-001 — Keyboard Shortcuts~~

~~Support navigation and actions.~~

**PX-002 — Auto-Advance Workflow**

Automatically move to next item after action.

**PX-003 — Smart Filtering**

Filter by:

- unassigned
- cluster size
- person
- activity

**PX-004 — Faces-Only Filtering**

Show only photos with faces.

**PX-005 — Face ↔ UI Highlighting**

Synchronize face boxes and UI entries.

**PX-006 — Jump to Cluster**

Click face → open cluster.

**PX-007 — Jump to Unassigned Workflow**

Click unassigned face → open workflow.

**PX-008 — Photo-Level Face Actions**

Allow:

- assign
- move
- remove

within photo view.

**PX-009 — Assign Person from Photo**

Direct assignment in photo view.

**PX-010 — Face Box Styling**

Color-coded:

- assigned
- clustered
- unassigned

**PX-011 — Face Hover Metadata**

Display:

- face id
- cluster id
- person

~~PX-012 — Photo Navigation Mode~~

~~Support:~~

- ~~next / previous~~
- ~~continuous review~~

**PX-013 — Person-Based Navigation**

Navigate across photos with same person.

**PX-014 — Photo-Centric Unified Correction Workspace**

Current system distributes correction workflows across multiple views:

* face correction (Review / Photos)
* event correction (Events tab, partial Photos support)
* metadata/canonicalization (Photo detail panel)
* future systems (tags, time, location) will also require correction workflows

**UX-015 — Multi-Surface UI Architecture (Viewer, Workbench, Admin Separation)**

Current system UI has evolved organically alongside feature development:

* Photos, Events, People, Places, Duplicate Groups, and search are all integrated into a single interface
* UI functions as a combined browsing, correction, and operational workbench
* Functional but not optimized for clarity, simplicity, or role separation

**PX-016 — Undated Asset Discovery (Missing captured_at Handling)**

Current system behavior:

* timeline navigation (12.6) excludes assets with null `captured_at`
* unified search (12.5) includes these assets only when no date filter is applied
* there is no explicit way to locate or isolate undated assets

---

## Problem

Assets missing canonical capture time are not easily discoverable.

User limitations:

* cannot explicitly search for “photos without dates”
* cannot access undated assets via timeline navigation
* difficult to audit or correct missing/incorrect metadata
* undated assets may become effectively hidden in large archives

---

## Desired Behavior

User should be able to:

* explicitly locate assets with missing `captured_at`
* isolate undated photos for review and correction
* treat undated assets as a first-class category in discovery

---

## Potential Approaches (Future)

### Timeline Integration

* add an **“Undated” bucket** in timeline navigation
* behaves alongside Year-level navigation

---

### Search Filter

* add explicit filter:
  * Date Status:
    * Has Date
    * Missing Date

---

### Combined Behavior

* allow undated filter to combine with:
  * filename search
  * camera filter
  * future metadata filters

---

## Requirements

* must use canonical metadata (`captured_at`)
* must not introduce inference or guessed dates
* must remain deterministic and auditable
* must not degrade performance

---

## Constraints

* must integrate cleanly with existing timeline/search architecture
* should not complicate core navigation for dated assets
* should remain simple and explicit for user understanding

---

## Notes

* complements Milestones 12.5 (search) and 12.6 (timeline)
* supports metadata quality improvement workflows
* useful precursor to future metadata correction tooling

---

## Status

Deferred — discovery/refinement feature for undated assets



---

## Problem

The current UI mixes multiple distinct usage modes:

* everyday photo browsing and discovery
* human-in-the-loop correction workflows
* system-level operations and configuration

This leads to:

* increasing UI complexity as features are added
* tension between simplicity and power
* reduced usability for non-technical or casual use
* risk of exposing advanced or destructive actions in normal workflows

---

## Desired Behavior

System should evolve into a **multi-surface UI architecture**, separating concerns into distinct modes:

### 1. Viewer (Library Experience)

Purpose:

* browse photos and collections
* search and discover content
* view albums, events, people, places

Characteristics:

* clean, minimal interface
* tile/grid-based browsing
* limited, safe interactions
* optimized for usability and visual clarity

---

### 2. Workbench (Review & Correction)

Purpose:

* fix system errors
* review duplicates, faces, events, metadata
* perform human-in-the-loop corrections

Characteristics:

* denser UI with diagnostic panels
* explicit controls and feedback
* metadata visibility and audit context
* workflow-oriented interactions

---

### 3. Admin (Operations & System Control)

Purpose:

* ingestion management
* processing and pipeline monitoring
* recompute/backfill operations
* configuration and system health

Characteristics:

* operational dashboards
* job and queue visibility
* system settings and controls
* separated from everyday user workflows

---

### (Optional Future) 4. Presentation / Sharing Surface

Purpose:

* slideshow or curated viewing
* potential sharing or external access

Characteristics:

* highly simplified UI
* no system control exposure
* focused on display and consumption

---

## Requirements

* clearly define boundaries between Viewer, Workbench, and Admin surfaces
* avoid mixing advanced controls into everyday browsing workflows
* maintain shared backend and core data model across all surfaces
* reuse components where appropriate without duplicating logic
* support progressive disclosure of functionality based on context

---

## Design Principles

* **Separation of concerns**: each surface optimized for its purpose
* **Safe defaults**: Viewer exposes only non-destructive actions
* **Power where needed**: Workbench retains full correction capability
* **Operational isolation**: Admin tools are not exposed in normal use
* **Auditability preserved**: deeper metadata/provenance accessible in Workbench/Admin, not forced in Viewer

---

## Constraints

* must not require full rewrite of existing UI
* should be implemented incrementally across multiple milestones
* must preserve existing workflows during transition
* must maintain consistency with current design system

---

## Notes

* current UI should be considered the evolving **Workbench surface**
* separation should occur only after core systems stabilize
* premature UI abstraction should be avoided until workflows are well understood

---

## Status

Deferred — foundational UX architecture decision for later-phase implementation

---

## Problem

Correction actions are fragmented across multiple UI surfaces.

User friction:

* must navigate between tabs to correct different aspects of the same photo
* interrupts natural browsing workflow
* increases cognitive load and reduces efficiency

---

## Desired Behavior

Establish the **Photo Detail / Photos tab as the primary correction workspace**.

From a single photo view, the user should be able to:

* assign/move/remove faces
* assign/reassign/remove event
* adjust metadata (future)
* manage tags/objects (future)
* adjust time (future)
* adjust location (future)

---

## Requirements

* consolidate correction actions into photo-level UI
* maintain clear, minimal, and safe interaction patterns
* preserve existing workflows while enabling unified access
* avoid accidental edits through clear affordances and validation

---

## UI Considerations

* grouped controls by category:
  
  * Identity (faces)
  * Event
  * Metadata
  * Tags
  * Location

* progressive disclosure (expand sections as needed)

* avoid clutter and maintain clean layout

---

## Constraints

* must not introduce large UI complexity prematurely
* must remain consistent with current design system
* must not break existing workflows
* should be implemented incrementally across multiple milestones

---

## Notes

* this is a UX/workflow evolution, not a backend requirement
* aligns with human-in-the-loop system philosophy
* should follow stabilization of core systems (events, metadata, tagging)

---

## Status

Deferred — UX/workflow consolidation milestone

**5. Events & Time System (EV)**

**EV-001 — Destructive Event Rebuild (Current Behavior)**

System currently:

- deletes all events
- deletes all asset→event relationships
- recreates events

Results:

- ID instability
- loss of manual edits
- shifting group membership

**EV-002 — Non-Destructive Event Model**

Future system must:

- preserve event identity
- support incremental updates
- maintain stable references

**EV-003 — Scan-Aware Event Grouping**

Use:

- folder structure
- provenance
- grouping context

**EV-004 — Hybrid Event Logic**

Use:

- digital → time-based
- scans → provenance-based

**EV-005 — Provenance-Based Event Creation**

Derive events from source folders.

**EV-006 — Multi-Level Provenance Hierarchy**

Support nested structures.

**EV-007 — Event Merge Suggestions**

Use:

- people overlap
- time similarity

**EV-008 — Event Confidence Weighting**

Weight:

- provenance
- timestamps
- people

**EV-009 — Timeline Trust Model**

Distinguish:

- no date (null)
- low-confidence date
- trusted date

Affects:

- grouping
- filtering
- display

**EV-010 — Multi-Type Time Model**

Store:

- exact
- estimated
- range
- source

**EV-011 — Scan Date Estimation**

Infer from:

- folder names
- context
- future ML

**EV-012 — Remove Asset from Event and Event Reassignment**

Current event administration supports:

* event label editing
* event merging

However, there is no asset-level event correction workflow for cases where an individual photo is grouped into the wrong event.

**EV-013 — Event Date Range Recalculation Inconsistency (Assign/Reassign)**

Current system behavior shows inconsistency in event date range updates depending on operation type.

Observed behavior:

* event merge correctly updates:
  
  * event date range (start/end)
  * display of date span

* asset-level assign/reassign:
  
  * updates membership and counts correctly
  * does NOT consistently update visible date range in UI

---

## Problem

Event summary fields (especially date range) are not being recalculated or reflected consistently across all mutation paths.

This leads to:

* incorrect or stale event date ranges after reassignment
* inconsistency between merge behavior and assign behavior
* reduced trust in event summaries

---

## Desired Behavior

All event mutation operations must produce consistent summary updates:

* merge
* asset removal
* asset assignment/reassignment

For each affected event:

* date range must reflect current asset membership
* display must update immediately after mutation
* backend and frontend must remain consistent

---

## Requirements

* ensure date range recalculation logic is shared across all mutation paths
* ensure UI refresh correctly reflects updated event summaries
* ensure no stale cached values remain after mutation
* maintain deterministic and predictable behavior

---

## Constraints

* must not trigger global event rebuild
* must remain lightweight and localized to affected events
* must not introduce performance regressions

---

## Notes

* this is a consistency/refinement issue, not a core architectural flaw
* likely involves aligning assign/reassign logic with existing merge recalculation logic
* should be addressed before expanding event features further

---

## Status

Deferred — refinement of event mutation consistency

---

## Problem

Some event issues are not solved by renaming or merging events.

Examples:

* one photo is incorrectly grouped into an event
* a photo belongs in a different existing event
* a photo should be removed from an event without immediate reassignment

Current system lacks a safe, explicit workflow for correcting event membership at the individual asset level.

---

## Desired Behavior

User should be able to:

* remove a photo from an event
* reassign a photo to another existing event
* optionally leave a photo temporarily unassigned

---

## Requirements

* preserve event integrity
* avoid orphaned or duplicate asset→event links
* update event counts correctly
* update event date ranges if necessary after asset removal
* keep behavior explicit and auditable

---

## UI Considerations

Possible surfaces:

* event detail view
* photo detail view
* event admin workflow

UI should remain simple and avoid accidental reassignment.

---

## Constraints

* must not silently trigger global event rebuilds
* must preserve current event editing logic
* should work with future non-destructive event model

---

## Notes

This is a natural extension of event administration, but it is broader than current label-edit and merge support.

It should be implemented after event identity and edit workflows are more mature.

**6. Provenance System (PR)**

**PR-001 — Full Source Path**

Display complete original path.

**PR-002 — Simplified Label**

Show immediate parent folder.

**PR-003 — Provenance Panel**

Display:

- origin
- path
- context

**PR-004 — Event Provenance Explanation**

Explain grouping logic.

**PR-005 — Provenance Breadcrumbs**

Hierarchical display.

**PR-006 — Provenance Search**

Filter by path/source.

**PR-007 — Provenance History**

Track:

- import batches
- changes

**PR-008 — Provenance as First-Class Signal**

Used for:

- event clustering
- metadata selection
- grouping

**7. Ingestion & Pipeline System (IN)**

**IN-001 — Drop Zone Modes**

Support:

- batch
- queue

**IN-002 — Cleanup Strategies**

Options:

- delete
- archive
- retain

**IN-003 — Processing Tracking**

Track per-file ingestion state.

**IN-004 — Partial Failure Handling**

Ensure safe recovery.

**IN-005 — Scope Separation**

Separate:

- ingestion
- global processing

**IN-006 — Incremental Processing**

Process only new assets.

**IN-007 — Non-Destructive Clustering**

Preserve cluster identity.

**IN-008 — Drop Zone Reprocessing Behavior**

Observed:

- entire drop zone processed each run
- uncleared zone → apparent full reprocessing

System must:

- define clear ingestion boundaries

**IN-009 — Background Near-Duplicate Lineage Processing**

Current duplicate-lineage processing for near duplicates is a major ingestion bottleneck.

Observed behavior:

* exact duplicate handling is fast and deterministic
* near-duplicate lineage analysis is much slower
* new assets may be compared against a growing archive population
* ingest speed degrades as total archive size increases

Future system should separate:

* **foreground ingest**
  
  * scan
  * filter
  * hash
  * exact dedup
  * vault copy
  * DB ingest
  * provenance handling

from

* **background near-duplicate lineage processing**
  
  * pHash comparison
  * near-duplicate grouping
  * canonical reevaluation within lineage groups

Desired behavior:

* files enter Vault / DB without waiting for full near-duplicate analysis
* near-duplicate lineage runs asynchronously or as a deferred worker
* system surfaces lineage status clearly
* later duplicate review/admin tools can act on completed results

Constraints:

* exact duplicate handling must remain immediate
* provenance must be preserved
* system must remain deterministic and auditable
* deferred lineage must not block normal ingestion workflows

Future options may include:

* local background worker
* NAS/desktop split processing
* optional cloud/offloaded compute if justified later

**IN-010 — Rejected / Unsupported Drop Zone Routing**

Current Drop Zone behavior can leave behind files that were not successfully processed, including:

* unsupported file types
* malformed files
* leftover sidecar / thumbnail artifacts
* files skipped for workflow reasons
* partial-failure cases

Leaving these files in Drop Zone creates confusion and pollutes future ingestion runs.

Future system should move such files out of Drop Zone into a dedicated holding area, for example:

* `quarantine/`
* `review/`
* `rejected/`

Desired behavior:

* successfully processed files leave Drop Zone
* unprocessed / unsupported / failed files are moved to a reviewable location
* original source context is preserved
* user can later inspect, delete, fix, or reprocess them

Recommended stored context:

* original source path
* reason for rejection / routing
* timestamp
* batch/run identifier if available

Constraints:

* must not silently delete questionable files
* must preserve auditability
* must keep Drop Zone clean and predictable
* should integrate with future cleanup/archive strategies

**IN-011 — Batch Staging Instead of Whole-Folder Staging**

Current ingestion behavior stages the entire selected source folder into Drop Zone first, then processes files in batches from an in-memory queue.

Observed limitations:

* Drop Zone may temporarily hold very large imports at once
* unnecessary disk churn for large source sets
* more confusing visibility into what is pending vs active
* leftover files can accumulate more easily
* large imports become operationally awkward

Future system should support **batch staging**, where only the next working batch is staged into Drop Zone at a time.

Desired behavior:

1. scan source / build candidate queue
2. stage only enough files for the next batch window
3. process that batch
4. clean/move leftovers appropriately
5. stage next batch
6. repeat until source exhausted or ingest limit reached

Benefits:

* Drop Zone reflects active work more accurately
* lower temporary storage usage
* cleaner lifecycle semantics
* better scaling for large imports

Constraints:

* must preserve current safety guarantees
* must not break provenance tracking
* must still support duplicate detection correctly
* must remain deterministic and rerunnable

Notes:

* whole-folder staging is acceptable for current MVP behavior
* batch staging is a future refinement for larger-scale ingestion workflows

**IN-012 — Separation of Durable Provenance and Ingestion Run History**

Current system behavior allows provenance records to be created per ingestion run, meaning the same asset and source path may be recorded multiple times across different runs.

While this supports audit history, it introduces conceptual ambiguity between:

* **what is true about the asset (provenance)**
* **what happened during ingestion (run history)**

---

## Problem

Provenance should represent a **durable fact**:

* where an asset came from
* source volume (e.g., External Drive 1)
* file hierarchy within that source

However, current design allows:

* repeated provenance rows for the same asset + source path across runs

* provenance acting as both:
  
  * source-of-truth
  * ingestion audit log

This can lead to:

* redundant provenance entries
* confusion in UI and data interpretation
* difficulty distinguishing source identity from ingestion activity

---

## Desired Model (Future)

### 1. Source (Stable)

A reusable, human-defined entity:

* Chuck PC
* External Drive 1
* iCloud Export

Expected behavior:

* small, stable list
* reused across ingestion runs
* eventually selectable via UI dropdown

---

### 2. Provenance (Durable Fact)

Represents:

* source (volume)
* relative file path within that source
* optional original absolute path

Key requirement:

* **one provenance record per unique (asset, source, relative path)**

Provenance should NOT multiply due to repeated ingestion runs.

---

### 3. Ingestion Run History (Operational Layer)

Represents:

* when ingestion occurred
* which files were observed during a run
* which sources were scanned

This should be tracked separately from provenance.

Possible implementation:

* ingestion_run table (already exists)
* ingestion_observation or similar (future)
* mapping of run → observed source paths

---

## Desired Behavior

* re-ingesting the same source path should:
  
  * NOT create new provenance rows
  * instead record observation under ingestion run history

* provenance remains stable and deduplicated

* ingestion runs provide audit trail without polluting provenance

---

## UI Implications (Future)

* source selection via dropdown (reuse existing sources)

* provenance display:
  
  * clean list of unique source paths

* ingestion history:
  
  * separate audit/log view

---

## Constraints

* must preserve full auditability
* must not lose ingestion history
* must not break existing duplicate/provenance logic
* must remain backward compatible or provide safe migration path

---

## Notes

* current implementation (11.1.2) is acceptable for MVP

* this refinement should be considered before:
  
  * advanced cleanup workflows
  * metadata canonicalization
  * source-based filtering UX

---

## Status

Deferred — architectural refinement for future milestone (likely Milestone 12+ or admin workflow phase)

**8. Metadata & Canonicalization System (MD)**

**MD-001 — Canonical Metadata Selection**

Select best metadata across duplicates.

**MD-002 — Trust-Based Selection**

Use:

- source type
- confidence
- provenance

**MD-003 — Per-Field Selection**

Combine best values across assets.

**MD-004 — Metadata Audit**

Track:

- source
- reasoning
- changes

**MD-005 — Re-Evaluation Capability**

Allow reprocessing on config change.

**MD-006 — EXIF Variability**

Handle differences between:

- local files
- cloud downloads
- HEIC sources

Prefer richest metadata source.

**9. Collections & Organization System (CO)**

**CO-001 — Smart Collections**

Rule-based grouping.

**CO-002 — Manual Collections**

User-defined.

**CO-003 — Hybrid Collections**

Rules + manual overrides.

**CO-004 — Albums Layer**

Subset grouping.

**CO-005 — Standalone Albums**

**CO-006 — Event-to-Album Integration**

The system currently supports:

* events as system-generated groupings
* albums as user-curated groupings

These two layers are valuable independently, but there is currently no workflow connecting them.

---

## Problem

Events often represent meaningful real-world groupings that the user may want to preserve as curated albums.

Examples:

* assign an existing event to an existing album
* create a new album from an event
* browse or search events from within the Albums workflow

Without integration, the user must manually rebuild event-based groupings inside albums.

---

## Desired Behavior

User should be able to:

* create a new album from an event

* add all assets from an event into an existing album

* search/select events while working in the Albums view

* preserve the difference between:
  
  * system-generated event grouping
  * user-curated album grouping

---

## Requirements

* event-to-album action must not alter the underlying event

* albums remain user-controlled and durable

* duplicate album membership rows must be prevented

* workflow should support both:
  
  * one-time copy from event to album
  * future expansion to smarter event/album relationships

---

## UI Considerations

Possible actions:

* “Create album from event”
* “Add event to album”
* event search/selector inside Albums page

UI should remain simple and avoid overcomplicating the Albums surface.

---

## Constraints

* must not make albums dependent on events
* must not silently sync album membership when event membership later changes
* should preserve current album model simplicity

---

## Notes

This is a high-value UX integration because events are often the most natural source for album creation.

It should be implemented as a workflow bridge, not a model coupling.

Independent curated sets.

**10. Intelligence & AI System (AI)**

**AI-001 — Person Suggestion**

Suggest identity via embeddings.

**AI-002 — Auto Assignment**

Optional automated assignment with safeguards.

**AI-003 — Semantic Tagging**

Use:

- scene detection
- object detection
- multimodal models

**AI-004 — Tag Fusion**

Combine outputs.

**AI-005 — Tag Consistency**

Stabilize results.

**11. System Behavior & Scaling (SB)**

**SB-001 — Processing Modes**

Define:

- incremental
- global

**SB-002 — Manual Override Protection**

Applies to:

- clusters
- events
- metadata
- canonical selection

System must:

- never overwrite user decisions silently
- require explicit reprocessing

**SB-003 — Scaling**

Support large archives.

**SB-004 — Advanced Ingestion**

Future expansion:

- full drive scans
- cloud ingestion

**SB-005 — Near-Duplicate Review Workflow**

Introduce:

- staging area
- human review

**SB-006 — Editable Metadata**

Allow editing:

- time
- tags
- attributes

**SB-007 — Rotated Face Overlay Support (Coordinate Transformation)**

Current system behavior suppresses face overlays when a photo is rotated (display_rotation_degrees ≠ 0°) to avoid misaligned bounding boxes.

While this is correct for MVP behavior, it results in loss of face visualization for rotated images.

---

## Problem

Face bounding boxes are stored in the original image coordinate space.

When a photo is rotated for display:

* image pixels are transformed
* stored face coordinates are not transformed
* overlays become misaligned if displayed without adjustment

Current solution:

* hide overlays when rotation is applied

This avoids incorrect display but removes useful functionality.

---

## Desired Behavior (Future)

Enable face overlays to display correctly on rotated images by transforming coordinates to match the display orientation.

Supported rotations:

* 90°
* 180°
* 270°

---

## Requirements

* transform stored face bounding boxes into rotated coordinate space
* maintain correct position, size, and orientation of overlays
* ensure overlays align with rendered image at all supported rotation values
* preserve interaction behavior (hover, click, selection)

---

## Technical Considerations

* coordinate transformation math for each rotation case
* interaction with scaled/responsive image rendering
* consistency with viewport-based sizing logic
* ensuring no regression in non-rotated (0°) behavior
* compatibility with existing face clustering and assignment systems

---

## UI Considerations

* overlays should appear seamlessly regardless of rotation
* no visual mismatch
* maintain current suppression fallback if transformation fails

---

## Constraints

* must not modify stored face coordinates in database
* transformation should occur at render/display layer only
* must not degrade performance in photo detail view
* should not introduce instability into face workflows

---

## Notes

* current suppression behavior (11.13) is correct for MVP
* this is a display-layer enhancement only
* should be implemented only after core UI and editing systems stabilize

---

## Status

Deferred — low-priority UX refinement

**12. Place & Location System (PL)**

**PL-001 — Geocoding Support**

Reverse geocoding:

- lat/lon → location
- caching
- provider flexibility

**PL-002 — Location Metadata Integration**

Use:

- EXIF GPS
- derived locations
- confidence

**PL-003 — Location Filtering**

Filter by:

- country
- state
- city

**PL-004 — Location as First-Class Dimension**

Location is equal to:

- Time
- People
- Events

Used for:

- filtering
- grouping
- navigation

**PL-005 — Location Grouping**

Group by:

- trips
- places
- recurring locations

**PL-006 — Place Normalization**

Handle naming inconsistencies.

**PL-007 — Provenance vs Location Reconciliation**

Resolve conflicts between:

- EXIF
- folder structure
- derived data

**PL-008 — Missing Location Handling**

Handle:

- no GPS
- partial data

Fallback:

- inference
- manual tagging

**13. Asset Quality & Canonicalization (AQ)**

**AQ-001 — Canonical Asset Selection**

Each duplicate group has one canonical asset.

Criteria:

- resolution
- clarity
- metadata completeness

**AQ-002 — Canonical Promotion / Demotion**

Allow:

- replacement by better asset
- demotion of previous canonical

**AQ-003 — Provenance Preservation**

Retain full lineage for all duplicates.

**AQ-004 — Near-Duplicate Handling**

Use perceptual hashing (pHash).

**AQ-005 — Hamming Distance Thresholds**

Detect similarity using thresholds (e.g. 10–15).

Filter by:

- resolution band
- time window
- file type

**Guiding Principles**

- AI assists, human decides
- provenance is a core signal
- identity must be preserved
- destructive actions must be explicit
- system must be explainable

**Usage**

- This is the canonical planning document
- Source for future milestones
- Do not directly mix into active work

\# Intake (Unstructured Additions)

New ideas go here before formal integration.

**AQ-006 — Cross-Format Near-Duplicate Detection Gap (HEIC ↔ JPEG)**

Current near-duplicate detection relies primarily on perceptual hashing (pHash) with a fixed Hamming distance threshold.

Observed limitation:

* format-converted versions of the same underlying image (e.g., HEIC → JPEG)
* may produce significantly different pHash values
* can exceed current threshold (e.g., distance ≈ 20 vs threshold 10)
* result: visually identical photos are not grouped into the same duplicate lineage
* commonly occurs with iCloud downloads vs original device files

**AQ-007 — Duplicate Group Audit & Visualization UI**

Current system supports:

* duplicate lineage grouping
* canonical asset selection
* manual merge control (12.3)

However, there is no dedicated UI for inspecting and validating duplicate groups as a whole.

---

## Problem

Duplicate groups are not easily auditable as complete sets.

User limitations:

* cannot search or navigate directly to a duplicate group
* cannot view all assets in a group in one place
* cannot visually confirm that grouped assets represent the same photo
* difficult to validate canonical selection quality

This leads to:

* reduced confidence in duplicate grouping
* slower manual validation workflows
* increased risk of incorrect canonical asset selection

---

## Desired Behavior

User should be able to:

* search for or navigate to a duplicate group
* view all assets in the group together
* visually inspect images (thumbnails/full view)
* clearly identify the canonical asset
* see key metadata per asset (captured_at, resolution, source)

---

## Requirements

* duplicate group listing / navigation mechanism
* group detail view showing:
  * all member assets
  * thumbnails or previews
  * canonical asset clearly marked
* basic metadata display per asset
* integration with existing duplicate-lineage system

---

## UI Considerations

* grid or gallery layout for group members
* clear canonical badge/indicator
* ability to open asset detail from group view
* optional future actions (merge, promote/demote canonical)

---

## Constraints

* must not introduce heavy performance cost when loading large groups
* must remain consistent with current UI patterns
* must not require major backend redesign

---

## Notes

* complements Milestone 12.3 (manual lineage control)
* focuses on **auditability and user confidence**
* likely precursor to more advanced duplicate workflows

---

## Status

Deferred — UX enhancement for duplicate lineage audit

**AQ-008 — Cross-Format Duplicate Auto-Grouping (HEIC ↔ JPEG and Similar Cases)**

Current duplicate-lineage system relies primarily on perceptual hashing (pHash) with a fixed Hamming distance threshold.

Observed limitation:

* same-photo variants across formats (e.g., HEIC ↔ JPEG)
* may produce significantly different pHash values
* exceed current threshold (e.g., distance ≈ 20 vs threshold 10)
* result: visually identical images are not grouped automatically

---

## Problem

The system correctly handles:

* exact duplicates (SHA256 match)
* near-duplicates within threshold

However, it fails to reliably detect:

* format-converted versions of the same underlying image
* images affected by compression, scaling, or encoding differences

This leads to:

* duplicate groups being incomplete
* multiple canonical assets for the same real-world photo
* increased manual correction burden (potentially thousands of cases)

---

## Desired Behavior

System should be able to:

* identify same-photo variants across formats
* group them into the same duplicate lineage automatically or semi-automatically
* reduce manual merge workload significantly

---

## Potential Approaches (Future)

### Multi-signal matching

Combine:

* pHash similarity
* capture time proximity
* filename similarity (e.g., IMG_#### patterns)
* resolution similarity
* provenance/source context
* file type relationships (HEIC ↔ JPEG conversions)

---

### Two-pass detection

* pass 1: strict threshold (current behavior)
* pass 2: relaxed threshold for strong candidate pairs

---

### Assisted review workflow

* generate candidate duplicate suggestions
* present in review queue
* allow user confirmation before grouping

---

### High-confidence auto-grouping (later stage)

* automatically group only when confidence is extremely high
* leave ambiguous cases for manual review

---

## Constraints

* must avoid false positives (incorrect grouping of different photos)
* must remain deterministic and explainable
* must not degrade performance significantly
* must preserve auditability of grouping decisions

---

## Notes

* this is a refinement of duplicate lineage system (11.7)
* complements manual control introduced in 12.3
* should be implemented after sufficient real-world examples are observed

---

## Status

Deferred — requires enhancement to duplicate detection and grouping logic

---

## Problem

The system correctly distinguishes:

* exact duplicates (same SHA256)
* near-duplicates (pHash similarity)

However, it does not reliably capture:

* cross-format conversions of the same original image
* especially when compression, scaling, or encoding differences alter perceptual hash significantly

This leads to:

* duplicate assets not grouped
* multiple canonical assets for the same real-world photo
* degraded canonical asset selection

---

## Desired Behavior

System should be able to:

* identify same-photo variants across formats (HEIC, JPEG, etc.)
* group them into a single duplicate lineage
* preserve canonical asset selection integrity

---

## Potential Approaches (Future)

* multi-signal duplicate detection:
  
  * pHash
  * dimensions similarity
  * capture time proximity
  * filename similarity
  * provenance context

* two-pass matching:
  
  * strict threshold (current behavior)
  * relaxed threshold for strong candidate pairs

* manual review workflow:
  
  * user confirmation for ambiguous cases

---

## Constraints

* must avoid false positives (grouping different photos)
* must preserve deterministic behavior
* must not degrade performance significantly
* must maintain auditability of grouping decisions

---

## Notes

* current behavior is correct under existing rules
* this is a coverage limitation, not a defect
* should be addressed as a refinement to duplicate lineage system (11.7)

---

## Status

Deferred — requires enhancement to near-duplicate detection logic

**AQ-009 — Duplicate Adjudication Policy & Review Workflow**

Current system now supports:

* automatic duplicate grouping
* canonical asset selection within duplicate groups
* manual duplicate-lineage merge control
* duplicate-group audit and visualization

However, the system does not yet define a clear human-reviewed policy for what should happen after a duplicate group is inspected.

---

## Problem

Not all near-duplicate groups represent “keep one, demote the rest” cases.

Examples:

* same underlying photo in different formats (HEIC ↔ JPEG) may be true duplicates
* slight edits / crops / exports may warrant one canonical asset with others retained
* visually similar photos taken moments apart may actually be distinct photos that should remain independently important
* current grouping may contain false positives that should be separated

This creates unresolved questions such as:

* when should one asset remain canonical and others be secondary?
* when should multiple assets remain effectively first-class photos?
* when should an asset be removed from a duplicate group?
* what should happen to non-canonical assets in UI and storage behavior?

---

## Desired Behavior

System should eventually support a human-guided adjudication workflow for duplicate groups.

Possible outcomes after review:

* confirm true duplicate relationship
* keep one canonical asset and retain other members as secondary
* reject grouping and separate assets
* define visibility behavior for non-canonical assets
* preserve archival truth without forcing destructive simplification

---

## Requirements

* define what “canonical” means for near-duplicate groups
* define when grouped assets are true duplicates vs distinct related photos
* support human review outcomes explicitly
* preserve provenance and auditability
* avoid destructive deletion or silent hiding of assets

---

## Key Questions for Future Design

* should near-duplicate groups always have exactly one canonical asset?
* should some groups allow multiple assets to remain first-class for browsing?
* should non-canonical assets be hidden from default views or remain normally visible?
* should the system support removing/splitting assets from a duplicate group?
* how should canonical choice interact with metadata, events, albums, and search?

---

## Constraints

* must preserve non-destructive archival design
* must remain explainable and human-guided
* must avoid oversimplifying distinct photos into one representative
* should build on existing duplicate audit and control workflows

---

## Notes

* this is a policy/workflow design problem, not just a UI issue
* duplicate-group audit (12.4) is the prerequisite foundation
* should be designed after reviewing more real duplicate groups and edge cases

---

## Status

Deferred — requires explicit duplicate adjudication policy and workflow design

\- [ ] item

\- [ ] item
