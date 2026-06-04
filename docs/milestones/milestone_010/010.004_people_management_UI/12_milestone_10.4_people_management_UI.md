**Milestone 10.4 — People Management UI**

**Goal**

Add a simple People Management UI to the existing frontend so the user can:

-   view all people
-   view clusters assigned to each person
-   create a new person
-   use the existing person-labeling system more efficiently

This milestone should **not** redesign the app.  
It should extend the current UI in a small, clean, beginner-friendly way.

**Context**

Completed work so far:

**Milestone 10.1**

Backend API layer exists for:

-   GET /api/clusters
-   GET /api/clusters/{cluster_id}
-   POST /api/clusters/{cluster_id}/assign-person
-   POST /api/clusters/{cluster_id}/ignore
-   POST /api/faces/{face_id}/remove-from-cluster
-   POST /api/faces/{face_id}/move
-   GET /api/people
-   GET /api/people-with-clusters

**Milestone 10.2**

Frontend review screen exists for:

-   cluster list
-   cluster detail
-   face grid
-   assign-person dropdown

**Milestone 10.3**

Frontend correction actions now exist for:

-   ignore cluster
-   remove face from cluster
-   move face to another cluster

The review UI is now functional.

This milestone adds a **simple people workflow** on top of that foundation.

**Scope**

Build a basic people view and person creation flow.

The UI should support:

1.  viewing people
2.  viewing clusters assigned to each person
3.  creating a new person
4.  making newly created people available in the existing assignment workflow

**Out of Scope (DO NOT DO)**

-   no rename person yet
-   no delete person yet
-   no merge people yet
-   no search/filter UI yet
-   no cluster merge UI
-   no advanced navigation redesign
-   no thumbnails/media work
-   no inline editing
-   no family/group relationships
-   no drag-and-drop
-   no people detail page with routing complexity unless absolutely necessary
-   no auth
-   no backend redesign beyond what is required for a create-person API endpoint

Keep this milestone narrow.

**Important Architecture Note**

Milestone 9 already created the backend person identity system and CLI creation flow.

Milestone 10.1 added people list endpoints, but **did not include create-person API**.

So Milestone 10.4 may require a **small backend follow-up**:

-   add a minimal API endpoint for creating a person

That backend change is allowed in this milestone because it directly supports the people UI.

Do not expand beyond that.

**Required Outcome**

When this milestone is complete, the user should be able to:

1.  open the frontend
2.  switch to a People view
3.  see all people returned by the backend
4.  see clusters assigned to each person
5.  create a new person from the UI
6.  return to the review screen and assign clusters to the newly created person

**Backend Follow-up (Allowed in 10.4)**

If not already available, add:

**POST /api/people**

Request:

{

"display_name": "Alice Henderson"

}

Response:

{

"success": true,

"person": {

"person_id": 8,

"display_name": "Alice Henderson"

}

}

Behavior:

-   create a person using existing person service logic
-   reject duplicate names clearly
-   keep error handling simple
-   do not add notes field editing in this milestone unless already trivial

If there is already a reusable service function from Milestone 9, reuse it.

Do not duplicate logic.

**Frontend Scope Details**

**1. Add a simple view switcher**

Add a small top-level view selector so the user can switch between:

-   Review
-   People

This can be:

-   two buttons
-   simple tabs
-   another minimal toggle

Keep it simple.

Do not build a full navigation system.

**2. Preserve existing Review view**

The current review page and its behavior should continue to work exactly as before.

Do not break:

-   cluster selection
-   assign person
-   ignore/remove/move actions

The People view should be added alongside the current review view, not replace it.

**3. People view**

Add a simple People panel/page section that shows:

For each person:

-   display name
-   person id (small secondary text is fine)
-   assigned clusters
-   cluster count
-   optional face counts per cluster if already available from API

Use the existing endpoint:

-   GET /api/people-with-clusters

Suggested simple layout:

People

\-------------------------------------------------

[ Create Person form ]

Alice Henderson

Person \#4

Clusters: 3

\- Cluster \#1 (4 faces)

\- Cluster \#7 (6 faces)

\- Cluster \#19 (2 faces)

Bob Henderson

Person \#5

Clusters: 1

\- Cluster \#21 (8 faces)

This is enough.

**4. Create Person form**

Add a simple form at the top of the People view.

Fields:

