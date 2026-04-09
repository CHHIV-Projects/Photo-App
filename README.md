## Storage Intent

- Drop Zone is temporary staging for ingestion.
- Vault is canonical hash-based long-term storage.
- Drop Zone should not be treated as long-term storage.

## Milestone 9.1 Correction Workflow

Run from `backend` to review clusters, correct assignments, and verify state.

```powershell
Set-Location "C:/Users/chhen/My Drive/AI Photo Organizer/Photo Organizer_v1/backend"
$py = "C:/Users/chhen/My Drive/AI Photo Organizer/Photo Organizer_v1/.venv/Scripts/python.exe"

# 1) List clusters for review (ignored clusters excluded by default)
& $py scripts/list_clusters_for_labeling.py 30

# 2) Optional: include ignored clusters in the list
& $py scripts/list_clusters_for_labeling.py --include-ignored 30

# 3) Review cropped faces for a cluster before labeling/correction
& $py scripts/review_face_cluster.py 5

# 3b) Review multiple clusters in one run (writes separate cluster_<id> folders)
& $py scripts/review_face_cluster.py --no-prompt --output-root storage/review_batch 5 11 12

# 4) Remove one bad face from its cluster (idempotent)
& $py scripts/unassign_face_from_cluster.py --no-prompt 123

# 5) Move one face into another cluster
& $py scripts/move_face_to_cluster.py --no-prompt 123 8

# 6) Merge source cluster into target cluster
& $py scripts/merge_face_clusters.py --no-prompt 12 8

# 7) Ignore a low-quality cluster (exclude from normal labeling workflows)
& $py scripts/ignore_face_cluster.py --no-prompt 12

# 8) Unignore a cluster if needed
& $py scripts/unignore_face_cluster.py --no-prompt 12

# 9) Label a cluster to a person (Milestone 9)
& $py scripts/create_person.py --no-prompt "Jane Smith"
& $py scripts/assign_clusters_to_person.py --no-prompt "Jane Smith" 8

# 10) Verify overall person/cluster state
& $py scripts/check_people_and_clusters.py 10

# 11) Verify face-level assignments (face_id, cluster_id, person_id, is_ignored)
& $py scripts/check_face_cluster_assignments.py 20
```

Notes:

- `--no-prompt` is recommended for automation or batch runs; scripts fail fast instead of waiting for input.
- `merge_face_clusters.py` blocks merge when source/target have conflicting `person_id` values.
- `move_face_to_cluster.py` blocks moves into ignored target clusters.
