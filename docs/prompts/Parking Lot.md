**Future Enhancements Backlog — Photo Organizer**

**Purpose**

This document tracks **non-critical but valuable enhancements** identified during development.

These items are intentionally **deferred from current milestones** to:

-   maintain focus
-   avoid scope creep
-   preserve milestone quality

They should be reviewed periodically and promoted into future milestones when appropriate.

**🔵 Identity & Clustering Enhancements**

**1. Create New Cluster from Face**

**Priority: High (when doing heavy cleanup)**

**Problem**

-   Some faces do not belong in any existing cluster
-   Current workflow requires knowing an existing cluster ID

**Enhancement**

-   Allow user to create a new cluster directly from:
    -   Unassigned Faces view
    -   (optionally) Review view

**Expected Behavior**

-   user clicks Create New Cluster
-   new cluster is created with that face as seed
-   face is removed from unassigned list
-   cluster appears in Review
-   optionally auto-select new cluster

**2. Friendlier Cluster Target Selection**

**Priority: Medium**

**Problem**

-   moving faces requires numeric cluster ID
-   not intuitive for users

**Enhancement**

Replace raw ID input with:

-   searchable dropdown
-   or combined selector:
    -   cluster id
    -   assigned person name
    -   face count preview

**Future Possibility**

-   allow move by **person name**, not just cluster

**3. Representative Faces per Cluster / Person**

**Priority: Medium (later ML enhancement)**

**Problem**

-   not all faces are equally useful
-   clusters may contain duplicates or low-quality faces

**Enhancement**

-   identify “best” faces based on:
    -   clarity
    -   frontal angle
    -   size
    -   lighting
-   use for:
    -   thumbnails
    -   person preview
    -   identity reference

**4. Cluster Confidence / Quality Signals**

**Priority: Low (advanced)**

**Enhancement**

-   assign confidence score to clusters
-   flag:
    -   mixed clusters
    -   low-confidence assignments

**🟢 Face Workflow Enhancements**

**5. Bulk Actions for Faces**

**Priority: Medium**

**Enhancement**

-   select multiple faces
-   apply:
    -   move
    -   remove
    -   assign

**6. Suggested Cluster for Unassigned Face**

**Priority: Medium–High (smart UX)**

**Enhancement**

-   show “likely clusters” based on embedding similarity
-   allow quick assignment

**7. Face Comparison Tool**

**Priority: Low**

**Enhancement**

-   compare two faces side-by-side
-   assist manual decisions

**🟡 Media & Image Enhancements**

**8. Full Image Viewer**

**Priority: High (after current phase)**

**Enhancement**

-   click photo → open full image
-   overlay detected faces
-   show assigned people

**9. Larger Face Preview / Zoom**

**Priority: Medium**

**Enhancement**

-   click face tile → larger view

**10. Thumbnail Quality Improvements**

**Priority: Low**

**Enhancement**

-   consistent crop padding
-   resizing/normalization

**🟠 Workflow & Navigation Enhancements**

**11. Keyboard Shortcuts**

**Priority: Medium**

**Enhancement**

-   next/previous cluster
-   assign person
-   move/remove face

**12. Auto-Advance Workflow Mode**

**Priority: Medium–High**

**Enhancement**

-   after action (assign/move), auto-advance to next cluster
-   faster review loop

**13. Smart Filtering**

**Priority: High (later phase)**

**Filters like:**

-   unassigned clusters
-   low-face clusters
-   recently modified
-   ignored clusters
-   specific person

**🔴 Data & System Enhancements**

**14. Unignore Workflow**

**Priority: Medium**

**Enhancement**

-   view ignored clusters
-   restore them

**15. Background Crop Generation**

**Priority: Medium**

**Enhancement**

-   automatically generate missing crops
-   replace manual script over time

**16. Incremental Clustering Improvements**

**Priority: Medium–High**

**Enhancement**

-   better handling of new ingestion
-   avoid degrading existing clusters

**🟣 Photo-Level Features (Future Phase)**

**17. Full Photo Review (Major Milestone)**

**Priority: High**

**Enhancement**

-   show full image
-   overlay faces
-   show assigned people

**18. Events / Timeline View**

**Priority: High**

**Enhancement**

-   group photos by time
-   browse chronologically

**19. Places / Location View**

**Priority: High**

**Enhancement**

-   use EXIF GPS
-   group by location

**20. Person-Centric Photo View**

**Priority: High**

**Enhancement**

-   open person → see all photos they appear in

**🧠 Notes**

-   Clusters are **intermediate AI groupings**, not final truth
-   People are the **primary identity objects**
-   Faces are **atomic data units**
-   Photos are the **final user-facing layer**

**🧭 Usage**

-   Review this list when planning new milestones
-   Promote items into structured milestones when needed
-   Do NOT mix these into active milestones unless explicitly promoted

**✔️ Current Status**

Core system now supports:

-   ingestion
-   face detection + embeddings
-   clustering
-   correction workflow
-   identity assignment
-   thumbnails
-   unassigned face handling
-   navigation improvements

Next major phase:

👉 **Full Photo Review → Events → Places**

# Addendum — Photo Review Enhancements (Post Milestone 10.10)

## Purpose

This section captures **photo-level usability improvements** identified after implementing Full Photo Review (Milestone 10.10).

These are **not required for initial functionality**, but will significantly improve usability and workflow efficiency.

---

# 🔵 Photo View Filtering

