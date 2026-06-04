**Milestone 10.1 — API Layer for UI (Cluster + Person Operations)**

**Goal**

Expose a minimal, stable FastAPI API layer to support the first UI for face cluster review and person labeling.

This milestone **does NOT build UI**.  
It only prepares backend endpoints for the upcoming frontend.

**Context**

Previous milestones completed:

-   ingestion pipeline (dedup + vault)
-   PostgreSQL database
-   EXIF extraction
-   event clustering
-   face detection + embeddings
-   face clustering
-   cluster review tools
-   cluster correction tools
-   person identity system (Milestone 9)

Milestone 9 introduced:

-   Person model
-   cluster → person assignment
-   CLI tools for labeling

This milestone builds the **API layer on top of that system**.

**Scope**

Build FastAPI endpoints to support:

-   cluster listing (for review)
-   cluster detail view (faces in cluster)
-   person listing
-   assign cluster → person
-   remove face from cluster
-   move face between clusters
-   ignore cluster
-   list people with assigned clusters

**Out of Scope (DO NOT DO)**

-   no frontend work
-   no UI components
-   no authentication
-   no search or filtering beyond basics
-   no pagination complexity beyond simple limit/offset
-   no changes to clustering logic
-   no database redesign
-   no background workers or async jobs
-   no websocket/live updates

**Architecture Requirements**

Follow existing backend structure:

backend/app/

-   api/
-   models/
-   schemas/
-   services/

Rules:

-   API layer must be **thin**
-   business logic belongs in **services**
-   reuse existing logic from scripts wherever possible
-   do NOT duplicate logic between scripts and API

If logic exists only in scripts, extract it into reusable service functions.

**Required Service Functions**

Ensure the following callable functions exist (create or refactor as needed):

-   list_clusters_for_review(...)
-   get_cluster_detail(cluster_id)
-   list_people()
-   assign_cluster_to_person(cluster_id, person_id)
-   remove_face_from_cluster(face_id)
-   move_face_to_cluster(face_id, target_cluster_id)
-   ignore_cluster(cluster_id)
-   list_people_with_clusters()

These should use existing DB/session patterns.

**API Endpoints**

Prefix all endpoints with:

/api

**1. GET /api/clusters**

Return clusters for review.

Response (per item):

-   cluster_id
-   face_count
-   person_id (nullable)
-   person_name (nullable)
-   is_ignored
-   preview_thumbnail_urls (if available)

Optional query params (keep simple):

-   include_ignored=false (default)
-   limit
-   offset

**2. GET /api/clusters/{cluster_id}**

Return full cluster detail.

Response:

-   cluster_id
-   person_id
-   person_name
-   is_ignored
-   faces:
    -   face_id
    -   asset_id
    -   thumbnail_url (if available)

Keep response UI-friendly.

**3. POST /api/clusters/{cluster_id}/assign-person**

Request:

{

"person_id": 1

}

Response:

{

"success": true

}

**4. POST /api/clusters/{cluster_id}/ignore**

Response:

{

"success": true

}

**5. POST /api/faces/{face_id}/remove-from-cluster**

Remove a face from its cluster.

Response:

{

"success": true

}

**6. POST /api/faces/{face_id}/move**

Request:

{

"target_cluster_id": 10

}

Response:

{

"success": true

}

**7. GET /api/people**

Return:

-   person_id
-   display_name

**8. GET /api/people-with-clusters**

Return:

[

{

"person_id": 1,

"display_name": "Alice",

"clusters": [

{

"cluster_id": 10,

"face_count": 7

}

]

}

]

Keep structure simple.

**Schemas (Pydantic)**

Create minimal schemas:

-   ClusterSummary
-   ClusterDetail
-   FaceSummary
-   PersonSummary
-   AssignPersonRequest
-   MoveFaceRequest

Keep fields explicit and small.

**Error Handling**

Handle basic cases:

-   cluster not found → 404
-   person not found → 404
-   face not found → 404
-   invalid cluster move → 400 or 404

Keep error messages simple and clear.

**Media / Thumbnails**

If thumbnails already exist:

-   return usable URL paths

If not:

