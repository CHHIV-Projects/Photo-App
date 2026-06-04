**Milestone 11.2 — Search and Filtering Across Core Views**

**Goal**

Add practical search and filtering so the user can more quickly find relevant content across the existing UI.

This milestone should improve usability without redesigning the system.

**Context**

By the start of Milestone 11.2, the application supports:

-   Review (clusters)
-   People
-   Unassigned Faces
-   Photos
-   Events
-   Places

The core system is now functional end-to-end, but browsing is still largely manual.

This milestone adds the first general usability layer:

-   search
-   filtering
-   narrowing visible results

**Problem This Milestone Solves**

As the dataset grows, it becomes harder to:

-   find a specific person
-   find unassigned/unlabeled work
-   locate a particular cluster
-   narrow photo/event/place views to the most relevant items

Right now, users must scroll through lists manually.

This milestone makes the system easier to use at larger scale.

**Primary Outcome**

When complete, the user should be able to:

1.  search people by name
2.  filter clusters by useful review states
3.  search photos by filename
4.  optionally narrow events and places with simple text filtering
5.  reduce scrolling and find things faster

**Scope**

Build a first-pass search/filter layer for the existing UI.

Required:

-   People view search by display name
-   Review view filtering for cluster workflow
-   Photos view search by filename
-   simple client-side filtering where practical

Optional if simple:

-   Event list text filter
-   Places list text filter
-   unassigned faces quick filter by face id or asset short hash

Keep this milestone practical and lightweight.

**Out of Scope (DO NOT DO)**

-   no full-text search engine
-   no semantic search
-   no Elasticsearch/OpenSearch
-   no advanced ranking system
-   no complex saved filters
-   no search history
-   no multi-page query routing
-   no backend-wide query DSL
-   no redesign of current views

This is a **basic usability milestone**, not a search platform.

**Guiding Principle**

Prefer the simplest implementation that gives real value.

Use:

-   client-side filtering where data sets are already loaded and reasonably small
-   minimal backend query params only when really needed

Do not overengineer.

**Required Features**

**1. People view search**

Add a search input in the People view.

Behavior:

-   filters people by display_name
-   case-insensitive substring match
-   updates visible list as user types

Examples:

-   typing aud matches Audrey Henderson
-   typing hend matches Audrey Henderson

No backend search endpoint required unless current People list is too large to handle client-side.

**2. Review view filtering**

Add simple controls to make cluster review easier.

Required filters:

**A. Show only unassigned-person clusters**

Clusters where:

-   cluster exists
-   no person assigned

**B. Show all reviewable clusters**

Current default-style view

Optional if simple:

**C. Show only clusters with at least N faces**

A small threshold filter like:

-   1+
-   2+
-   5+

If that becomes too much for 11.2, skip it.

At minimum, implement:

-   All
-   Unassigned Person

Behavior:

-   filter applies to the cluster list in Review
-   selection/fallback should remain stable

**3. Photos view search**

Add a search input in the Photos view.

Behavior:

-   filter photo list by filename
-   case-insensitive substring match
-   updates visible list as user types

No need for advanced metadata search in this milestone.

**Optional Features**

Include only if simple and low-risk.

**4. Events view text filter**

Filter event list by:

-   formatted date text
-   maybe filename matches in loaded event detail only if trivial

This is optional. Do not overbuild.

**5. Places view text filter**

If places currently show raw coordinates, a simple text filter by coordinate string is acceptable.

This is optional and lower priority.

**6. Unassigned Faces quick filter**

A simple text input that matches:

-   face id
-   asset short hash

This is optional.

**Backend Considerations**

Default approach:

-   keep filtering client-side in frontend for this milestone

Only add backend filtering if:

-   there is already an obvious API query parameter pattern
-   or client-side filtering becomes clearly impractical

For 11.2, frontend filtering is preferred.

**Frontend Requirements**

**1. People search UI**

In People view:

-   add search box above people list
-   filter visible people live as user types

**2. Review filter UI**

In Review view:

-   add small filter control above cluster list

Suggested options:

-   All
-   Unassigned Person

Simple buttons, select, or segmented control are fine.

**3. Photos search UI**

In Photos view:

-   add search box above photo list
-   filter visible photo list live as user types

**Selection Behavior**

Important:

When filtering changes:

-   if currently selected item is still visible, keep it selected
-   if currently selected item is filtered out:
    -   select first visible item
    -   or clear selection if no visible items remain

Apply this to:

-   Review clusters
-   Photos list
-   optionally People if a selected person concept exists later

Keep this logic stable and predictable.

**Error Handling**

Minimal:

-   search/filter should not generate new API errors in normal use
-   empty results should show clean messages

Examples:

-   No people match your search.
-   No clusters match this filter.
-   No photos match your search.

**Suggested UI Shape**

**People**

People

[ Search people... ]

Audrey Henderson

Bob Henderson

...

**Review**

Clusters

[ All ] [ Unassigned Person ]

Cluster \#11

Cluster \#14

...

**Photos**

Photos

[ Search photos... ]

IMG_0727.JPG

IMG_0873.JPG

...

**Styling Guidance**

Keep styling minimal and consistent with current app.

Requirements:

-   search inputs should be obvious
-   filter controls should be compact and readable
-   no full redesign
-   no design system expansion

**Suggested File Changes**

Likely frontend-only changes:

-   page.tsx
-   PeopleView.tsx
-   PhotosView.tsx
-   maybe Review/cluster list components
-   ui-api.ts only if small helper types are needed
-   CSS modules as needed

Avoid backend changes unless necessary.

**Verification Checklist**

Manually verify:

1.  app still loads normally
2.  People search works
3.  Review filter works
4.  Photos search works
5.  selection remains stable when possible
6.  selection falls back cleanly when filtered out
7.  empty-state messages appear correctly
8.  existing correction flows still work
9.  existing Events / Places views remain unaffected

Optional:  
10\. any extra filters implemented also work correctly

**Deliverables**

After completion, provide:

1.  files added/modified
2.  exact repo-relative file paths
3.  summary of search/filter behavior per view
4.  note whether any backend changes were needed
5.  manual verification notes
6.  known limitations intentionally deferred

**Definition of Done**

Milestone 11.2 is complete when:

-   user can search People by name
-   user can filter Review clusters by useful state
-   user can search Photos by filename
-   selection remains stable or falls back cleanly
-   no regression to existing workflows

**Do NOT add in this milestone**

-   advanced search engine
-   semantic search
-   saved filters
-   ranking systems
-   global unified search across all entities
-   complex query syntax

Those belong later.

**Notes for Next Milestone**

After 11.2, likely next candidates are:

1.  scan-aware event logic
2.  event/place refinement tools
3.  usability polish
4.  smarter move/assignment helpers

But 11.2 should focus only on simple, practical search and filtering.

**Suggested Commit**

git commit -m "Milestone 11.2: Add search and filtering across people, review clusters, and photos"


1. Please include the Review face-count threshold filters in this pass: `1+`, `2+`, and `5+`, along with `All` and `Unassigned Person`.

2. Please include the optional simple client-side text filters for Events, Places, and Unassigned Faces in this same pass.

3. Use the existing button styling with a clear active selected state for the Review filters.

4. For selection stability in Review, use option (a): if the current selection is filtered out, call `onSelectCluster(firstVisible.cluster_id)`, or clear selection if nothing remains visible.

Please proceed with that approach.
