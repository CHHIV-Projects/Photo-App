**Milestone 10.2 — Next.js Frontend Scaffolding and First Working Review Screen**

**Goal**

Build the **first minimal UI screen** for face cluster review using the API completed in Milestone 10.1.

This milestone should create a simple, working Next.js page that allows the user to:

-   view face clusters
-   select a cluster
-   view faces within that cluster
-   assign the selected cluster to a person

This is the **first usable UI slice** only.

**Context**

Milestone 10.1 is complete and provides these backend endpoints:

-   GET /api/clusters
-   GET /api/clusters/{cluster_id}
-   POST /api/clusters/{cluster_id}/assign-person
-   POST /api/clusters/{cluster_id}/ignore
-   POST /api/faces/{face_id}/remove-from-cluster
-   POST /api/faces/{face_id}/move
-   GET /api/people
-   GET /api/people-with-clusters

Current confirmed backend file locations include:

-   backend\\app\\api\\clusters.py
-   backend\\app\\api\\faces.py
-   backend\\app\\api\\people.py
-   backend\\app\\schemas\\ui_api.py
-   backend\\app\\services\\identity\\ui_api_service.py
-   backend\\app\\main.py

The frontend scaffold already exists.

**Scope**

Build a minimal frontend with:

1.  a cluster list panel
2.  a cluster detail panel
3.  a person assignment control
4.  basic fetch/load/error handling
5.  manual refresh after assignment

**Out of Scope (DO NOT DO)**

-   no full product UI
-   no auth
-   no search
-   no routing complexity beyond what is needed
-   no global state library
-   no Redux, Zustand, or React Query
-   no advanced styling system
-   no drag-and-drop
-   no cluster merge UI yet
-   no move/remove/ignore UI yet in this milestone
-   no thumbnail/media serving work
-   no optimistic updates
-   no mobile layout work
-   no editing of people

This milestone is only the first review screen.

**Primary Outcome**

When complete, the user should be able to:

1.  open the frontend
2.  see a list of clusters from the backend
3.  click a cluster
4.  see details for that cluster
5.  see faces in that cluster
6.  select a person from a dropdown
7.  assign the cluster to that person
8.  see the UI refresh correctly afterward

**Implementation Constraints**

-   keep implementation beginner-friendly
-   prefer simple client-side React state with useState and useEffect
-   keep data flow explicit
-   do not over-engineer
-   frontend must call backend API only
-   do not duplicate backend logic in frontend

**Recommended Page Structure**

Create a single working page first.

Suggested layout:

-   left column: cluster list
-   right column: selected cluster detail

Simple structure is enough:

\+--------------------------------------------------------------+

\| Clusters \| Selected Cluster \|

\| \| \|

\| Cluster \#11 \| Cluster \#11 \|

\| Cluster \#14 \| Assigned: Unassigned \|

\| Cluster \#19 \| [person dropdown] [Assign] \|

\| \| \|

\| \| Face grid \|

\| \| [face] [face] [face] \|

\+--------------------------------------------------------------+

**Frontend Requirements**

**1. API client layer**

Create a small frontend API helper module for backend requests.

It should include functions for:

-   getClusters()
-   getCluster(clusterId)
-   getPeople()
-   assignPerson(clusterId, personId)

Use the existing backend base URL locally:

-   http://127.0.0.1:8001

Keep this simple and centralized.

**2. Types/interfaces**

Create minimal TypeScript types for:

-   cluster summary
-   cluster detail
-   face summary
-   person summary
-   list response wrapper

Use the actual API response shape from Milestone 10.1.

Important:

-   asset_sha256 is the field name, not asset_id
-   thumbnail_url may be null
-   preview_thumbnail_urls may be empty

**3. Main page behavior**

On initial load:

-   fetch clusters
-   fetch people
-   if clusters exist, auto-select the first cluster
-   fetch detail for the selected cluster

When user clicks a cluster:

-   set selected cluster
-   fetch that cluster’s detail

When user assigns a person:

-   call POST /api/clusters/{cluster_id}/assign-person
-   refresh selected cluster detail
-   refresh cluster list

