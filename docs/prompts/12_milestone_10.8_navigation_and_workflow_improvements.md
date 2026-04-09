**Milestone 10.8 — Navigation and Workflow Improvements**

**Goal**

Improve the speed and usability of the existing UI so cluster review and person labeling require fewer clicks and less context switching.

This milestone should make the current application easier to use without redesigning the system.

**Context**

Completed milestones now include:

**Milestone 10.1**

-   backend API layer

**Milestone 10.2**

-   review UI with cluster list and cluster detail

**Milestone 10.3**

-   correction actions:
    -   ignore cluster
    -   remove face
    -   move face

**Milestone 10.4**

-   people management UI
-   create person flow

**Milestone 10.5**

-   cluster merge UI

**Milestone 10.6**

-   local thumbnail/media serving

**Milestone 10.7**

-   thumbnail continuity after move/merge

The system is now functional and visually usable.  
What is missing is smoother navigation between review tasks.

**Primary Outcome**

When complete, the user should be able to move through review work more efficiently by:

1.  opening a person in the People view
2.  clicking one of that person’s clusters
3.  jumping directly to the Review view with that cluster selected
4.  moving through clusters more quickly in the Review view
5.  keeping context after actions without unnecessary re-clicking

**Scope**

Add small workflow/navigation improvements to the existing UI.

Required:

-   click a cluster from People view to jump to Review view and select that cluster
-   add previous/next cluster navigation in Review view
-   preserve selection more intelligently after actions when possible

Optional if simple:

-   auto-scroll selected cluster into view in the cluster list
-   highlight selected cluster more clearly

Keep the milestone practical and focused.

**Out of Scope (DO NOT DO)**

-   no routing redesign
-   no full sidebar/navigation overhaul
-   no search/filter yet
-   no keyboard shortcut system
-   no pagination redesign
-   no thumbnail redesign
-   no full cluster history
-   no undo system
-   no people merge/rename/delete
-   no advanced state library
-   no backend redesign unless absolutely required

Keep this milestone frontend-focused and lightweight.

**Required Features**

**1. Jump from People view to Review view**

In the People view, each listed cluster under a person should become clickable.

Behavior:

-   clicking a cluster in People view switches to the Review view
-   the clicked cluster becomes the selected cluster in Review
-   cluster detail loads for that cluster immediately

Example:

Alice Henderson

Clusters: 3

\- Cluster \#1 (4 faces) \<-- click

\- Cluster \#7 (6 faces)

\- Cluster \#19 (2 faces)

Clicking Cluster \#7 should:

-   switch to Review tab
-   select cluster 7
-   load cluster 7 detail

This is the most important feature in 10.8.

**2. Previous / Next cluster navigation in Review view**

Add simple navigation controls in the Review view for moving through the currently loaded cluster list.

Suggested controls:

-   Previous
-   Next

Placement:

-   near the cluster detail header is fine
-   keep it simple and visible

Behavior:

-   Previous selects the previous cluster in the current cluster list
-   Next selects the next cluster in the current cluster list
-   disable button if there is no previous/next cluster

This should work with the currently loaded cluster list order.

**3. Preserve selected cluster after refresh when possible**

Current refresh logic already handles fallback selection. Improve it slightly:

After actions like:

-   assign person
-   ignore
-   remove face
-   move face
-   merge

Behavior should be:

-   if the intended selected cluster still exists, keep it selected
-   if not, fall back cleanly using existing rules

For merge:

-   prefer target cluster
-   else first cluster
-   else empty state

For other actions:

-   prefer current cluster if still present
-   else first cluster
-   else empty state

Keep this logic explicit and readable.

**Optional Small Enhancements**

Include only if simple and low-risk:

**A. Auto-scroll selected cluster into view**

When cluster selection changes, scroll the selected cluster item into view in the left cluster list.

This is helpful, but optional.

**B. Stronger selected-state styling**

Slightly improve visual highlighting for the selected cluster.

Only minor styling changes if needed.

Do not turn this into a redesign.

**Frontend Implementation Guidance**

**1. No backend changes by default**

This milestone should use existing APIs.

Use current data already available from:

-   GET /api/clusters
-   GET /api/clusters/{cluster_id}
-   GET /api/people-with-clusters

Only add backend work if there is a real blocker, which is not expected.

**2. State ownership**

Keep using the current simple top-level state pattern.

Likely in page.tsx:

-   current view (Review or People)
-   selected cluster id
-   loaded cluster list
-   selected cluster detail
-   people-with-clusters data

Continue using:

-   useState
-   useEffect
-   explicit refresh functions

Do not introduce Redux/Zustand/React Query.

**3. People view changes**

Update the People view so cluster entries are clickable.

Suggested behavior:

-   render clusters as buttons or clickable text rows
-   clicking calls a parent handler such as:
    -   onSelectClusterFromPeople(clusterId)

The parent handler should:

-   set current view to Review
-   set selected cluster id
-   trigger/load selected cluster detail

Keep implementation straightforward.

**4. Review view changes**

Add previous/next controls to the selected cluster area.

A simple implementation is enough:

-   compute current cluster index from cluster list
-   determine previous and next ids
-   wire buttons to selection changes

No fancy navigation component needed.

**Error Handling**

Keep existing simple error handling style.

If a cluster clicked from People view no longer exists:

-   fail gracefully
-   reload clusters if needed
-   fall back to first available cluster or empty state

Do not crash or leave UI stuck.

**Styling Guidance**

Keep styling minimal and consistent.

Requirements:

-   clickable clusters in People view should look interactive
-   Previous / Next controls should be clear
-   selected cluster state should remain visually obvious

No major CSS rewrite.

**Verification Checklist**

Manually verify:

1.  app still loads normally
2.  Review tab still works
3.  People tab still works
4.  clicking a cluster in People view switches to Review
5.  clicked cluster becomes selected
6.  cluster detail loads correctly after People → Review jump
7.  Previous button works
8.  Next button works
9.  buttons disable correctly at list boundaries
10. assign/ignore/remove/move/merge still work
11. selection stays stable after refresh when possible
12. empty/fallback behavior still works correctly

Optional:  
13\. selected cluster auto-scroll works if implemented

**Deliverables**

After completion, provide:

1.  list of files added or modified
2.  exact repo-relative file paths
3.  summary of People → Review jump behavior
4.  summary of Previous / Next navigation behavior
5.  notes on any selection-preservation improvements
6.  manual verification notes
7.  any limitations intentionally deferred

**Definition of Done**

Milestone 10.8 is complete when:

-   user can click a person’s cluster and jump into Review with that cluster selected
-   user can move Previous/Next through the current cluster list
-   selection behavior after actions is more stable and intentional
-   no regression to existing functionality

**Do NOT add in this milestone**

-   search/filter
-   keyboard shortcuts
-   routing overhaul
-   large layout redesign
-   people edit/delete/merge
-   advanced cluster browsing tools
-   new backend data models

Those belong later.

**Notes for Next Milestone**

After 10.8, likely next candidates are:

1.  search/filter for clusters and people
2.  maintenance/admin tools such as unignore
3.  larger image preview
4.  keyboard shortcuts for faster review

But 10.8 should focus only on faster movement through the existing workflow.

**Suggested Commit**

git commit -m "Milestone 10.8: Improve navigation between people and cluster review workflows"