## 21. Filter Photos to Only Those With Faces

**Priority: Medium**

### Problem

* Photos with zero detected faces appear in the Photos view
* These are not useful for identity/face review workflows
* They add noise and reduce efficiency

### Enhancement

* Default behavior:

  * show only photos where `face_count > 0`

### Future Option

* allow toggle:

  * “Show all photos”
  * “Show only photos with faces”

---

# 🟢 Photo Interaction Improvements

## 22. Face Box ↔ Face List Highlighting

**Priority: Medium–High**

### Problem

* No visual linkage between:

  * face boxes on image
  * face entries in the list

### Enhancement

* clicking a face row highlights corresponding box
* clicking a face box highlights corresponding row

### Benefit

* easier identification of faces in crowded photos
* reduces confusion during review

---

## 23. Click Face → Jump to Cluster Review

**Priority: High**

### Problem

* user sees a face in photo but cannot easily jump to cluster context

### Enhancement

* clicking a face (box or row) provides:

  * “Open in Review”
* switches to Review tab
* selects corresponding cluster
* loads cluster detail

### Benefit

* tight integration between photo view and cluster workflow
* faster correction loop

---

## 24. Click Face → Jump to Unassigned Workflow

**Priority: Medium**

### Problem

* unassigned faces in photo require manual navigation to Unassigned Faces tab

### Enhancement

* clicking unassigned face provides:

  * “Open in Unassigned Faces”

### Benefit

* faster cleanup of unresolved identities

---

# 🟡 Photo Context Editing (Future Phase)

## 25. Basic Face Actions in Photo View

**Priority: Medium (later)**

### Enhancement

Allow limited editing directly from photo:

* assign to cluster
* remove from cluster
* move to cluster

### Note

* must reuse existing backend endpoints
* should not duplicate logic

---

## 26. Assign Person from Photo View

**Priority: Medium (later)**

### Enhancement

* assign person directly from face in photo

### Benefit

* reduces need to switch to cluster view for simple assignments

---

# 🟠 Visual Improvements

## 27. Improved Face Box Styling

**Priority: Low**

### Enhancement

* color-code boxes:

  * green → assigned person
  * yellow → cluster but no person
  * red → unassigned

### Benefit

* quick visual scanning of photo identity state

---

## 28. Hover Details for Face Boxes

**Priority: Low**

### Enhancement

* hover over face box shows:

  * face id
  * cluster id
  * person name

---

# 🔴 Navigation Enhancements

## 29. Auto-Advance Through Photos

**Priority: Medium**

### Enhancement

* next/previous photo controls
* optional “review mode”:

  * auto-advance after action

---

## 30. Jump Between Photos with Same Person

**Priority: Medium–High**

### Enhancement

* from a face/person:

  * jump to next photo containing that person

---

# 🧠 Notes

* Photo view is the **final integration layer** of the system
* Clusters and faces feed into this experience
* Improvements here have **high user impact**

---

# ✔️ Position in Roadmap

These enhancements should be considered **after**:

1. Full Photo Review (10.10) ✅
2. Events / timeline UI
3. Places / location UI

Then:

* return to photo UX improvements
* refine interaction and speed

---

# 🧭 Guiding Principle

Keep photo view:

* simple
* fast
* contextual

Avoid turning it into a complex editing surface too early.

---
# Addendum — Scan-Aware Event Grouping & Provenance Utilization

## Purpose

Enhance event grouping and photo organization by leveraging **scan provenance metadata**, especially original folder/album structure, which is often more reliable than timestamps for scanned images.

This applies specifically to:

* scanned photos
* digitized albums
* legacy archives with weak or missing EXIF time data

---

# 🔵 Scan Event Challenges

## Problem

Scanned images often have unreliable or misleading timestamps:

* scan/import time replaces original capture time
* EXIF metadata may be missing or incorrect
* multiple decades of photos may appear grouped into a single “event”

This breaks time-based event clustering.

---

# 🟢 Provenance as a Primary Signal

## 31. Use Source Folder as Event Anchor

**Priority: High**

### Insight

Original folder structure often represents:

* physical albums
* labeled batches
* meaningful human groupings

Example:

```text
Scans/
  1985 Birthday Party/
  Hawaii Trip 1992/
  Christmas 2001/
```

These are effectively **pre-labeled events**.

---

### Enhancement

For scanned images:

* treat source folder as a **strong event grouping signal**
* optionally override time-based clustering

### Behavior

* all images from same source folder:
  → default to same event
* timestamps become secondary signal

---

## 32. Provenance-Based Event Creation

**Priority: High**

### Enhancement

During ingestion or post-processing:

* create events directly from folder groupings
* assign all assets in folder to same event

Optional:

* derive event name from folder name

---

## 33. Hybrid Event Logic (Scans vs Digital)

**Priority: High**

### Enhancement

Use different strategies depending on asset type:

### For digital photos:

* primary: timestamp clustering
* secondary: location / people overlap

### For scans:

* primary: provenance (folder/batch)
* secondary: optional approximate date
* ignore strict time-gap rules

---

# 🟡 Advanced Provenance Enhancements

## 34. Multi-Level Provenance Hierarchy

**Priority: Medium**

### Enhancement

Use nested folder structure:

```text
Scans/
  Family Albums/
    1980s/
      Vacation Italy/
```

To derive:

* top-level grouping (collection)
* mid-level grouping (era)
* event-level grouping (album/event)

---

## 35. Combine Provenance with People Overlap

