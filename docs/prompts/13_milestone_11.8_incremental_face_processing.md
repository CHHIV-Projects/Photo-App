**Milestone 11.8 — Incremental Face Processing**

**Goal**

Allow newly ingested assets to go through face processing **without destroying or rebuilding existing reviewed face, cluster, and person-assignment work**.

This milestone shifts face processing from a global rebuild-oriented workflow to an **incremental, identity-safe workflow**.

**Context**

The current system can:

-   ingest and deduplicate assets
-   extract and normalize metadata
-   detect faces
-   generate embeddings
-   cluster faces
-   support review, reassignment, merge, move, ignore, and person assignment workflows

Current limitation:

-   safe defaults avoid automatic global face rebuilds
-   new ingestion does not yet flow cleanly into face detection / embedding / clustering without risk of disturbing existing reviewed work
-   the system still relies too heavily on rebuild-style assumptions

This milestone must preserve the value of prior human review while allowing archive growth.

**Scope**

**In Scope**

-   incremental face detection for newly inserted assets
-   incremental face crop generation for new faces
-   incremental embedding generation for new faces
-   incremental cluster assignment for new faces
-   safe handling of unmatched/new faces
-   pipeline integration for incremental face processing
-   explicit protection of reviewed cluster/person work
-   scripts/utilities needed to support rerunnable incremental processing

**Out of Scope**

-   full global reclustering redesign
-   person suggestion engine (11.11)
-   duplicate cleanup workflows
-   changes to face review UX
-   auto-merging reviewed clusters based on new model logic
-   reprocessing all historical faces by default
-   changing existing manual review semantics

**Core Requirement**

**New assets must be processable without resetting, reassigning, or destabilizing existing reviewed identity data.**

That includes preserving:

-   existing face records
-   existing cluster records
-   existing person assignments
-   existing ignore states
-   existing manual corrections

**Desired Processing Model**

**Current Safe Direction**

Global rebuilds remain available only as explicit/manual workflows.

**New Incremental Direction**

For normal ingestion, the pipeline should support:

1.  ingest new asset
2.  detect faces on that asset only
3.  create face crops for those faces only
4.  create embeddings for those faces only
5.  assign those new faces into the existing clustering system safely
6.  leave all unrelated historical faces/clusters untouched

**Functional Requirements**

**1. Asset-Level Incremental Face Detection**

Process face detection only for assets that:

-   are newly inserted, or
-   explicitly lack completed face detection results

Requirements:

-   do not rerun face detection for already-processed assets during normal pipeline execution
-   preserve original-coordinate bounding box rules
-   create only missing face records

Suggested implementation pattern:

-   use explicit processing-state checks, not assumptions

**2. Incremental Face Crop Generation**

Generate review/debug crops only for newly created faces or missing crops.

Requirements:

-   do not regenerate all crops globally
-   do not overwrite existing valid crops unnecessarily

**3. Incremental Embedding Generation**

Generate embeddings only for faces that do not already have embeddings.

Requirements:

-   existing embeddings remain untouched
-   failed embeddings should remain retryable
-   reruns must be idempotent

**4. Incremental Cluster Assignment**

New faces must be compared against existing cluster structure and handled safely.

**Required behavior**

For each new embedded face:

-   compare against existing cluster representatives and/or eligible cluster members
-   if a confident match exists:
    -   assign face to existing cluster
-   if no confident match exists:
    -   create a new cluster
-   do not re-cluster historical faces globally during normal ingestion

**Safety rules**

-   must not dissolve existing clusters
-   must not remove existing person assignments
-   must not split reviewed clusters
-   must not automatically merge reviewed clusters as part of this milestone

**5. Reviewed Cluster Protection**

Introduce explicit protection rules for reviewed identity work.

At minimum, incremental processing must preserve:

-   cluster-to-person assignments
-   ignored clusters
-   manual face moves
-   manual cluster merges already accepted by the user

If needed, add simple state markers that distinguish:

-   reviewed / user-touched clusters
-   untouched / machine-generated clusters

Do this only if necessary for safe logic. Keep it minimal.

**6. Matching Strategy**

Use an explainable, deterministic incremental matching strategy.

Requirements:

