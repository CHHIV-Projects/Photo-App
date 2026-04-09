**Utility Script — Generate Missing Face Crops (Review Thumbnails)**

**Goal**

Create a standalone utility script that:

-   scans all faces in the database
-   checks whether a corresponding face crop exists in the review folder
-   generates crops only for faces that are missing them

This script is for development/testing convenience and to support Milestone 10.6–10.7 thumbnail behavior.

**Context**

Current system:

-   face crops (thumbnails) are stored under a review directory
-   thumbnails are served from these existing files
-   not all faces necessarily have crops
-   cluster corrections (move/merge) do not generate new crops

This leads to:

-   some faces showing placeholders instead of images

This script fills in missing crops without re-running the entire pipeline.

**Scope**

The script should:

1.  Query all faces from the database
2.  For each face:
    -   determine if a crop image exists in review
3.  If missing:
    -   generate a face crop using existing face detection data
4.  Save the crop to the correct review structure
5.  Skip faces that already have crops

**Out of Scope (DO NOT DO)**

-   do not rerun full ingestion
-   do not rerun clustering
-   do not modify cluster assignments
-   do not build a background job system
-   do not redesign storage structure
-   do not add a new database table

Keep it a simple, repeatable script.

**Key Requirements**

**1. Input source**

Use existing database tables:

-   faces table (face_id, asset reference, bounding box)
-   asset reference (likely via asset_sha256)

You must reuse:

-   stored bounding box coordinates
-   existing image file path logic

Do NOT re-run face detection.

**2. Crop generation**

For each face:

-   load the original image from storage/vault
-   use bounding box coordinates to crop the face
-   optionally add a small padding around the face (if already standard in project)
-   resize if needed (optional — not required for this milestone)

**3. Output location**

Save crops into the existing review directory structure.

Follow existing conventions used by current review export.

If current structure is:

review/

cluster_11/

face_27.jpg

Use the same naming and format.

Important:

-   do not invent a new structure
-   match existing naming so 10.6/10.7 lookup continues to work

**4. Crop existence check**

Before generating a crop:

-   check if a crop file already exists for that face
-   if yes → skip
-   if no → generate

Because 10.7 introduced face-based lookup, you should:

-   check for existence of crop for that face_id anywhere in review folders

**5. File format**

Use:

-   .jpg as default output

**6. Logging**

Provide simple console output:

Examples:

Processing face 27...

Crop exists → skipping

Processing face 28...

Generating crop → saved to review/cluster_11/face_28.jpg

Also include summary:

Total faces: 1200

Existing crops: 950

Generated: 250

**7. Performance**

Keep it simple:

-   sequential processing is acceptable
-   no multiprocessing required

**Suggested Script Name**

Place under your scripts/utilities area, for example:

scripts/generate_missing_face_crops.py

**Suggested Function Structure**

-   load_faces()
-   crop_exists(face_id)
-   generate_crop(face)
-   save_crop(face_id, image)
-   main()

Keep functions small and readable.

**Edge Cases**

Handle gracefully:

-   missing source image → log and skip
-   invalid bounding box → log and skip
-   file write failure → log and continue

Do not crash entire script.

**Verification**

After running script:

1.  review folder should contain more face crop files
2.  previously missing thumbnails should now appear in UI
3.  no existing crops should be overwritten

**Deliverables**

Provide:

1.  script file path
2.  summary of how crop path is determined
3.  confirmation it matches existing review structure
4.  example console output
5.  instructions for running script

**Definition of Done**

Script is complete when:

-   it generates crops only for missing faces
-   it does not overwrite existing crops
-   thumbnails appear in UI for previously missing faces
-   it runs without errors on current dataset

**Notes**

This script is a development utility and may later evolve into:

-   background crop generation
-   ingestion-time crop creation
-   batch refresh after clustering updates

For now, keep it simple and reliable.

1. Do not skip faces with `cluster_id = null`. Generate them into a fallback folder such as `storage/review/unassigned`.

2. If a face already has a crop anywhere in `review`, always skip generation.

3. If a source image is missing or bbox is invalid, continue processing, log a warning, and finish with a useful summary. Only exit non-zero for a true script-level failure.

4. Please add a `--dry-run` option now so the script can report what it would generate without writing files.

5. For v1, use console summary only. No JSON summary file is needed yet.

Please proceed with that approach.