**Priority: Medium**

### Enhancement

If two scan folders:

* share many of the same people
* and have similar time estimates

→ suggest merging into a single event or trip

---

## 36. Provenance Confidence Weighting

**Priority: Medium**

### Enhancement

Assign confidence to grouping signals:

* folder grouping → high confidence
* timestamp → low confidence (for scans)
* people overlap → medium confidence

Use weighting to influence future event logic.

---

# 🟠 User Interaction Enhancements

## 37. Display Provenance in UI

**Priority: Medium**

### Enhancement

Show source folder in:

* photo detail
* event view
* metadata panel

Example:

```text
Source: "Hawaii Trip 1992"
```

---

## 38. Manual Event Override for Scans

**Priority: Medium**

### Enhancement

Allow user to:

* merge scan-based events
* split incorrectly grouped folders
* rename events

---

# 🔴 Data & System Enhancements

## 39. Store Provenance Metadata Explicitly

**Priority: Medium**

### Enhancement

Ensure database tracks:

* original folder path
* import batch id
* scan source

This enables:

* reproducibility
* smarter grouping later

---

## 40. Scan-Specific Event Pipeline

**Priority: Low (future)**

### Enhancement

Separate pipeline for scans:

* detect scan vs digital
* apply different clustering logic
* optionally skip time-based clustering entirely

---

# 🧠 Notes

* Provenance is often **more accurate than timestamps for scans**
* This is a **major advantage** in your dataset
* Systems without provenance must rely on weaker heuristics

---

# ✔️ Strategic Value

Leveraging provenance allows:

* near-perfect event grouping for scanned archives
* less manual correction
* more human-aligned organization

---

# 🧭 Position in Roadmap

These enhancements should be implemented after:

1. Events / Timeline UI (10.11) ✅
2. Places / Location View (10.12)
3. Basic event refinement tools

Then:

👉 Introduce scan-aware event logic

---

# 🔑 Guiding Principle

For scans:

> Trust human-created structure (folders/albums) over inferred signals (timestamps)

---
# Addendum — Drop Zone Cleanup & Post-Ingest File Management

## Purpose

Define future enhancements for handling files in the **drop zone after ingestion**, including safe cleanup, archival strategies, and automation options.

This addresses current behavior where files remain in the drop zone after successful ingestion.

---

# 🔵 Current Behavior (Baseline)

## Status

* Files are ingested from drop zone
* Files are processed and stored in vault
* Files remain in drop zone after processing

## Implication

* Safe for development and debugging
* Requires manual cleanup during testing
* Can lead to clutter over time

---

# 🟢 Short-Term Practice (Current Phase)

## Manual Cleanup

**Recommended current workflow:**

* After successful ingestion:

  * verify assets appear in UI (Photos, Events, etc.)
  * confirm no ingestion errors
* manually delete files from drop zone

This is acceptable and expected for Milestone 11 phase.

---

# 🟡 Future Enhancements

## 41. Optional Drop Zone Cleanup Flag

**Priority: High**

### Enhancement

Add an optional flag to orchestration script:

```bash
--cleanup-dropzone
```

### Behavior

* after successful ingestion + vault storage:

  * delete original files from drop zone
* only execute if:

  * pipeline completes successfully

### Safety Requirement

* do NOT delete files if any critical stage fails

---

## 42. Move to Processed / Archive Folder

**Priority: High**

### Enhancement

Instead of deleting, move files to:

```text
dropzone/processed/
```

or

```text
dropzone/archive/
```

### Benefits

* retains original files for backup
* enables audit and reprocessing
* safer than deletion

---

## 43. Idempotent Drop Zone Handling

**Priority: Medium**

### Enhancement

Allow drop zone to persist without manual cleanup by:

* tracking processed files via hash
* skipping already-ingested files

### Behavior

* files can remain in drop zone
* system ignores duplicates automatically

---

## 44. Ingestion State Tracking

**Priority: Medium**

### Enhancement

Track ingestion status per file:

* pending
* processed
* failed

### Benefit

* enables smarter cleanup
* supports retry logic

---

## 45. Partial Failure Handling

**Priority: Medium**

### Enhancement

If pipeline fails mid-run:

* only keep unprocessed or failed files
* optionally move successful ones to processed/

---

# 🟠 Advanced Enhancements

## 46. Configurable Cleanup Policy

**Priority: Low**

### Enhancement

Allow configurable modes:

* keep (default)
* delete
* archive

Example:

```bash
--cleanup-mode delete
--cleanup-mode archive
```

---

## 47. Scheduled Cleanup

**Priority: Low**

### Enhancement

Periodic cleanup job:

* remove files older than X days
* archive old drop zone contents

---

# 🔴 Risks & Safety Considerations

* accidental deletion of unprocessed files
* partial pipeline failures leaving inconsistent state
* user confusion about file lifecycle

---

# 🧠 Guiding Principle

> Never delete source files unless ingestion and storage are confirmed successful.

---

# ✔️ Strategic Value

Improving drop zone handling will:

* reduce manual cleanup effort
* support large-scale ingestion
* make pipeline safer and more repeatable
* enable production-like workflows

---

# 🧭 Position in Roadmap

These enhancements should be implemented after:

* Milestone 11.1 (Pipeline orchestration) ✅
* Initial batch testing workflows

Then:

👉 Introduce controlled cleanup and archival behavior

---

# 🔑 Summary

Current state:

* manual cleanup is correct and expected

