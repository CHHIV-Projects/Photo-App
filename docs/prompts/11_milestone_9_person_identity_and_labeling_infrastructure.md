Build Milestone 9: Person identity and labeling infrastructure.

Goal:

Create the first person-labeling layer so unlabeled face clusters can be assigned to known people.

Scope:

\- local only

\- no UI yet

\- no retraining yet

\- no relationship/family grouping yet

\- do not change face detection or clustering behavior

\- build only the identity storage and assignment layer

Required behavior:

1\. Database changes

Create a new Person model/table with fields:

\- id

\- display_name (unique)

\- notes (nullable)

\- created_at_utc

Update FaceCluster:

\- add nullable person_id foreign key to Person.id

Notes:

\- a cluster may remain unlabeled

\- a person may have multiple clusters

\- for this milestone, clusters belong to at most one person

2\. Person service

Create a small service that can:

\- create a person by display_name

\- list people

\- assign one or more cluster_ids to a person

\- unassign a cluster from a person if needed

Behavior:

\- prevent duplicate person names

\- fail clearly if cluster_id or person_id does not exist

\- keep logic simple and explicit

3\. Scripts

Create scripts like:

\- backend/scripts/create_person.py

Behavior:

\- create a person from CLI input or argument

\- print created person record

\- backend/scripts/assign_clusters_to_person.py

Behavior:

\- accept person name or person id

\- accept one or more cluster ids

\- assign those clusters to the person

\- print summary

\- backend/scripts/check_people_and_clusters.py

Behavior:

\- print total people

\- print all people

\- print clusters assigned per person

\- print clusters still unlabeled

\- show sample unlabeled clusters

4\. Optional helper for review

If helpful, add a script that prints:

\- cluster_id

\- face_count

so the user can pick clusters to label

Example:

\- backend/scripts/check_face_clusters.py can be extended, or create:

\- backend/scripts/list_clusters_for_labeling.py

5\. Implementation notes

\- keep code modular and beginner-friendly

\- use SQLAlchemy session patterns already in the project

\- no migrations; use current reset-based development approach if schema changed

\- do not introduce UI/API endpoints yet

\- do not rename or merge people automatically

\- do not infer names from file/folder names

6\. What to explain after coding

1\. what files were added or changed

2\. how to create a person

3\. how to assign clusters to a person

4\. how to inspect labeled vs unlabeled clusters

5\. what is still deferred to later milestones

