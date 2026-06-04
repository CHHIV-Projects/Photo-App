**Milestone 10.6 — Thumbnail and Media Serving for Review UI**

**Goal**

Add real image/thumbnail support to the existing review UI so the user can see actual face images instead of placeholder boxes.

This milestone should make the current UI significantly more usable without redesigning the app.

**Context**

Completed milestones now include:

**Milestone 10.1**

-   backend API layer for clusters, faces, people

**Milestone 10.2**

-   initial review UI

**Milestone 10.3**

-   correction actions in UI:
    -   ignore cluster
    -   remove face
    -   move face

**Milestone 10.4**

-   people management UI
-   create person flow

**Milestone 10.5**

-   cluster merge UI

The application now has working review and correction workflows.  
What is missing is **visual usability**.

Currently:

-   face tiles can render placeholders
-   API returns thumbnail_url as null or empty
-   no real media-serving layer is wired for the frontend

This milestone adds a **minimal, local-only media/thumbnails layer**.

**Primary Outcome**

When complete, the user should be able to:

1.  open the review UI
2.  select a cluster
3.  see real face thumbnail images in the face grid
4.  continue using all current actions normally
5.  optionally see small preview images in the cluster list if easy and safe

The core requirement is the **face grid** in cluster detail.  
Cluster list previews are optional.

**Scope**

Build the minimum backend + frontend support needed to serve and display face thumbnails.

Required:

-   backend can return usable thumbnail/media URLs
-   frontend displays real images when available
-   placeholders remain as fallback
-   existing review/correction flows continue to work

Optional if trivial:

-   cluster list preview thumbnails

**Out of Scope (DO NOT DO)**

-   no cloud storage
-   no auth
-   no CDN
-   no image editing
-   no cropping UI
-   no full-resolution image viewer
-   no slideshow/lightbox
-   no gallery redesign
-   no upload flow changes
-   no background thumbnail generation system unless already trivial
-   no optimization overengineering
-   no advanced caching work
-   no mobile redesign

Keep this milestone practical and local.

**Important Architecture Guidance**

Use the simplest reliable source of face images already present in the project.

From the project structure, likely candidates include existing local review/exported face crops or other stored face image artifacts. The implementation should prefer **already existing face crop files** if they are available, rather than building a complex new image pipeline.

Guiding rule:

-   reuse existing face crop/review/export outputs if possible
-   only generate or derive new thumbnail paths if necessary
-   do not introduce a large new subsystem

**Backend Requirements**

**1. Provide usable thumbnail URLs in cluster detail**

Update the backend so GET /api/clusters/{cluster_id} returns usable thumbnail_url values for faces whenever a thumbnail/crop exists.

Current response shape already includes:

-   face_id
-   asset_sha256
-   thumbnail_url

Keep that shape.

Change only the population of thumbnail_url so it becomes a real browser-usable URL when possible.

Example:

{

"face_id": 13,

"asset_sha256": "c76217e9143f57af9322800a05a99d8953203ce90181498941ac106eb662f73e",

"thumbnail_url": "/media/faces/13.jpg"

}

If no image exists:

-   return null

**2. Add media serving route(s)**

Expose the thumbnail/crop files through FastAPI so the browser can request them.

Use a simple local-only approach, for example:

-   mount a static directory, or
-   add a simple file-serving endpoint

Example acceptable patterns:

-   /media/faces/{filename}
-   /api/media/faces/{face_id}

Choose the approach that best fits the existing backend and storage layout.

Important:

-   URLs returned by the API must be browser-usable from the Next.js frontend
-   keep implementation simple
-   do not expose arbitrary filesystem paths directly

**3. Source of images**

Prefer using an existing source already produced by your backend workflow.

Likely options:

-   exported face crops
-   review folder face crops
-   other existing face image artifacts

If filenames are not already deterministic enough for simple lookup, add a small mapping/helper in backend service logic.

Do not redesign storage.

**4. Optional cluster-list previews**

If it is easy and safe, update GET /api/clusters so preview_thumbnail_urls contains one or more real image URLs.

This is optional.

If it is not simple, leave cluster-list previews empty and focus only on cluster detail face tiles.

**Frontend Requirements**

**1. Face grid image rendering**