Future direction:

* controlled, optional, and safe automation of drop zone cleanup

---
# Addendum — Incremental Face Processing vs Global Rebuild

## Purpose

Define the current behavior and future improvements for **face detection and clustering during ingestion**, specifically addressing the distinction between:

* safe (non-destructive) ingest
* global (destructive) rebuild

This ensures clarity in operator workflows and prevents accidental loss of reviewed identity data.

---

# 🔵 Current System Behavior

## 48. Face Pipeline is Globally Destructive

**Priority: Critical Understanding**

### Current Implementation

* Face detection:

  * replaces or rebuilds face records globally
* Face clustering:

  * clears all cluster assignments
  * deletes and recreates clusters
* Person assignments:

  * tied to clusters, and therefore lost when clusters are rebuilt

### Implication

Running face detection/clustering in the current pipeline:

* **affects the entire dataset**
* is **not limited to newly ingested images**
* can reset previously reviewed identity work

---

# 🟢 Current Operator Modes

## 49. Safe Ingest Mode (Default)

**Priority: High**

### Behavior

* runs ingestion pipeline
* processes metadata, events, etc.
* **skips face detection and clustering**

### Result

* existing clusters and person assignments are preserved
* new images:

  * are ingested
  * but **do not receive face detection or clustering**

---

## 50. Global Rebuild Mode (Destructive)

**Priority: High**

### Behavior

* runs face detection and clustering across entire dataset

### Result

* new images:

  * get face detection and clustering
* existing images:

  * are reprocessed
  * cluster structure is rebuilt
  * person assignments may be lost or reset

---

## 51. Tradeoff in Current Design

| Mode           | Preserves Existing Work | Processes New Faces |
| -------------- | ----------------------- | ------------------- |
| Safe Ingest    | Yes                     | No                  |
| Global Rebuild | No                      | Yes                 |

This is a temporary limitation of the current architecture.

---

# 🟡 Desired Future Behavior

## 52. Incremental Face Processing

**Priority: High**

### Goal

Enable processing of **newly ingested images only**, without affecting existing reviewed data.

### Desired Behavior

* run face detection only on new assets
* generate embeddings only for new faces
* assign new faces into existing clusters
* preserve:

  * cluster IDs
  * person assignments
  * reviewed corrections

---

## 53. Non-Destructive Clustering Updates

**Priority: High**

### Goal

Allow clustering to evolve without resetting prior work.

### Possible Approaches

* incremental clustering:

  * assign new faces into existing clusters
* cluster merge/split heuristics:

  * applied selectively
* preserve cluster IDs where possible

---

## 54. Separation of Concerns

Future pipeline should distinguish:

* ingest pipeline (safe, repeatable)
* face processing pipeline (incremental)
* full rebuild pipeline (explicit and rare)

---

# 🟠 Operator Workflow (Future Target)

## Ideal Workflow

1. import new batch
2. run pipeline
3. new images:

   * automatically get faces detected
   * get clustered into existing structure
4. existing reviewed work remains intact

---

## Rebuild Workflow (Advanced)

* explicit action
* used for:

  * model upgrades
  * clustering improvements
  * major corrections

---

# 🔴 Safety Considerations

* accidental global rebuild can destroy review work
* operator must clearly understand difference between modes
* destructive actions must require confirmation

---

# 🧠 Guiding Principle

> Normal ingestion should be safe and preserve user-reviewed identity data.

> Destructive rebuilds should be explicit, rare, and clearly communicated.

---

# ✔️ Strategic Value

Implementing incremental face processing will:

* remove need for tradeoff between safety and completeness
* enable continuous ingestion workflows
* preserve user effort in identity labeling
* improve system scalability and usability

---

# 🧭 Position in Roadmap

This enhancement should be addressed after:

* Milestone 11.2 (Search & Filtering)
* additional usability improvements

Then:

👉 Introduce incremental face processing and non-destructive clustering

---

# 🔑 Summary

Current state:

* safe ingest OR full rebuild (mutually exclusive tradeoff)

Future goal:

* safe ingest WITH incremental face processing

---
# Addendum — Collections and Albums (User-Defined Grouping Layer)

## Purpose

Introduce a future **user-defined grouping layer** that allows flexible organization of photos beyond system-generated structures.

This layer will enable:

* personal organization
* storytelling
* curation
* grouping based on any combination of available data

It is especially important because many source systems (e.g., iPhone albums) do not preserve album structure on export.

---

# 🧠 Concept Overview

## Collections vs Albums

### Collections (Primary Layer)

Collections are:

* broad, durable groupings
* often based on rules or themes
* cross-cutting across people, time, and location

Examples:

* Dad’s Photos
* Henderson Family
* Childhood
* All Scans
* Photos to Review

Collections can be:

* rule-based (smart)
* manually curated
* or a hybrid

---

### Albums (Secondary Layer)

Albums are:

* more specific or curated groupings
* often subsets of collections or standalone

Examples:

* Henderson Family → Christmases
* Dad’s Photos → Fishing Trips
* Childhood → School Pictures

Albums are typically:

* manually curated
* presentation-focused
* smaller and more intentional

---

# 🔵 Core Capabilities

## 55. Smart Collections (Rule-Based)

**Priority: High**

### Behavior

User defines rules such as:

* person = Audrey
* date range = 1985–1995
* place = San Diego
* is_scan = true
* filename contains "IMG_"

System dynamically includes matching photos.

### Notes