-   reuse current embedding approach
-   use current similarity approach unless a small adaptation is required
-   prefer assigning new faces into existing clusters rather than triggering broad reclustering
-   keep thresholds config-driven
-   if ambiguous, prefer creating a new cluster over forcing assignment

This milestone should favor **safety over aggressiveness**.

**7. Pipeline Integration**

Update the normal pipeline so that incremental face processing can run as part of standard ingestion.

Desired behavior:

-   default pipeline run with new assets can optionally include incremental face processing
-   global rebuild remains separate and explicit
-   logs should clearly distinguish:
    -   new assets processed
    -   new faces detected
    -   embeddings created
    -   faces assigned to existing clusters
    -   new clusters created

Do not silently trigger a global rebuild.

**8. Rerun / Idempotency Requirements**

Normal reruns must be safe.

Rerunning incremental processing should not:

-   duplicate face rows
-   duplicate embeddings
-   duplicate crops
-   create repeated cluster assignments
-   disturb existing reviewed work

If an asset already completed all incremental face stages, rerun should skip it cleanly.

**9. Error Handling**

Failures should be localized.

Requirements:

-   one failed asset must not invalidate all previously processed face work
-   partial progress should be preserved where safe
-   failed items should be retryable

**Backend Requirements**

**Data / State**

Add minimal processing-state support as needed to determine whether an asset/face has already completed:

-   face detection
-   crop generation
-   embedding generation
-   cluster assignment

This can be:

-   explicit status fields, or
-   safe presence/absence checks

Keep design simple and durable.

**Services**

Update or add services for:

-   incremental face detection
-   incremental embedding generation
-   incremental cluster assignment

**Scripts / Orchestration**

Update pipeline orchestration so incremental face processing can be invoked cleanly in standard runs without global rebuild behavior.

**Frontend Requirements**

No major new UI required.

Optional only if simple:

-   surface new unassigned/newly created faces naturally in the existing review workflow
-   ensure current review screens still function normally after incremental processing

Do not expand UI scope for this milestone.

**Validation Checklist**

**Incremental Processing**

-   a newly ingested asset can complete face detection without global rebuild
-   only new/missing faces get crops
-   only new/missing faces get embeddings
-   only new faces are considered for incremental cluster assignment

**Identity Safety**

-   existing clusters remain intact
-   existing person assignments remain intact
-   ignored clusters remain intact
-   prior manual corrections remain intact

**Clustering Behavior**

-   confident new face matches join existing cluster
-   unmatched new faces create new cluster
-   ambiguous cases do not force unsafe assignment

**Rerun Safety**

-   rerunning does not duplicate faces, crops, or embeddings
-   rerunning does not churn reviewed cluster structure
-   rerunning is idempotent for completed assets

**Regression**

-   existing review workflow still works
-   people assignments still display correctly
-   photos/events/people views remain stable

**Deliverables**

-   backend changes for incremental face-processing flow
-   pipeline/orchestration updates
-   minimal state tracking needed for safe reruns
-   code summary describing:
    -   how new faces are matched
    -   how reviewed clusters are protected
    -   how rerun safety is enforced
-   validation results from coder

**Definition of Done**

-   newly ingested assets can go through face processing incrementally
-   existing reviewed identity work is preserved
-   no global rebuild is required for routine ingestion
-   reruns are safe and idempotent
-   system remains deterministic and stable
-   existing UI/review flows continue to function

11.8 decisions:

Q1:
- Yes, proceed with persistent embedding storage
- Add faces.embedding_json TEXT
- Add face_clusters.centroid_json TEXT
- Keep serialization simple (JSON float list / JSON centroid), no vector-index work yet

Q2:
- Use explicit Asset.face_detection_completed_at DATETIME
- This is preferred over Face-row presence because it handles zero-face assets cleanly

Q3:
- Add FaceCluster.is_reviewed BOOL
- Protected clusters = person-assigned OR ignored OR reviewed
- Manual face moves should mark affected clusters as reviewed

Q4:
- Yes, safe default approved
- Faces with stored embeddings are not treated as new on incremental rerun
- Manually unassigned faces remain unassigned until an explicit future rebuild/reprocess workflow

Q5:
- Normal run_pipeline.py should run incremental face processing by default
- Only for new/unprocessed assets
- No global rebuild unless explicitly requested
- Logging should clearly distinguish incremental processing from rebuild workflows