Update the existing face grid so that:

-   if thumbnail_url exists:
    -   display the image
-   if it is missing/null:
    -   keep existing placeholder behavior

This fallback is required.

**2. Image URL handling**

Use the backend base URL already configured in the frontend env-backed API setup.

If backend returns relative URLs like:

-   /media/faces/13.jpg

then frontend should resolve them correctly against the backend base URL.

Keep this logic simple and centralized if possible.

**3. Preserve existing actions**

All existing face tile actions must continue to work:

-   remove from cluster
-   move to cluster

Displaying the image must not break those controls.

**4. Optional cluster list previews**

If backend provides preview URLs, you may show a very small preview image in the cluster list.

This is optional.  
Do not delay the milestone for it.

**Backend Implementation Constraints**

-   keep local-only
-   keep URLs stable
-   avoid exposing raw absolute paths
-   do not create a complicated media domain model
-   do not introduce unnecessary DB schema changes unless absolutely required

If a tiny schema/path helper is needed, that is fine.

**Frontend Styling Guidance**

Keep styling minimal.

Requirements:

-   images should fit cleanly inside current face tiles
-   use simple object-fit behavior
-   preserve readability of face id and action controls
-   placeholders should still look reasonable when no image exists

No design overhaul.

**Suggested Technical Approach**

Recommended order:

**Backend first**

1.  identify where face crop images already live
2.  create a stable way to resolve a face id to an image file
3.  serve those files through FastAPI
4.  update cluster detail response to include real thumbnail_url
5.  optionally update cluster list previews

**Frontend second**

1.  update face grid rendering to use image URLs
2.  keep placeholder fallback
3.  verify existing actions still work

**Error Handling**

Keep media handling resilient.

If an image file cannot be resolved:

-   return thumbnail_url = null from API if detected server-side

If a returned image URL fails in browser:

-   frontend should fail gracefully
-   optional: image onError can fall back to placeholder if simple to add

Do not overbuild.

**Verification Checklist**

Manually verify:

1.  backend starts successfully
2.  cluster detail endpoint now returns real thumbnail_url values for at least some faces
3.  media URLs load in browser
4.  frontend face grid shows real images
5.  missing images still show placeholders
6.  cluster selection still works
7.  assign person still works
8.  ignore/remove/move still work
9.  merge still works
10. People view still works
11. no broken layout from image rendering

Optional:  
12\. cluster list preview images display if implemented

**Deliverables**

After completion, provide:

1.  list of files added or modified
2.  exact repo-relative file paths
3.  explanation of where thumbnail/crop images are being sourced from
4.  explanation of how media is served
5.  sample API response showing real thumbnail_url
6.  note whether cluster-list previews were implemented
7.  manual verification notes
8.  known limitations intentionally deferred

**Definition of Done**

Milestone 10.6 is complete when:

-   selected cluster face tiles show real images whenever available
-   backend returns usable thumbnail URLs
-   frontend falls back gracefully when no image is available
-   existing review and correction actions still work
-   implementation remains simple and local-only

**Do NOT add in this milestone**

-   full image viewer
-   zoom
-   slideshow
-   bulk export
-   gallery redesign
-   cloud storage
-   advanced thumbnail generation pipeline
-   image caching subsystem
-   admin media tools

**Notes for Next Milestone**

After 10.6, likely next milestones are:

1.  better people/cluster navigation
2.  search/filter improvements
3.  unignore / maintenance tools
4.  optional larger image preview

But this milestone should focus only on getting real images into the existing UI.

**Suggested Commit**

git commit -m "Milestone 10.6: Add thumbnail/media serving for face review UI"

reuse the most stable existing face-crop source already produced by your pipeline, and avoid inventing a new storage system unless absolutely necessary.


1. Use the existing `review` outputs as the only image source for 10.6. If a face crop is missing there, return `null`. Do not generate new crops on demand.

2. Use a simple static mount such as `/media/review/...` for this milestone.

3. Skip optional cluster-list previews for now and focus only on cluster detail face tiles.

4. Add a simple frontend `onError` fallback so a failed image load swaps back to the existing placeholder behavior.

5. It is acceptable that thumbnails appear only for faces that already have crops under `review`, and others remain placeholders.

Please proceed with that approach.