* built on top of search/filter system (Milestone 11.2)
* updates automatically as new photos are ingested

---

## 56. Manual Collections

**Priority: High**

### Behavior

User can:

* create a collection
* add/remove photos manually
* override or supplement smart rules

---

## 57. Hybrid Collections

**Priority: Medium**

### Behavior

* start with a rule-based collection
* allow manual additions/removals

Example:

* “All Dad photos” + manually include exceptions

---

# 🟢 Albums

## 58. Album Creation

**Priority: Medium**

### Behavior

* create albums independently or within a collection
* manually add/remove photos

---

## 59. Albums as Subsets of Collections

**Priority: Medium**

### Behavior

* albums can live inside a collection
* represent curated subsets

Example:

```text
Henderson Family (Collection)
  ├── Christmases (Album)
  ├── Beach Trips (Album)
```

---

## 60. Standalone Albums

**Priority: Medium**

### Behavior

* albums can exist outside collections if needed
* useful for ad-hoc grouping

---

# 🟡 Data Sources for Grouping

Collections should be able to use:

* people (person assignments)
* clusters (indirectly)
* events (time-based)
* places (GPS grouping)
* provenance (folder/source)
* scan vs digital flag
* filenames / metadata
* manual selection

This leverages all existing system intelligence.

---

# 🟠 UI Considerations (Future)

## Collections View

* list of collections
* create/edit/delete
* show photo count
* optional preview

## Collection Detail

* photo grid
* rule summary (for smart collections)
* manual add/remove controls

## Album View

* nested under collections or standalone
* simple grid + edit controls

---

# 🔴 Constraints & Risks

* complexity of rule builder UI
* performance for large datasets
* syncing smart collections with new ingestion
* avoiding duplication of system-generated structures

---

# 🧠 Guiding Principles

1. **User control complements AI, not replaces it**
2. **Collections should feel natural and flexible**
3. **Do not depend on external album metadata (e.g., iPhone albums)**
4. **Build on top of existing search/filter capabilities**

---

# ✔️ Strategic Value

Adding Collections and Albums will:

* enable personal organization beyond system defaults
* allow storytelling and curation
* replace missing album data from source systems
* significantly improve user experience

---

# 🧭 Position in Roadmap

Should be implemented after:

* Milestone 11.2 (Search & Filtering) ✅
* additional usability improvements
* stable ingestion and identity workflows

Then:

👉 Introduce Collections (smart + manual)
👉 Followed by Albums layer

---

# 🔑 Summary

Current system provides:

* who, what, when, where

Collections/Albums will provide:

* **why / meaning / personal organization**

---
# Addendum — Full Provenance Display and Source History

## Purpose

Introduce a future **provenance visibility layer** so the user can inspect where a photo came from, how it entered the system, and what original source structure is associated with it.

This is especially valuable for:

* scanned photos
* imported archives
* folder-based event grouping
* trust/debugging of automated organization

---

# 🧠 Concept Overview

Provenance is not just metadata — it is part of the meaning of the photo.

Examples of useful provenance:

* original source folder
* full original relative path
* import batch / source folder
* scan/archive origin
* whether the asset came from:

  * scan source
  * iPhone export
  * camera folder
  * shared album export
  * manual import batch

This information can help the user understand:

* where a photo came from
* why it was grouped the way it was
* how scanned materials relate to physical albums or archive structure

---

# 🔵 Core Provenance Display Features

## 61. Show Full Original Source Path in Photo Detail

**Priority: High**

### Enhancement

In photo detail / photo review UI, display:

* full original source path
* or a clearly readable source path section

Example:

```text id="0mjm5z"
Original Source Path:
Scans/Family Albums/1992/Hawaii Trip/IMG_001.jpg
```

### Benefit

* helps verify scan grouping
* makes folder-based provenance visible to the user
* improves trust and debugging

---

## 62. Show Immediate Provenance Folder Separately

**Priority: Medium**

### Enhancement

Display the immediate source folder as a simpler label, for example:

```text id="yrh6l5"
Source Folder: Hawaii Trip
```

This is especially helpful when full paths are long.

---

## 63. Provenance Section in Photo Metadata Panel

**Priority: High**

### Enhancement

Add a dedicated **Provenance** section in photo detail showing available fields such as:

* original source path
* source folder
* import path
* scan vs digital
* import batch id (if available later)

---

# 🟢 Event and Grouping Transparency

## 64. Explain Why a Scan Event Exists

**Priority: Medium**

### Enhancement

In event detail or photo metadata, show when a scan-derived event came from provenance rather than timestamp logic.

Example:

```text id="w6dgqb"
Event Grouping Basis: Source Folder
Derived From: Hawaii Trip
```

### Benefit

* helps explain system decisions
* useful for scan-heavy archives

---

## 65. Show Provenance in Events View

**Priority: Medium**

### Enhancement

When viewing scan-derived events, show folder/source label in the event detail panel.

---

# 🟡 Advanced Provenance Features

## 66. Provenance Breadcrumb UI

**Priority: Medium**

### Enhancement

Render path as breadcrumbs instead of plain text:

```text id="drx9e0"
Scans > Family Albums > 1992 > Hawaii Trip
```

This is more readable than long raw paths.

---

## 67. Copy Provenance Path

**Priority: Low**

### Enhancement

Add a simple copy button so the user can copy the original source path.

Useful for:

* debugging
* finding originals
* referencing folder structure

---

## 68. Search / Filter by Provenance