-   display name

Controls:

-   text input
-   Create button

Behavior:

-   call POST /api/people
-   on success:
    -   refresh people list
    -   clear input
    -   ideally refresh people data used by the Review view assignment dropdown too

Behavior on duplicate or error:

-   show simple readable error message

Do not add advanced validation beyond basics.

Recommended simple validation:

-   trim whitespace
-   block empty names
-   allow backend to enforce uniqueness

**API Client Updates**

Extend frontend API helper with:

-   getPeopleWithClusters()
-   createPerson(displayName)

Keep using the existing env-backed API base URL.

**TypeScript Types**

Add any missing types needed for:

-   create person request/response
-   people-with-clusters response
-   person with assigned clusters

Keep types aligned with real backend payloads.

**State Management Rules**

Keep this milestone consistent with previous ones:

-   use useState
-   use useEffect
-   explicit refresh after mutations

Do not add:

-   Redux
-   Zustand
-   React Query
-   complex app-wide state systems

If useful, keep top-level state in the existing page.tsx.

**Refresh Requirements**

After successful person creation:

-   refresh People view list
-   refresh any people list used in the Review view assignment dropdown

This is important so the new person is immediately assignable.

Keep the implementation explicit and easy to follow.

**Error Handling**

Keep errors simple and visible.

Examples:

-   Failed to create person
-   Person name is required
-   A person with that name already exists

If backend returns useful detail, show it in a simple readable form.

No toast system needed.

**Loading States**

Handle basic loading states:

-   loading people
-   creating person
-   failed to load people

Keep them lightweight.

**Styling / UI Requirements**

Keep styling simple and consistent with 10.2 and 10.3.

Requirements:

-   clear way to switch between Review and People views
-   readable People list/cards/sections
-   create-person form should be obvious
-   no design-system work
-   no major styling refactor

A little CSS is fine, but keep it minimal.

**Suggested File/Component Changes**

Use existing project structure and conventions.  
Possible additions/updates:

-   page.tsx
    -   add simple view switching
    -   manage people view loading/refresh if appropriate
-   api.ts
    -   add people-with-clusters and create-person calls
-   ui-api.ts
    -   add create-person and people-with-clusters types if needed
-   new component(s), for example:
    -   PeopleView.tsx
    -   CreatePersonForm.tsx

Only add components if they keep the code cleaner.  
Do not refactor everything.

**Verification Checklist**

Manually verify:

1.  frontend still loads successfully
2.  Review view still works
3.  view switching works
4.  People view loads existing people
5.  assigned clusters display under each person
6.  create person works
7.  duplicate person creation shows a clear error
8.  new person appears in People view after creation
9.  new person appears in Review assignment dropdown after refresh
10. existing 10.3 correction actions still work

**Deliverables**

After completion, provide:

1.  list of files added or modified
2.  exact repo-relative file paths
3.  note whether backend create-person endpoint was added
4.  short summary of People view structure
5.  short summary of create-person flow
6.  manual verification notes
7.  known limitations intentionally deferred to a later milestone

**Definition of Done**

Milestone 10.4 is complete when:

-   user can switch between Review and People views
-   user can see people and their assigned clusters
-   user can create a new person from the UI
-   newly created person becomes available for cluster assignment
-   existing Review functionality remains intact

**Do NOT add in this milestone**

Specifically do not add:

-   rename person
-   delete person
-   merge people
-   search/filter people
-   cluster merge UI
-   advanced routing
-   media/thumbnails work
-   person notes editing
-   family/grouping features
-   unignore or admin maintenance screens

Those belong later.

**Notes for Next Milestone**

Milestone 10.5 will likely be one of:

1.  cluster merge UI
2.  real thumbnail/media serving
3.  better people/cluster navigation improvements

Keep 10.4 focused on basic people management only.


1. Keep Review as the default view and People as the secondary tab.

2. After successful person creation, refresh the Review people list immediately even if the user is still on the People view, so the new person is ready when switching back.

3. Use the exact `POST /api/people` success response shape:
   {
   "success": true,
   "person": {
   "person_id": ...,
   "display_name": "..."
   }
   }

4. Duplicate-name behavior mapping to HTTP 400 with backend detail text is acceptable and consistent with the current API style.

5. Keep the existing alphabetical-by-display-name ordering as-is for the People view.

Please proceed with that approach.
