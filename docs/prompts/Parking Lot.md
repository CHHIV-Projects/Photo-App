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