**Priority: Medium–High**

### Enhancement

Allow future search/filter features to use provenance fields:

* folder names
* path fragments
* import source

Example:

* search for `Hawaii Trip`
* search for `Family Albums`

---

# 🟠 Data & System Extensions

## 69. Provenance History / Import History

**Priority: Medium**

### Enhancement

Track not just original source path, but also:

* when imported
* which batch imported it
* whether moved/reimported
* possible duplicate origin

This would provide a richer source-history model.

---

## 70. Display All Available Provenance Fields

**Priority: Medium**

### Enhancement

Show multiple provenance-related fields when available, not just one.

Examples:

* original source path
* normalized source path
* import batch source
* vault path reference
* scan flag

---

# 🔴 Risks & Considerations

* long paths can clutter UI
* some paths may be inconsistent or messy
* provenance should aid understanding, not overwhelm the user

---

# 🧠 Guiding Principle

> Provenance should be visible enough to support trust, debugging, and archival understanding — but not so noisy that it overwhelms the main photo experience.

---

# ✔️ Strategic Value

Full provenance display will:

* improve confidence in scan-aware grouping
* help explain why events/collections exist
* support archive-oriented workflows
* make imported folder structure visible and useful

---

# 🧭 Position in Roadmap

This should be implemented after:

* stable photo review
* event and place context
* search/filter improvements

Then:

👉 add provenance visibility to photo detail and event context

---

# 🔑 Summary

Current system uses provenance internally.

Future enhancement:

* make provenance visible and explorable in the UI.

---
# Addendum — Full Provenance Display and Source History

## Purpose

Introduce a future **provenance visibility layer** so the user can inspect where a photo came from, how it entered the system, and what original source structure is associated with it.

This is especially valuable for:

* scanned photos
* imported archives
* folder-based event grouping
* trust/debugging of automated organization

---

# 🧠 Concept Overview

Provenance is not just metadata — it is part of the meaning of the photo.

Examples of useful provenance:

* original source folder
* full original relative path
* import batch / source folder
* scan/archive origin
* whether the asset came from:

  * scan source
  * iPhone export
  * camera folder
  * shared album export
  * manual import batch

This information can help the user understand:

* where a photo came from
* why it was grouped the way it was
* how scanned materials relate to physical albums or archive structure

---

# 🔵 Core Provenance Display Features

## 61. Show Full Original Source Path in Photo Detail

**Priority: High**

### Enhancement

In photo detail / photo review UI, display:

* full original source path
* or a clearly readable source path section

Example:

```text id="0mjm5z"
Original Source Path:
Scans/Family Albums/1992/Hawaii Trip/IMG_001.jpg
```

### Benefit

* helps verify scan grouping
* makes folder-based provenance visible to the user
* improves trust and debugging

---

## 62. Show Immediate Provenance Folder Separately

**Priority: Medium**

### Enhancement

Display the immediate source folder as a simpler label, for example:

```text id="yrh6l5"
Source Folder: Hawaii Trip
```

This is especially helpful when full paths are long.

---

## 63. Provenance Section in Photo Metadata Panel

**Priority: High**

### Enhancement

Add a dedicated **Provenance** section in photo detail showing available fields such as:

* original source path
* source folder
* import path
* scan vs digital
* import batch id (if available later)

---

# 🟢 Event and Grouping Transparency

## 64. Explain Why a Scan Event Exists

**Priority: Medium**

### Enhancement

In event detail or photo metadata, show when a scan-derived event came from provenance rather than timestamp logic.

Example:

```text id="w6dgqb"
Event Grouping Basis: Source Folder
Derived From: Hawaii Trip
```

### Benefit

* helps explain system decisions
* useful for scan-heavy archives

---

## 65. Show Provenance in Events View

**Priority: Medium**

### Enhancement

When viewing scan-derived events, show folder/source label in the event detail panel.

---

# 🟡 Advanced Provenance Features

## 66. Provenance Breadcrumb UI

**Priority: Medium**

### Enhancement

Render path as breadcrumbs instead of plain text:

```text id="drx9e0"
Scans > Family Albums > 1992 > Hawaii Trip
```

This is more readable than long raw paths.

---

## 67. Copy Provenance Path

**Priority: Low**

### Enhancement

Add a simple copy button so the user can copy the original source path.

Useful for:

* debugging
* finding originals
* referencing folder structure

---

## 68. Search / Filter by Provenance

**Priority: Medium–High**

### Enhancement

Allow future search/filter features to use provenance fields:

* folder names
* path fragments
* import source

Example:

* search for `Hawaii Trip`
* search for `Family Albums`

---

# 🟠 Data & System Extensions

## 69. Provenance History / Import History

**Priority: Medium**

### Enhancement

Track not just original source path, but also:

* when imported
* which batch imported it
* whether moved/reimported
* possible duplicate origin

This would provide a richer source-history model.

---

## 70. Display All Available Provenance Fields

**Priority: Medium**

### Enhancement

Show multiple provenance-related fields when available, not just one.

Examples:

* original source path
* normalized source path
* import batch source
* vault path reference
* scan flag

---

# 🔴 Risks & Considerations

* long paths can clutter UI
* some paths may be inconsistent or messy
* provenance should aid understanding, not overwhelm the user

---

# 🧠 Guiding Principle

> Provenance should be visible enough to support trust, debugging, and archival understanding — but not so noisy that it overwhelms the main photo experience.

---

