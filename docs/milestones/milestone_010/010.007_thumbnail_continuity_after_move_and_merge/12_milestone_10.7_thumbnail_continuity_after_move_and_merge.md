**Milestone 10.7 — Thumbnail Continuity After Move and Merge**

**Goal**

Preserve thumbnail visibility for faces after cluster correction actions, especially:

-   move face to another cluster
-   merge one cluster into another

This milestone should fix the current limitation where database changes succeed but thumbnails may disappear because review crop lookup is tied to the current cluster folder.

**Context**

Milestone 10.6 added local thumbnail/media serving by reusing existing review crops.

Current behavior:

-   thumbnails are sourced from existing review output folders
-   lookup currently depends on cluster-folder-based paths
-   after move or merge:
    -   database data updates correctly
    -   existing crop files remain in their original review folder
    -   thumbnails may disappear
    -   UI falls back to placeholder

This is expected with the current implementation, but it reduces usability during correction workflows.

This milestone should improve thumbnail continuity without redesigning the whole media system.

**Primary Outcome**

When complete, the user should be able to:

1.  move a face to another cluster
2.  merge one cluster into another
3.  continue seeing thumbnails for affected faces whenever an existing review crop already exists somewhere in the review outputs

The goal is continuity of display, not full crop regeneration.

**Scope**

Fix thumbnail lookup so existing thumbnails remain usable after move/merge.

Preferred approach:

-   resolve thumbnails by **face identity** rather than by current cluster folder only

This milestone should reuse already existing review crops and avoid creating a large new media subsystem.

**Out of Scope (DO NOT DO)**

-   no on-demand crop generation
-   no full crop regeneration pipeline
-   no file copying/moving during move/merge unless absolutely required
-   no thumbnail database table
-   no storage redesign
-   no full gallery/media subsystem
-   no cloud/media hosting work
-   no search/filter changes
-   no frontend redesign

Keep this milestone narrow and practical.

**Recommended Technical Direction**

Prefer this strategy:

**Face-based thumbnail resolution**

Instead of only looking in the current cluster review folder, resolve a face thumbnail by finding an existing crop file for that face_id anywhere in the known review outputs.

In other words:

-   a thumbnail belongs to the face, not to the current cluster assignment
-   if a crop already exists somewhere for that face, keep using it
-   cluster move/merge should not cause thumbnail disappearance just because the DB cluster id changed

This is the preferred solution for 10.7.

**Backend Requirements**

**1. Update thumbnail lookup logic**

Modify the backend thumbnail-resolution logic used by cluster detail responses.

Current problem:

-   lookup depends on current cluster folder path

Required improvement:

-   locate crop by face_id across the available review crop files
-   return a stable browser-usable media URL if found
-   return null if no crop exists anywhere

Keep the existing API response shape:

-   face_id
-   asset_sha256
-   thumbnail_url

Do not change payload shape unless absolutely necessary.

**2. Keep existing media serving approach**

Keep the 10.6 local media-serving approach in place.

Do not redesign the media URL strategy if it already works.

If media URLs currently use a static mount such as /media/review/..., continue using that.

**3. Thumbnail resolution helper**

If useful, add a small helper/service function that:

-   accepts face_id
-   finds the first matching review crop file for that face
-   returns a media URL or null

Keep it simple and readable.

Do not overengineer indexing unless truly needed.

**4. Optional lightweight optimization**

If scanning review folders repeatedly is too slow, a small in-memory mapping/cache built at startup or on first use is acceptable.

Examples:

-   face_id → relative media path

This is optional and should remain lightweight.

Do not build a persistent cache/database layer.

**Frontend Requirements**

**1. No major frontend redesign**

The frontend should need little or no structural change.

The main expected result is:

-   after move/merge refreshes, affected faces continue showing images because backend now returns better thumbnail_url values

**2. Preserve existing fallback behavior**

Keep current image fallback behavior:

-   if image loads, show it
-   if image missing or fails, show placeholder

No redesign needed.

**Behavior Requirements**

**After move face**

-   moved face should still show thumbnail if an existing crop already exists anywhere in review outputs

**After merge**

-   faces now displayed under target cluster should still show thumbnails if crops already exist anywhere in review outputs

**If no crop exists at all**

-   placeholder is still correct behavior

**Validation Rules**

Do not invent thumbnails that do not exist.

If no crop file can be found:

-   return null
-   frontend placeholder remains correct

This milestone is about continuity of existing crops, not generating missing ones.

**Verification Checklist**

Manually verify:

1.  review UI still loads normally
2.  existing thumbnails still display
3.  move face works
4.  moved face still shows thumbnail afterward when a crop existed before
5.  merge cluster works
6.  faces in merged target cluster still show thumbnails when crops existed before
7.  remove face still works
8.  ignore cluster still works
9.  People view still works
10. placeholders still appear for faces with no crop anywhere

Please use real move/merge test cases that previously caused thumbnail disappearance.

**Deliverables**

After completion, provide:

1.  list of files added or modified
2.  exact repo-relative file paths
3.  short explanation of the new thumbnail lookup strategy
4.  note whether any lightweight cache/index was added
5.  sample before/after behavior description for move/merge
6.  manual verification notes
7.  known limitations intentionally deferred

**Definition of Done**

Milestone 10.7 is complete when:

-   move/merge no longer cause thumbnail disappearance for faces that already have existing review crops
-   backend still returns null for truly missing crops
-   frontend continues working without redesign
-   implementation remains small and local-only

**Do NOT add in this milestone**

-   crop regeneration
-   moving/copying files during corrections
-   media database tables
-   full media indexing system
-   gallery redesign
-   search/filter changes
-   full-resolution viewer

Those are later concerns.

**Notes for Next Milestone**

After 10.7, likely next candidates are:

1.  unignore / maintenance tools
2.  better navigation between people and clusters
3.  optional larger preview view
4.  search/filter support

But 10.7 should focus only on preserving existing thumbnails across correction actions.

**Suggested Commit**

git commit -m "Milestone 10.7: Preserve thumbnails after move and merge using face-based lookup"


1. Include `.jpg`, `.jpeg`, and `.png` in face lookup for this milestone.

2. If multiple files match the same `face_id`, use a deterministic rule: most recently modified file wins.

3. Use a lightweight in-memory index built on first use, mapping `face_id -> media path`. Keep it simple and local-only.

4. Keep returned URLs in the existing `/media/review/...` format even if the matched file is found in a different cluster folder than the face’s current cluster.

5. If the `review` source folder is absent or unavailable, return `thumbnail_url: null` gracefully and do not fail the cluster API response.

Please proceed with that approach.
