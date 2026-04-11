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
