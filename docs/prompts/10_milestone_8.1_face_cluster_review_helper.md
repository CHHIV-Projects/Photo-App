Build a small review helper milestone before practical Person labeling.

Goal:

Add a visual review tool for face clusters so a human can inspect the faces inside a cluster before assigning that cluster to a Person.

Reason:

The current person-labeling scripts are structurally correct, but practical labeling requires a way to see what faces are inside each cluster. We should not assign clusters to people blindly based only on cluster IDs.

Required behavior:

1\. Create a review script

Create:

\- backend/scripts/review_face_cluster.py

2\. Inputs

The script should accept:

\- a required cluster_id

\- an optional output folder path

If no output folder is provided, default to something like:

\- storage/review/cluster_\<id\>/

3\. What the script should do

For the requested cluster_id:

\- load all Face rows with that cluster_id

\- join to Asset so the script can access vault_path, original_filename, and original_source_path

\- crop each face from the original vault image using stored bbox coordinates

\- save each cropped face image to the review output folder

4\. Saved output

Each saved crop should have a readable filename that includes useful identifiers, for example:

\- face_\<face_id\>__asset_\<sha256_prefix\>__\<original_filename\>.jpg

Also create a small manifest file in the same review folder, for example:

\- manifest.json

The manifest should include for each cropped face:

\- face_id

\- cluster_id

\- asset_sha256

\- vault_path

\- original_filename

\- original_source_path

\- bbox_x

\- bbox_y

\- bbox_width

\- bbox_height

\- confidence_score

5\. Behavior

\- do not modify the database

\- do not assign labels

\- do not recluster

\- fail clearly if cluster_id does not exist

\- skip invalid crops and record them in the manifest or summary

\- keep code simple and beginner-friendly

6\. Optional convenience

If easy, also print a summary:

\- cluster_id

\- total faces found

\- crops saved

\- failures

7\. Project structure

Suggested file:

\- backend/scripts/review_face_cluster.py

What to explain after coding:

1\. how to run the script

2\. where the output folder is created

3\. what files are written

4\. how this review step fits before person labeling

1. Cluster exists but has 0 faces
Treat it as an error and exit non-zero.

Reason:
- a cluster with no faces is not useful for review
- better to surface it clearly than create misleading empty review output

2. Output image format
Always save review crops as .jpg.

Reason:
- simpler and more consistent for quick human review
- avoids format-specific issues
- this is a review artifact, not canonical storage

3. Existing output folder behavior
Overwrite existing crops and manifest.

Reason:
- review output should reflect the current cluster contents
- avoids stale or duplicate files from earlier runs

4. Crop safety
Clamp to image bounds and save if still valid.

Reason:
- some boxes may slightly exceed bounds after scaling
- valid clamped crops should still be reviewable
- only skip if the crop becomes invalid after clamping

5. Invalid crops / failures
Yes, do both:
- include them in manifest.json under a failures section
- print them in the CLI summary

6. Filename style
Yes, sanitize original_filename to filesystem-safe text while preserving readability.

7. Output root default
Yes, confirm default output should be under project storage as:
- storage/review/cluster_<id>/