# ✔️ Strategic Value

Full provenance display will:

* improve confidence in scan-aware grouping
* help explain why events/collections exist
* support archive-oriented workflows
* make imported folder structure visible and useful

---

# 🧭 Position in Roadmap

This should be implemented after:

* stable photo review
* event and place context
* search/filter improvements

Then:

👉 add provenance visibility to photo detail and event context

---

# 🔑 Summary

Current system uses provenance internally.

Future enhancement:

* make provenance visible and explorable in the UI.

---
# Addendum — Scaling Intelligence: Person Auto-Labeling, Time Layer, and Scan Date Estimation

## Purpose

Define future enhancements required for scaling the system to **5K–10K+ photos**, focusing on:

* person auto-labeling and suggestions
* time as a first-class layer
* scan date estimation and temporal inference

These features enable the system to move from manual-heavy workflows to intelligent, scalable organization.

---

# 🧠 Core Concept

At scale, the system must evolve from:

> “User organizes photos”

to:

> “System organizes photos, user corrects and curates”

---

# 🔵 Person Auto-Labeling and Identity Scaling

## 71. Person Suggestion System

**Priority: High**

### Behavior

When a new cluster is created:

* compare its embeddings against clusters already assigned to known people
* suggest likely matches:

```text
Likely: Audrey Henderson (92% confidence)
```

User can:

* accept
* reject
* ignore

---

## 72. Confidence-Based Auto Assignment

**Priority: Medium**

### Behavior

If confidence exceeds a threshold:

* auto-assign person
* optionally flag as “auto-assigned”

### Safety

* must be reversible
* must not overwrite manual assignments

---

## 73. Preserve Manual Identity Work

**Priority: Critical**

### Requirement

* manual cluster-to-person assignments must always override automation
* no automatic process should silently erase or override confirmed identity work

---

# 🟢 Time as a First-Class Layer

## 74. Explicit Time Layer

**Priority: High**

### Enhancement

Elevate time from EXIF metadata into a visible and usable layer:

* browse by year
* browse by month
* timeline navigation
* filter by date range

---

## 75. Multiple Time Types per Photo

**Priority: High**

### Model

Each photo may have:

* `captured_at_exact` (EXIF)
* `captured_at_estimated`
* `captured_at_range`
* `imported_at`
* `date_source`:

  * EXIF
  * scan
  * inferred
  * user-entered

---

## 76. Timeline UI (Future)

**Priority: Medium**

### Enhancement

* visual timeline browsing
* group by decade/year
* combine with people/events/places

---

# 🟡 Scan Date Estimation

## 77. Provenance-Based Time Estimation

**Priority: High**

### Behavior

Use:

* folder names (e.g., “1992 Hawaii Trip”)
* album structure
* batch context

to infer approximate date.

---

## 78. Visual Clue Extraction (Advanced)

**Priority: Medium–Low**

### Potential Signals

* printed dates in image (OCR)
* clothing, objects, vehicles
* image quality / film characteristics
* known people ages

---

## 79. Estimated Date Confidence

**Priority: Medium**

### Model

Each inferred date should include:

* estimated date or range
* confidence level
* source of inference

---

# 🟠 System Behavior at Scale

## 80. Automatic vs Manual Responsibilities

### Automatic

* face clustering
* event grouping
* place grouping
* time grouping
* object/scene detection (future)

### Semi-Automatic

* person assignment suggestions
* scan date estimation

### Manual (User Authority)

* identity corrections
* collections/albums
* special case adjustments

---

# 🔴 Risks & Constraints

* incorrect auto-labeling of people
* over-reliance on weak signals for scan dates
* user trust degradation if automation is not transparent

---

# 🧠 Guiding Principles

1. Automation should assist, not override
2. Identity (people) must remain user-controlled
3. Time should be flexible and multi-source
4. Provenance is a strong signal for scans
5. All automated decisions should be explainable where possible

---

# ✔️ Strategic Value

These features will:

* make large imports manageable
* reduce manual workload dramatically
* improve search and retrieval
* enable future semantic and narrative capabilities

---

# 🧭 Position in Roadmap

Implement after:

* Milestone 11 core usability and detail improvements
* stable ingestion and identity workflows

Then:

👉 add person suggestions
👉 add time layer UI
👉 introduce scan date estimation

---

# 🔑 Summary

Scaling requires:

* smarter identity handling
* richer time understanding
* better handling of imperfect scan metadata

---
# Parking Lot — Drop Zone Lifecycle and Processing Scope Control

## Problem

The current pipeline treats the drop zone as a **persistent working set**, resulting in:

* Previously staged files being reprocessed on subsequent runs
* “Single file” ingestion unintentionally triggering multi-file processing
* Confusion around pipeline scope (batch vs global)
* Potential performance degradation as drop zone grows

---

## Goal

Introduce a clear and deterministic **drop zone lifecycle model** that:

* ensures each pipeline run operates on an explicit batch
* prevents unintended reprocessing of already handled files
* supports both:

  * one-off ingestion runs
  * future automated/scheduled ingestion

---

## Desired Behavior

### Batch Semantics

Define drop zone behavior as one of:

* **Ephemeral batch mode (preferred)**

  * files are staged → processed → cleared
  * drop zone is empty after successful run

* **Persistent queue mode (alternative)**

  * files marked with processing state
  * processed files excluded from future runs

---

### Processing Scope Control

Pipeline should clearly distinguish:

* **Newly staged assets (delta set)**
* **Existing assets (global set)**

