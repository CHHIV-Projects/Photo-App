I observed two problematic behaviors after running the 11.1 pipeline orchestration:

1.  The Unassigned Faces view now shows no unassigned faces.
2.  Existing face/person assignments appear to have been wiped out.

This is not the operator behavior I want for normal batch ingest.

Please investigate whether run_pipeline.py is currently rerunning face clustering in a way that rebuilds cluster memberships globally and resets cluster/person relationships.

Questions to answer:

-   Did the orchestration run full face clustering across all faces, not just newly ingested ones?
-   Does the current face clustering stage recreate cluster assignments/cluster IDs from scratch?
-   Are person assignments tied to cluster IDs in a way that gets lost when reclustering runs?
-   Were previously unassigned faces automatically reclustered during the run?

What I want:

-   normal pipeline ingestion should be safe for an already-reviewed/labeled system
-   it should not wipe out person assignments by default
-   it should not silently eliminate the unresolved/unassigned review state by reclustering everything

Please propose the safest operator behavior for this system. My current preference is:

-   default pipeline run should NOT rerun destructive global face clustering unless explicitly requested
-   full face reclustering should be an intentional/manual operation, not standard ingest behavior
-   reviewed identity work should be preserved by default

Please diagnose the exact cause first and then recommend the smallest safe fix.

I agree with the diagnosis and with the small safe fix direction.

Please proceed with the following decisions:

1. Yes, destructive mode should require a stronger confirmation than a simple yes/no. Please require the operator to type `REBUILD` before running global destructive face stages.

2. If destructive face stages are skipped, then crop generation should also be skipped by default in that same normal ingest flow. Since crop generation depends on face outputs, it should stay aligned with the face stages rather than running as if a face refresh occurred.

3. Yes, please change the wording to safer positive prompts such as:

* Run global face detection rebuild? (y/n, default n)
* Run global face clustering rebuild? (y/n, default n)

That is clearer and safer than skip wording.

4. Yes, keep CLI overrides for automation, but make the destructive behavior explicit there as well. It should never happen silently by default.

My preferred operator model is:

* normal ingest preserves reviewed identity work
* destructive global face rebuild is explicit, rare, and clearly warned