-   return placeholder or existing file path
-   DO NOT build full media system in this milestone

**Implementation Notes**

-   follow existing SQLAlchemy session patterns
-   keep code modular and beginner-friendly
-   do not introduce new abstractions unless necessary
-   keep naming consistent with existing services

**Testing / Verification**

Manually verify:

-   GET /api/clusters returns data
-   GET /api/clusters/{id} returns faces
-   GET /api/people returns people
-   assign-person updates cluster correctly
-   remove-from-cluster works
-   move face works
-   ignore cluster works
-   people-with-clusters returns correct mapping

**Deliverables**

After completion, provide:

1.  list of files added or modified
2.  list of new service functions
3.  list of API routes
4.  sample responses for each endpoint
5.  any small refactors made
6.  notes for next milestone (UI)

**Definition of Done**

-   all endpoints implemented and working
-   endpoints call reusable service logic
-   responses are UI-ready
-   manual testing completed
-   no frontend work started

**Notes for Next Milestone**

Milestone 10.2 will build:

-   Next.js UI
-   cluster list + detail view
-   person assignment UI
-   basic correction actions

This API must support that UI cleanly.

Milestone 10 implementation decisions
1. Route prefix

Keep the existing health route as-is.

Leave current health route untouched
Add all new UI-related routers under /api/*

Result:

existing health route stays wherever it already is
new routes go under:
/api/clusters
/api/faces
/api/people

Reason:

avoids unnecessary churn
keeps milestone scoped to the new API layer only
2. Thumbnail URL behavior

Use null placeholders for now if there is no reliable existing thumbnail/media URL path already available.

Rules:

if a clean, already-supported URL can be produced safely, return it
otherwise return null
do not invent brittle filesystem-derived browser paths
do not build media serving in this milestone

So:

preview_thumbnail_urls: may be empty list or list of nullable values, but prefer returning only valid URLs
thumbnail_url: return null when unavailable

Reason:

this milestone is API structure, not media plumbing
avoids fake paths that the frontend cannot use
3. Cluster detail asset field

Use asset_sha256 as the field name, not asset_id.

Since the relationship is based on SHA and not a numeric asset id, the API should reflect reality.

So in face objects return:

face_id
asset_sha256
thumbnail_url

Reason:

clearer and accurate
avoids misleading the frontend
4. People-with-clusters payload shape

Use an object wrapper:

{
  "count": 2,
  "items": [
    {
      "person_id": 1,
      "display_name": "Alice",
      "clusters": [
        {
          "cluster_id": 10,
          "face_count": 7
        }
      ]
    }
  ]
}

Reason:

more extensible
consistent with list-style endpoints
easier to add metadata later

Please also use the same wrapper style for GET /api/people and GET /api/clusters.

5. Default pagination

Use:

limit=50
offset=0
hard max limit=500

That proposal is good.

6. Assign-person semantics

Overwrite existing person_id unconditionally.

Behavior:

if cluster is unlabeled, assign it
if cluster is already assigned, replace the assignment with the new person
return success

Do not reject reassignment in this milestone.

Reason:

simpler for UI
supports correction workflow
avoids adding extra friction for a personal/local tool

If practical, log or clearly report previous → new assignment in service-level notes or debug output, but no special API complexity is needed.

7. Ignore endpoint semantics

Yes — make it one-way only for this milestone.

Behavior:

POST /api/clusters/{cluster_id}/ignore sets ignored = true
no toggle behavior
unignore remains deferred / separate

That matches scope.

8. Error format

Use default FastAPI error shape for now.

So standard HTTPException(detail="...") is acceptable.

Do not build a custom error envelope in this milestone.

Reason:

lower complexity
faster to implement
fine for early internal UI work
Final confirmed choices

Use these exact choices:

keep existing health route unchanged
add new routes under /api/*
thumbnail URLs: real URL if already available, otherwise null
use asset_sha256, not asset_id
list payloads should use object wrapper: { "count": X, "items": [...] }
pagination defaults: limit=50, offset=0, hard max 500
assign-person should overwrite existing assignment
ignore is one-way only
use default FastAPI error responses

You can send that directly to coder.