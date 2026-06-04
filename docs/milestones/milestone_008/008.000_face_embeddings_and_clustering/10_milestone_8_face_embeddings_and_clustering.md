Build Milestone 8: Face embeddings and clustering (person grouping).

Goal:

Group detected faces into clusters representing the same individual, without assigning names.

Scope:

\- use local processing only

\- do not build UI

\- do not assign identities/names

\- do not modify existing ingestion or face detection logic

\- operate only on existing Face records

Library choice:

Use DeepFace for embeddings (facial feature vectors).

\- backend: CPU-only mode is fine

\- use a lightweight model (e.g., Facenet or VGG-Face default)

Required behavior:

1\. Database changes

Create a new table: FaceCluster

Fields:

\- id (primary key)

\- created_at_utc

Update Face table:

\- add cluster_id (nullable foreign key to FaceCluster.id)

Notes:

\- no schema migrations required (use reset approach for now)

2\. Embedding generation

For each Face:

\- load the source image from vault_path

\- crop the face using bbox coordinates

\- generate embedding vector using DeepFace

Behavior:

\- skip faces where crop fails or invalid

\- collect failures but do not crash

\- do not store embeddings in DB for this milestone (in-memory only)

3\. Clustering

Group embeddings into clusters:

\- use cosine similarity or Euclidean distance

\- simple approach:

\- iterate through faces

\- assign to an existing cluster if similarity \> threshold

\- otherwise create new cluster

Default:

\- similarity threshold configurable (e.g., 0.7)

Behavior:

\- deterministic grouping for same dataset

\- no need for advanced clustering algorithm yet

4\. Persistence

Before clustering:

\- clear all existing FaceCluster rows

\- reset Face.cluster_id to null

After clustering:

\- create FaceCluster rows

\- assign cluster_id to each Face

5\. Runner script

Create:

\- backend/scripts/run_face_clustering.py

Output:

\- total faces processed

\- clusters created

\- average cluster size

\- largest cluster size

\- failures

6\. Verification

Create:

\- backend/scripts/check_face_clusters.py

Output:

\- total clusters

\- faces per cluster (sample)

\- sample cluster with multiple faces

\- confirm each face has cluster_id

7\. Project structure

Suggested:

\- backend/app/models/face_cluster.py

\- backend/app/services/vision/face_embedder.py

\- backend/app/services/vision/face_clusterer.py

\- backend/scripts/run_face_clustering.py

\- backend/scripts/check_face_clusters.py

8\. Configuration

Add to config.py:

\- FACE_CLUSTER_SIMILARITY_THRESHOLD (default \~0.7)

\- FACE_EMBEDDING_MODEL (default DeepFace standard)

9\. What to explain after coding

1\. embedding model used

2\. similarity metric used

3\. clustering approach

4\. threshold behavior

5\. sample cluster output

1. Embedding model default
Use FaceNet as the default for FACE_EMBEDDING_MODEL.

Reason:
- good balance of quality and practicality
- widely used for face embeddings
- a better fit for clustering than relying on a vague library default

2. Similarity rule definition
Implement true cosine similarity, where higher is better.

Use:
- cosine similarity
- default threshold = 0.7

Reason:
- easier to reason about
- matches the prompt wording
- more intuitive for future tuning

3. Face crop preprocessing
Add a small margin around the stored bbox before embedding.

Use default:
- 10% margin

Reason:
- helps include a bit more facial context
- usually improves embedding stability
- still keeps the crop tight enough to focus on the face

4. Invalid crop behavior
Yes, confirm that invalid crops should be skipped and recorded as failures.

Reason:
- invalid crops should not produce embeddings
- better to discard bad inputs than contaminate clustering

5. Dependency update
Yes, it is okay to add deepface and its dependencies to requirements.txt for this milestone.

6. Cluster-id reset scope
Yes, confirm rerun behavior should only:
- clear FaceCluster rows
- reset Face.cluster_id to null

Do not rerun face detection automatically as part of clustering.