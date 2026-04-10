**Milestone 11.1 — Pipeline Orchestration for Batch Ingest and Processing**

**Goal**

Create a single orchestration script that can run the photo organizer pipeline in the correct order for a new batch or larger test set.

This milestone should make it much easier to process a larger import without manually running many separate scripts in sequence.

**Context**

By the end of Milestone 10, the system now has:

-   ingestion pipeline pieces
-   PostgreSQL database
-   EXIF extraction and normalization
-   event clustering
-   face detection
-   face embeddings
-   face clustering
-   correction and review workflows
-   people, events, places, and photos UI
-   utility scripts such as missing crop generation

The backend works, but running a larger test set still relies on multiple manual steps.

This milestone creates the first **operator-friendly pipeline runner**.

**Problem This Milestone Solves**

Today, importing and processing a batch likely requires manually remembering and running multiple scripts in the correct order.

That is workable for development, but not ideal for:

-   larger test sets
-   repeatable experiments
-   reliable operational use
-   confidence that the same steps ran every time

This milestone provides one main script to orchestrate the pipeline.

**Primary Outcome**

When complete, the user should be able to run one command such as:

python backend/scripts/run_pipeline.py

or:

python backend/scripts/run_pipeline.py --from-path "C:\\some\\test\\set"

and have the pipeline run in the correct order with readable logging and a final summary.

**Scope**

Build a single orchestration script for batch processing.

Required:

-   one main entry-point script
-   clear ordered execution of existing pipeline stages
-   readable console output
-   basic success/failure reporting
-   support for default input source and optional override path
-   ability to skip selected stages
-   safe handling of failures

Optional if simple:

-   dry-run mode for stage plan only
-   summary timing per stage

Keep this milestone practical and operator-focused.

**Out of Scope (DO NOT DO)**

-   no background worker system
-   no job queue
-   no web-triggered execution
-   no scheduler
-   no advanced progress dashboard
-   no parallel/distributed orchestration
-   no major refactor of existing pipeline logic
-   no rewriting all scripts into a new framework

Reuse the current scripts and services wherever possible.

**Guiding Principle**

This should be an **orchestrator**, not a full pipeline rewrite.

Use the existing script/service logic that already works.

If some scripts currently only work as CLI wrappers, refactor lightly only when needed so the orchestrator can call reusable functions cleanly.

Do not duplicate logic.

**Required Behavior**

**1. Default pipeline order**

The orchestrator should run the major stages in the correct order.

Recommended default order:

1.  scan / collect input
2.  filter
3.  hash
4.  deduplicate
5.  storage/vault step
6.  ingest to DB
7.  EXIF extraction
8.  metadata normalization
9.  event clustering
10. face detection
11. face embeddings
12. face clustering
13. thumbnail/review crop generation or missing-crops utility if appropriate

If exact stage names differ in the project, follow the existing script naming and architecture.

**2. Default input source**

By default, use the project’s normal ingest/drop zone behavior.

If the current system expects a default drop/input directory, preserve that.

**3. Optional path override**

Allow the user to specify a custom source path for a batch import.

Example:

python backend/scripts/run_pipeline.py --from-path "C:\\Users\\chhen\\Desktop\\test_batch"

This should be beginner-friendly and clearly logged.

If existing pipeline pieces assume a fixed drop zone, it is acceptable to implement this by temporarily routing through that mechanism or by passing the path into the earliest compatible stage.

Keep it simple.

**4. Skip flags**

Allow skipping selected stages.

Examples:

-   \--skip-face-detection
-   \--skip-face-embeddings
-   \--skip-face-clustering
-   \--skip-crop-generation

Exact flag names may be adjusted to match your project naming, but they should be readable.

This is useful for:

-   reruns
-   faster iteration
-   partial reprocessing

**5. Readable logging**

Console output should clearly show:

-   which stage is starting
-   which stage completed
-   which stage failed
-   elapsed time per stage if easy

Example:

[1/13] Running scanner...

Done in 2.4s

[2/13] Running filter...

Done in 0.8s

At the end, show a summary.

**6. Failure behavior**

If a critical stage fails:

-   stop the pipeline
-   print clear error
-   exit non-zero

Do not blindly continue through dependent stages after a hard failure.

If a stage is intentionally skipped, make that explicit in output.

**7. Dry-run mode**

If simple, add:

\--dry-run

Behavior:

-   print the stages that would run
-   print skipped stages
-   do not execute anything

This is optional but recommended.

**8. Minimal summary**

At the end, print a summary such as:

Pipeline complete

Stages run: 12

Stages skipped: 1

Total elapsed: 00:04:32

Status: SUCCESS

If failed:

Pipeline stopped at face_embeddings

Status: FAILED

**Implementation Approach**

**Preferred approach**

Create a single script such as:

backend/scripts/run_pipeline.py

This script should orchestrate existing pipeline components.

It may:

-   call existing service functions directly
-   or invoke existing scripts/functions cleanly

Prefer direct function reuse when practical.

**Avoid**

Do not create a giant hardcoded shell-out script unless absolutely necessary.

If shelling out is currently the most practical option for one or two stages, that is acceptable, but the general design should remain clean and readable.

**Configuration Behavior**

Keep configuration simple.

Allowed:

-   use existing settings/config patterns already in project
-   accept --from-path
-   use current environment and database settings

Do not create a large new configuration subsystem.

**Suggested CLI Interface**

At minimum, support:

python backend/scripts/run_pipeline.py

python backend/scripts/run_pipeline.py --from-path "C:\\path\\to\\batch"

python backend/scripts/run_pipeline.py --skip-face-clustering

python backend/scripts/run_pipeline.py --skip-face-detection --skip-face-embeddings

Optional:

python backend/scripts/run_pipeline.py --dry-run

**Usability Requirements**

This script is meant for a non-programmer operator workflow.

So it should be:

-   predictable
-   clearly logged
-   easy to run
-   easy to understand when something fails

Avoid cryptic output.

**Suggested Internal Structure**

Possible helpers:

-   build_stage_plan(args)
-   run_stage(name, fn)
-   print_summary(results)
-   main()

Use a small ordered stage list rather than deeply nested logic.

**Verification Checklist**

Manually verify:

1.  script runs from backend project context
2.  default pipeline order executes in expected sequence
3.  \--from-path is accepted and clearly reported
4.  skip flags work
5.  pipeline stops on intentional stage failure
6.  summary prints at end
7.  dry-run works if implemented
8.  existing pipeline behavior is not broken

Use a small test batch for verification first.

**Deliverables**

After completion, provide:

1.  exact repo-relative file paths
2.  list of scripts/services reused
3.  supported CLI flags
4.  example commands
5.  sample console output
6.  notes on any light refactors made to support orchestration
7.  known limitations intentionally deferred

**Definition of Done**

Milestone 11.1 is complete when:

-   one orchestration script exists
-   it runs the pipeline in correct order
-   it supports default and override input source
-   it supports skip options
-   it gives clear console output and summary
-   it stops cleanly on failure

**Do NOT add in this milestone**

-   background jobs
-   GUI execution controls
-   advanced dashboards
-   distributed processing
-   major pipeline redesign
-   automatic event/place refinement
-   advanced retry system

Those belong later.

**Notes for Next Milestone**

After 11.1, likely next candidates are:

1.  search and filtering across people/clusters/photos/events/places
2.  scan-aware event logic
3.  event/place refinement tools
4.  usability polish and smarter suggestions

But 11.1 should focus only on a reliable batch-run orchestration workflow.

**Suggested Commit**

git commit -m "Milestone 11.1: Add pipeline orchestration script for batch ingest and processing"


1. For 11.1, use a single combined `--skip-face-clustering` flag. Since `run_face_clustering.py` currently performs both embedding generation and clustering, do not refactor just to split those controls in this milestone. Please document that this stage currently covers both embeddings and clustering.

2. For `--from-path`, it is acceptable and preferred to reuse `run_dropzone_ingestion.py` and the existing drop zone staging flow rather than bypassing it. That fits the orchestrator goal and keeps the implementation safer and simpler.

Please proceed with that approach.
