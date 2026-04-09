Build Milestone 7: Face detection and face bounding box storage.

Goal:

Detect faces in images stored in the Vault and store their bounding box coordinates in the database for future use.

Scope:

\- use local processing only (no cloud APIs)

\- do not implement face recognition or identity matching

\- do not cluster faces

\- do not build UI

\- focus only on detection and storage

Library choice:

Use a fast and lightweight face detector suitable for CPU:

\- preferred: OpenCV YuNet (cv2 face detection)

\- acceptable alternative: SCRFD (via insightface)

\- avoid heavy/slow models like DeepFace for this milestone

Required behavior:

1\. Database changes

Create a new Face model/table with fields:

\- id

\- asset_sha256 (foreign key to Asset.sha256)

\- bbox_x

\- bbox_y

\- bbox_width

\- bbox_height

\- confidence_score

\- created_at_utc

Notes:

\- bounding box coordinates should be pixel-based

\- assume origin (0,0) is top-left corner

\- store coordinates exactly as returned or normalized consistently

2\. Face detection service

Create a service that:

\- loads assets from the database

\- reads image files from the Vault using vault_path

\- runs face detection on each image

\- returns detected face bounding boxes

Behavior:

\- skip non-image files

\- skip files that cannot be opened

\- allow multiple faces per image

\- do not crash on errors; collect failure reasons

3\. Persistence

For each detected face:

\- insert a record into the Face table

Behavior:

\- allow reruns for development

\- for this milestone, it is acceptable to:

\- clear all existing Face records before inserting new ones

\- do not deduplicate faces yet

4\. Runner script

Create:

\- backend/scripts/run_face_detection.py

It should:

\- iterate over assets

\- run detection

\- store face records

\- print summary:

\- total assets processed

\- total faces detected

\- assets with faces

\- assets without faces

\- failures

5\. Verification

Create:

\- backend/scripts/check_faces_in_db.py

It should:

\- print total face records

\- print number of assets with faces

\- show sample records:

\- asset_sha256

\- bbox coordinates

\- confidence

6\. Performance considerations

\- process sequentially for now

\- do not add multiprocessing yet

\- keep code simple and stable

\- make detector initialization efficient (not per-image if possible)

7\. Project structure

Suggested locations:

\- backend/app/models/face.py

\- backend/app/services/vision/face_detector.py

\- backend/scripts/run_face_detection.py

\- backend/scripts/check_faces_in_db.py

8\. What to explain after coding

1\. which library was used and why

2\. how bounding boxes are defined

3\. how to run detection

4\. sample output

5\. any limitations observed

Face detection performance requirement:

Before running face detection, resize images so the longest dimension is approximately 800–1200 pixels while maintaining aspect ratio.

Run face detection on the resized image.

After detection, scale bounding box coordinates back to the original image dimensions before storing them in the database.

All stored bounding boxes must correspond to original-resolution coordinates.

1. Detector model file source
Do not vendor the YuNet ONNX model into the repo.

Use a local path via config/environment setting and fail with a clear message if the model file is missing.

Reason:
- keeps the repo lighter
- avoids committing model binaries
- gives flexibility later for NAS/server deployment

2. Dependency choice
Yes, it is okay to add opencv-python-headless to requirements.txt for this server-side milestone.

3. Bounding box storage type
Store bounding box fields as integers after scaling back to original resolution.

Reason:
- simpler and cleaner for database storage
- easier for future UI overlays
- face boxes are pixel coordinates in the original image space

4. Confidence threshold
Yes, apply a default detection confidence threshold and make it configurable in config.py.

Use default:
- 0.7

5. Rerun behavior
Yes, confirm we should clear all Face rows on each run for this milestone.

Reason:
- keeps development behavior simple
- matches the rebuild-style approach used for event clustering
- we can make reruns more incremental later