Each stage must explicitly declare:

* operates on:

  * new assets only
  * changed assets only
  * all assets (global)

---

### Failure Handling

* failed files remain in drop zone (or flagged)
* successful files are:

  * removed (batch mode), or
  * marked processed (queue mode)

---

### Observability

Pipeline output should clearly show:

* number of newly staged files
* number of previously staged files (if any)
* whether run is:

  * batch-only
  * mixed (batch + global stages)

---

## Constraints

* Must NOT break existing ingestion or deduplication logic
* Must preserve provenance tracking
* Must remain deterministic and rerunnable
* Must not introduce destructive behavior without explicit confirmation

---

## Future Integration

This system will support:

* incremental processing (11.8)
* admin workflows (11.13)
* scheduled ingestion
* large archive scaling

---

## Notes

This is a **pipeline orchestration concern**, not a data model change.

Implementation should be simple and explicit, not overly abstract.
# Parking Lot — Duplicate Lineage Re-evaluation on Config Change

## Problem

Duplicate grouping and canonical selection currently depend on:

* Hamming distance threshold
* Quality scoring weights
* Pre-filter parameters (resolution band, time window, etc.)

These are **config-driven**, but:

* existing assets are only evaluated at ingestion or backfill
* changes to config do NOT automatically trigger re-evaluation
* system may become inconsistent with updated rules over time

---

## Goal

Introduce a controlled mechanism to **re-evaluate duplicate lineage and canonical selection** when configuration changes.

---

## Desired Behavior

### Re-evaluation Trigger

System should support:

* manual trigger:

  * e.g., script or admin action
* optional future:

  * automatic trigger when config version changes

---

### Re-evaluation Scope

Configurable scope:

* full system (all assets)
* subset:

  * specific time range
  * specific asset groups
  * newly ingested assets only

---

### Re-evaluation Actions

* recompute pHash comparisons if needed (optional)
* re-run grouping logic
* recompute canonical selection
* preserve:

  * provenance
  * asset identity
  * lineage continuity where possible

---

### Stability Requirements

* deterministic results
* minimal unnecessary churn
* avoid group ID changes where composition unchanged (future improvement)

---

### Observability

Output should include:

* groups changed
* canonical switches
* assets reassigned
* summary before/after stats

---

## Constraints

* Must NOT run automatically in normal ingestion flow
* Must be explicitly invoked
* Must not impact identity system (faces, people)
* Must remain safe and reversible

---

## Future Integration

This feature supports:

* tuning near-duplicate detection
* improving canonical selection logic
* scaling to larger archives
* admin workflows (11.13)

---

## Notes

This is an **administrative reprocessing capability**, not part of normal ingestion.

Should be implemented as a controlled script or admin tool.
# Parking Lot — Event Clustering Stability and Non-Destructive Behavior

## Problem

The current event clustering system operates as a **full rebuild on every pipeline run**, which:

* deletes all existing events
* clears all asset-to-event assignments
* recreates events and reassigns assets

This results in:

* **event ID churn** on every run
* potential changes in asset-to-event grouping when inputs change
* loss of any future manual edits (labels, merges, splits)
* instability for any UI or feature relying on persistent event identity

---

## Current State (Accepted Behavior)

* Event clustering is **global and destructive by design**
* Events are currently:

  * system-generated
  * not user-edited
  * deterministic based on metadata (time + provenance)

This makes rebuild behavior acceptable **at this stage**

---

## Goal

Evolve event clustering toward a **non-destructive, identity-stable model** that:

* preserves event identity where possible
* minimizes unnecessary churn on reruns
* supports future user interaction with events

---

## Desired Behavior (Future)

### 1. Stable Event Identity

* Preserve event IDs when:

  * asset membership is unchanged
  * event boundaries are unchanged

* Avoid delete/recreate when no meaningful change occurred

---

### 2. Incremental Update Capability (Partial)

Support limited incremental behavior:

* new assets can be assigned to:

  * existing events
  * new events if needed

* only affected events are recalculated when:

  * time gaps are impacted
  * capture-time trust changes

---

### 3. Controlled Rebuild

Retain ability to:

* perform full rebuild when explicitly requested
* compare before/after results for validation

---

### 4. Separation of System vs User Data

Prepare for future event editing by separating:

* system-generated properties:

  * time boundaries
  * inferred grouping
* user-controlled properties:

  * labels
  * notes
  * manual merges/splits

User-controlled data must **not be lost on recompute**

---

### 5. Observability

Future system should be able to report:

* events unchanged
* events modified
* events merged/split
* assets reassigned

---

## Constraints

* Must preserve correctness of time-based grouping
* Must not introduce inconsistent event boundaries
* Must remain deterministic and explainable
* Must not compromise ingestion pipeline safety

---

## Complexity Note

Event clustering is inherently more complex than face clustering because:

* boundaries depend on time gaps
* inserting a single asset may:

  * merge adjacent events
  * split an existing event
  * shift boundaries non-locally

A fully incremental solution may not always be feasible; hybrid approaches are acceptable.

---

## Future Integration

This work should align with:

* **11.9 — Timeline and Time Layer**
* future event editing capabilities
* collections/albums (11.10)
* sharing (11.14)

---

## Notes

This is a **known and accepted limitation** at the current stage.

Do not implement changes prematurely. Address when:

* events become user-editable
* timeline becomes a primary navigation layer
* event identity stability becomes important to UX