**4. Cluster list panel**

Show a simple vertical list of clusters.

Each item should display at minimum:

-   cluster id
-   face count
-   assigned person name if present, otherwise “Unassigned”

Selection should be visually clear.

No thumbnails required in the list yet.

**5. Cluster detail panel**

Show:

-   cluster id
-   current assigned person or “Unassigned”
-   person dropdown
-   assign button
-   face grid

For the face grid:

-   if thumbnail_url exists, display image
-   if thumbnail_url is null, show a simple placeholder box with:
    -   face id
    -   optional small text like “No thumbnail”

Do not block progress because thumbnails are not yet available.

**6. Loading and empty states**

Handle these clearly:

-   loading clusters
-   no clusters found
-   loading cluster detail
-   no cluster selected
-   loading people
-   failed request

Keep messages simple.

**7. Error handling**

Use simple visible error messages in the page when a request fails.

Do not build a full notification/toast system.

Examples:

-   “Failed to load clusters”
-   “Failed to load cluster detail”
-   “Failed to assign person”

**Suggested File Structure**

Use project conventions if they already exist.  
If not, a structure like this is acceptable:

frontend/

src/

app/

page.tsx

components/

ClusterList.tsx

ClusterDetail.tsx

FaceGrid.tsx

PersonAssignForm.tsx

lib/

api.ts

types/

ui-api.ts

If the current frontend scaffold uses a slightly different structure, stay consistent with it.

**Implementation Notes**

-   use Next.js with React client components where needed
-   keep the first page simple
-   minimal CSS is fine
-   plain inline styles or simple CSS modules are acceptable
-   prioritize correctness over appearance

**Minimal UI Requirements**

The screen does not need to look polished, but it should be readable and functional.

Required visual behavior:

-   selected cluster is clearly highlighted
-   cluster detail is clearly separated from cluster list
-   assign form is obvious and usable
-   face tiles are visible even without thumbnails

**Testing / Verification**

Manually verify the following:

1.  frontend starts successfully
2.  page loads without crashing
3.  cluster list appears
4.  selecting a cluster loads cluster detail
5.  people dropdown appears
6.  assigning a person succeeds
7.  cluster detail refreshes after assign
8.  cluster list refreshes after assign
9.  missing thumbnails do not break the page

Please test against the running backend on port 8001.

**Deliverables**

After completion, provide:

1.  list of files added or modified
2.  exact repo-relative file paths
3.  short explanation of component structure
4.  sample description of UI behavior
5.  any setup steps required to run frontend
6.  any known limitations intentionally deferred to Milestone 10.3

**Definition of Done**

Milestone 10.2 is complete when:

-   frontend can load cluster list from API
-   user can select a cluster
-   frontend displays selected cluster detail
-   frontend displays faces in cluster
-   user can assign selected cluster to a person
-   UI refreshes correctly after assignment
-   page remains usable even when thumbnails are missing

**Do NOT add in this milestone**

Specifically do not add:

-   remove face button
-   move face button
-   ignore cluster button
-   people detail page
-   thumbnails/media backend
-   search/filter UI
-   pagination UI
-   cluster merge UI
-   unassign person button
-   editing people
-   routing between multiple pages unless absolutely necessary

Those belong in later milestones.

**Notes for Next Milestone**

Milestone 10.3 will likely add:

-   remove face from cluster
-   move face to another cluster
-   ignore cluster action
-   possibly a simple people view

This milestone should keep the UI foundation clean so those actions can be added incrementally.



1. Please add a small backend follow-up for local-development CORS only. Keep it minimal and allow the local Next.js frontend origins needed for this milestone.

2. Use an env-backed API base URL in the frontend. Default local value should be `http://127.0.0.1:8001`.

3. A desktop-first two-column layout is exactly right for 10.2. Basic graceful shrinking is fine, but no mobile-focused redesign is needed.

4. Keep styling minimal and functional. Lightweight component-level styles are acceptable as long as they stay simple and milestone-scoped.

Please proceed with that approach.

