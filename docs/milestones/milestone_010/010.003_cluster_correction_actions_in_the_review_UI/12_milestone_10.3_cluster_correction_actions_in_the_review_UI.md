**Milestone 10.3 — Cluster Correction Actions in the Review UI**

**Goal**

Extend the existing Milestone 10.2 review screen so the user can perform the core correction actions directly from the UI:

-   remove a face from its cluster
-   move a face to another cluster
-   ignore a cluster

This milestone should build on the existing review page and existing API endpoints.  
Do **not** redesign the app.

**Context**

Milestone 10.1 is complete:

-   FastAPI API layer exists for clusters, faces, and people
-   endpoints already exist for:
    -   GET /api/clusters
    -   GET /api/clusters/{cluster_id}
    -   POST /api/clusters/{cluster_id}/assign-person
    -   POST /api/clusters/{cluster_id}/ignore
    -   POST /api/faces/{face_id}/remove-from-cluster
    -   POST /api/faces/{face_id}/move
    -   GET /api/people
    -   GET /api/people-with-clusters

Milestone 10.2 is complete:

-   Next.js review page exists
-   cluster list works
-   selected cluster detail works
-   face grid works
-   assign-person flow works
-   local CORS support exists
-   env-backed API base URL exists

This milestone adds **correction actions only**.

**Scope**

Add UI controls for:

1.  ignoring the currently selected cluster
2.  removing an individual face from the current cluster
3.  moving an individual face to another cluster

These actions must use the existing backend API.

**Out of Scope (DO NOT DO)**

-   no people page yet
-   no search/filter UI
-   no pagination UI
-   no merge cluster UI yet
-   no thumbnail/media serving work
-   no drag-and-drop
-   no bulk actions
-   no undo system
-   no optimistic updates
-   no modal framework
-   no routing redesign
-   no editing people
-   no backend behavior changes unless absolutely required for UI support

Keep this milestone narrow.

**Primary Outcome**

When complete, the user should be able to:

1.  open the existing review screen
2.  select a cluster
3.  ignore that cluster from the UI
4.  remove a specific face from the cluster from the UI
5.  move a specific face into another cluster from the UI
6.  see the UI refresh correctly after each action

**UI Behavior Requirements**

**1. Ignore selected cluster**

Add an **Ignore Cluster** button in the selected cluster panel.

Behavior:

-   when clicked, call POST /api/clusters/{cluster_id}/ignore
-   after success:
    -   refresh cluster list
    -   refresh selected cluster detail if still relevant
    -   if ignored clusters are excluded from the list and the current cluster disappears, select the next available cluster automatically
    -   if no clusters remain, show a clean empty state

Keep the interaction simple.

A lightweight confirmation like window.confirm(...) is acceptable for this milestone.

**2. Remove face from cluster**

For each face tile in the face grid, add a simple action button:

-   Remove from cluster

Behavior:

-   when clicked, call POST /api/faces/{face_id}/remove-from-cluster
-   after success:
    -   refresh cluster detail
    -   refresh cluster list
    -   if the cluster now has zero faces or otherwise disappears from review results, handle selection gracefully

Use a simple confirmation prompt before removing.

**3. Move face to another cluster**

For each face tile, add a simple move control.

Keep this implementation minimal and testable.

Recommended simple version:

-   text input or numeric input for target cluster id
-   button labeled Move

Behavior:

-   user enters target cluster id
-   click move
-   call POST /api/faces/{face_id}/move
-   after success:
    -   refresh cluster detail
    -   refresh cluster list

Important:

-   each face tile may maintain its own local input state, or the parent may manage it
-   keep implementation simple, explicit, and beginner-friendly

Do not build a fancy cluster picker in this milestone.

**Error Handling Requirements**

Show simple visible errors when an action fails.

Examples:

-   Failed to ignore cluster
-   Failed to remove face from cluster
-   Failed to move face

If backend returns a useful error detail, surface it in a simple readable way.

Do not build a toast system.

**Loading / Action States**

Add lightweight action-state handling so the user has feedback.

Examples:

-   disable ignore button while request is running
-   disable remove/move controls while the action for that face is running
-   optionally show text like:
    -   Ignoring...
    -   Removing...
    -   Moving...

Keep this local and simple.

**Recommended Component Changes**

Build on the current component structure from 10.2.

Possible updates:

-   ClusterDetail.tsx
    -   add Ignore Cluster button
-   FaceGrid.tsx
    -   render per-face action controls
-   optionally add a small face action subcomponent if helpful

Keep the structure understandable.  
Do not refactor the whole screen unless necessary.

**API Client Updates**

Extend the existing frontend API helper to include:

-   ignoreCluster(clusterId)
-   removeFaceFromCluster(faceId)
-   moveFace(faceId, targetClusterId)

Reuse the env-backed API base URL already created in 10.2.

**State Management Rules**

Keep using the same approach as 10.2:

-   useState
-   useEffect
-   explicit refresh after mutations

Do not introduce:

-   Redux
-   Zustand
-   React Query
-   optimistic caching
-   global mutation orchestration

**Selection / Refresh Rules**

Handle post-action refresh carefully.

**After ignoring a cluster**

-   reload clusters
-   if the selected cluster no longer exists in the list:
    -   select the first remaining cluster
    -   or clear selection if none remain

**After removing a face**

-   reload cluster detail
-   reload clusters
-   if selected cluster is no longer available after refresh, select first remaining cluster

**After moving a face**

-   reload cluster detail
-   reload clusters
-   keep selection if the cluster still exists
-   otherwise fall back to first remaining cluster

This is important for a stable UI.

**UX Requirements**

Keep UX simple and safe.

Acceptable for this milestone:

-   window.confirm(...) before destructive actions
-   inline error messages
-   inline inputs for target cluster id

Do not build:

-   fancy dialogs
-   side drawers
-   multi-step action flows

**Visual / Styling Requirements**

Keep styling minimal and consistent with 10.2.

Requirements:

-   correction buttons should be clearly visible
-   destructive actions should be visually distinct enough to avoid confusion
-   layout should remain readable
-   no design-system work

A small amount of CSS adjustment is fine.

**Verification Checklist**

Manually verify:

1.  existing review page still loads
2.  cluster selection still works
3.  assign-person still works after changes
4.  ignore cluster works
5.  ignored cluster disappears from default list if backend excludes ignored clusters
6.  face removal works
7.  move face works with a valid target cluster id
8.  invalid move shows a clear error
9.  UI does not crash if selected cluster disappears after an action
10. missing thumbnails still render gracefully

Please test against the existing backend on port 8001.

**Deliverables**

After completion, provide:

1.  list of files added or modified
2.  exact repo-relative file paths
3.  short summary of UI changes
4.  short summary of API helper changes
5.  notes on how post-action refresh/selection is handled
6.  manual verification notes
7.  any limitations intentionally deferred to Milestone 10.4

**Definition of Done**

Milestone 10.3 is complete when:

-   user can ignore the selected cluster from the UI
-   user can remove a face from the current cluster from the UI
-   user can move a face to another cluster from the UI
-   UI refreshes correctly after each action
-   selection remains stable or falls back cleanly when data changes
-   no major regression to the Milestone 10.2 review flow

**Do NOT add in this milestone**

Specifically do not add:

-   cluster merge UI
-   people page
-   search
-   filters
-   pagination controls
-   thumbnail media serving
-   multi-page navigation redesign
-   undo/redo
-   keyboard shortcuts
-   advanced confirmation dialogs

Those are later milestones.

**Notes for Next Milestone**

Milestone 10.4 will likely add one or both of:

-   simple people view using GET /api/people-with-clusters
-   cluster merge UI

This milestone should keep the current review page clean and extensible.

1. Clear the move target input only after a successful move, and only for the face that was moved.

2. Use one shared action-error area in the selected-cluster panel for 10.3.

3. Add simple client-side validation to block moving a face to the currently selected cluster. Show a readable message and skip the API call.

4. If the selected cluster disappears after ignore/remove/move, fall back to the first cluster in the refreshed list. If no clusters remain, clear selection and show an empty state.

Please proceed with that approach.
