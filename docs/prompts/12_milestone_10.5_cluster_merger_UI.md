**Milestone 10.5 — Cluster Merge UI**

**Goal**

Add a simple UI to **merge one face cluster into another**.

This completes the core correction toolkit:

-   assign person ✅
-   remove face ✅
-   move face ✅
-   ignore cluster ✅
-   **merge clusters (this milestone)**

The merge UI should be **simple, explicit, and safe**.

**Context**

Previous milestones completed:

**Milestone 10.1**

-   Backend API layer implemented

**Milestone 10.2**

-   Review UI (cluster list + detail)

**Milestone 10.3**

-   Correction actions:
    -   ignore cluster
    -   remove face
    -   move face

**Milestone 10.4**

-   People management UI
-   create person
-   assign cluster to person

The system is now fully interactive.

This milestone adds **cluster merging** to fix incorrect clustering results.

**Scope**

Add UI support to:

-   merge the currently selected cluster into another cluster
-   call the existing backend merge endpoint
-   refresh UI correctly after merge

**Out of Scope (DO NOT DO)**

-   no redesign of UI layout
-   no multi-select cluster UI
-   no drag-and-drop merging
-   no automatic merge suggestions
-   no undo system
-   no bulk merge
-   no merge history
-   no conflict resolution UI
-   no search/filter UI
-   no thumbnails/media work
-   no backend clustering changes

Keep this simple and controlled.

**Backend Requirement**

Milestone 10.1 may or may not already include:

**POST /api/clusters/merge**

If not present, add it now.

**Request:**

{

"source_cluster_id": 11,

"target_cluster_id": 5

}

**Response:**

{

"success": true

}

**Behavior:**

-   move all faces from source → target cluster
-   delete or deactivate source cluster (based on existing backend logic)
-   ensure data integrity
-   reuse existing merge logic from scripts/services

Do not rewrite clustering logic.

**Primary Outcome**

User should be able to:

1.  select a cluster in Review UI
2.  enter a target cluster id
3.  merge current cluster into that target
4.  see cluster list and detail update correctly
5.  continue working without UI breaking

**UI Design (Simple)**

Add merge controls to the **Cluster Detail panel**.

Suggested layout:

Cluster \#11

Assigned: Unassigned

[Person dropdown] [Assign]

\--- Merge Cluster ---

Target Cluster ID: [____]

[ Merge Into Target ]

\--- Faces ---

[ face grid... ]

**UI Behavior**

**1. Merge input**

-   numeric input for target_cluster_id
-   controlled input state

**2. Merge button**

Label:

-   Merge Into Target

**Validation Rules (Important)**

Before calling API:

**Block these cases:**

1.  target cluster id is empty
2.  target cluster id equals current cluster id

Show simple messages:

-   Target cluster is required
-   Cannot merge a cluster into itself

Do not call API if validation fails.

**Confirmation (Required)**

Before merge, show:

window.confirm("Are you sure you want to merge this cluster into the target cluster? This cannot be undone.")

If user cancels:

-   do nothing

**API Call**

On confirm:

-   call POST /api/clusters/merge
-   send:
    -   source = currently selected cluster
    -   target = user input

**Post-Merge Behavior (Critical)**

After successful merge:

**Refresh data**

-   reload cluster list
-   reload cluster detail

**Handle selection**

If source cluster no longer exists:

-   select the target cluster if it exists in refreshed list
-   otherwise select first cluster in list
-   if no clusters remain:
    -   clear selection
    -   show empty state

**Error Handling**

Show simple error messages in the existing shared error area:

Examples:

-   Failed to merge clusters
-   include backend error detail if available

**Loading State**

-   disable merge button while request is running
-   optionally show:
    -   Merging...

Keep it simple.

**API Client Updates**

Extend api.ts with:

-   mergeClusters(sourceClusterId, targetClusterId)

Use existing API base URL setup.

**Component Changes**

Modify:

**ClusterDetail.tsx**

Add:

-   merge section (input + button)
-   validation
-   confirmation
-   call handler passed from parent

**page.tsx**

Add:

-   merge handler
-   refresh logic
-   selection fallback logic

Do not refactor entire component structure.

**State Management**

Keep same pattern:

-   useState
-   useEffect
-   explicit refresh after mutation

Do not introduce new libraries.

**Styling**

Minimal styling only:

-   small section divider
-   label for merge section
-   input + button aligned cleanly

No design system work.

**Verification Checklist**

Manually verify:

1.  UI loads normally
2.  cluster selection still works
3.  assign-person still works
4.  ignore/remove/move still work
5.  merge input accepts valid id
6.  merging cluster works successfully
7.  source cluster disappears after merge (if expected)
8.  target cluster reflects updated faces
9.  UI selects correct fallback cluster
10. invalid merge (same cluster) is blocked
11. API error is shown cleanly

**Deliverables**

After completion, provide:

1.  list of files added/modified
2.  exact repo-relative file paths
3.  summary of merge UI implementation
4.  summary of merge API usage
5.  notes on selection fallback logic
6.  manual verification notes
7.  any limitations deferred to later milestone

**Definition of Done**

Milestone 10.5 is complete when:

-   user can merge clusters from the UI
-   validation prevents invalid merges
-   UI updates correctly after merge
-   no regression to previous functionality
-   UI remains simple and stable

**Do NOT add in this milestone**

-   no cluster picker UI
-   no search
-   no multi-select
-   no merge preview
-   no undo
-   no analytics
-   no background processing

**Notes for Next Milestone**

Milestone 10.6 should be:

👉 **Thumbnail / Media Serving**

This will:

-   display real face images instead of placeholders
-   significantly improve usability

**Suggested Commit**

git commit -m "Milestone 10.5: Add cluster merge UI with validation and safe merge flow"
