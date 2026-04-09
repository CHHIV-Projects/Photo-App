Build Milestone 9.5: Face cluster correction tools.

Goal:

Add practical correction tools so a human can fix imperfect face clustering before or during person labeling.

Context:

The current face clustering system is working, but real-world review has shown expected issues:

\- some clusters are low-quality or junk

\- some clusters contain one or more incorrect faces

\- the same person may appear in multiple clusters

We need correction tools before relying heavily on person labeling.

Scope:

\- local only

\- script-based only

\- no UI yet

\- no retraining yet

\- do not change face detection or embedding generation logic

\- keep this milestone focused on manual correction workflows

Required behavior:

1\. Face-level cluster removal

Create a script to remove a specific face from its current cluster.

Suggested file:

\- backend/scripts/unassign_face_from_cluster.py

Behavior:

\- input: face_id

\- set that Face.cluster_id to null

\- do not delete the face record

\- print summary

2\. Face-level cluster reassignment

Create a script to move a specific face from one cluster to another.

Suggested file:

\- backend/scripts/move_face_to_cluster.py

Behavior:

\- input: face_id and target_cluster_id

\- validate both exist

\- update Face.cluster_id to target_cluster_id

\- print summary

3\. Cluster merge

Create a script to merge one cluster into another.

Suggested file:

\- backend/scripts/merge_face_clusters.py

Behavior:

\- input: source_cluster_id, target_cluster_id

\- move all Face rows from source cluster to target cluster

\- if FaceCluster has person_id and target cluster does not, preserve the target cluster as canonical

\- after moving all faces:

\- delete the now-empty source cluster

\- or mark it inactive if you introduce an active flag

\- print summary including number of faces moved

Preferred for this milestone:

\- delete the empty source cluster after merge

\- keep logic simple

4\. Cluster ignore flag

Update FaceCluster model:

\- add is_ignored boolean, default False

Create a script:

\- backend/scripts/ignore_face_cluster.py

Behavior:

\- input: cluster_id

\- mark cluster as ignored

\- ignored clusters should remain in DB but be clearly excluded from normal labeling workflows

Optional companion:

\- unignore_face_cluster.py

5\. Review/listing updates

Update or extend review/listing scripts so they clearly support correction workflows.

Requirements:

\- list_clusters_for_labeling.py should exclude ignored clusters by default

\- optionally include a flag to show ignored clusters

\- check_people_and_clusters.py should report:

\- labeled clusters

\- unlabeled clusters

\- ignored clusters

6\. Verification script support

If useful, add or update a checker script so we can inspect:

\- face_id

\- cluster_id

\- person_id if any

\- is_ignored

7\. Safety rules

\- do not delete faces

\- do not delete assets

\- only modify cluster assignments and cluster metadata

\- fail clearly on invalid IDs

\- keep operations explicit and reversible where practical

8\. Implementation notes

\- keep code modular and beginner-friendly

\- use existing SQLAlchemy session patterns

\- do not add UI

\- do not add automatic reclustering

\- do not add bulk person merge logic yet

9\. What to explain after coding

1\. what files were added or changed

2\. how to remove one bad face from a cluster

3\. how to move a face to another cluster

4\. how to merge clusters

5\. how ignored clusters behave

6\. how the listing/check scripts changed
