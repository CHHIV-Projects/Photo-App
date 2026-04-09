Build Milestone 6: event clustering and temporal grouping.

Goal:

Group stored assets into simple candidate events using normalized metadata, especially captured_at.

Scope:

\- use existing Asset records in PostgreSQL

\- use normalized metadata already stored on Asset

\- create a first practical event grouping system

\- keep the logic simple, deterministic, and beginner-friendly

\- do not build embeddings or AI clustering yet

\- do not build frontend event UI yet

\- do not build smart labels yet

\- do not build album features yet

Required behavior:

1\. Database changes

Create an Event model/table with fields like:

\- id

\- start_at

\- end_at

\- asset_count

\- label (nullable)

\- created_at_utc

Also connect assets to events using one of these simple approaches:

\- add nullable event_id to Asset

or

\- create a simple link table

Preferred for this milestone:

\- add nullable event_id to Asset

2\. Event grouping logic

Create a service that:

\- loads assets from the database

\- ignores assets with no captured_at if needed

\- sorts assets by captured_at

\- groups consecutive assets into the same event when they are within a configurable time gap

\- starts a new event when the gap exceeds the threshold

Default recommendation:

\- use a simple threshold like 4 hours, configurable

3\. Basic heuristics

Keep heuristics simple:

\- use captured_at as the primary grouping signal

\- optionally avoid grouping assets marked is_scan with normal photo events unless timestamps clearly fit

\- preserve deterministic behavior

\- do not add GPS-based grouping yet unless very simple

4\. Persistence

Create/update Event rows and assign event_id to grouped Asset rows.

Behavior:

\- safe to rerun for development

\- for this milestone, it is acceptable to reset and rebuild event assignments during the run

\- report:

\- total assets considered

\- assets skipped for missing captured_at

\- total events created

\- largest event size

\- smallest event size

5\. Runner script

Create a script:

\- backend/scripts/run_event_clustering.py

It should:

\- read assets from DB

\- cluster them into events

\- persist the results

\- print a summary

6\. Verification

If useful, also create a small read/check script or extend the existing DB check script so we can inspect:

\- event_id

\- event start/end

\- asset count per event

Implementation notes:

\- keep code modular and readable

\- use type hints and docstrings

\- avoid overengineering

\- do not add Alembic or migrations yet

\- keep the threshold easy to adjust

\- make the run idempotent enough for development use

Project structure guidance:

Use files in locations like these unless a better fit already exists:

\- backend/app/models/event.py

\- backend/app/services/organization/event_clusterer.py

\- backend/scripts/run_event_clustering.py

What to explain after coding:

1\. what files were added or changed

2\. how the clustering logic works

3\. what time-gap threshold is used

4\. how to run the script

5\. how to verify event assignments

1. Event assignment for scans
For Milestone 6, exclude scans from clustering.

Reason:
- scan timestamps are less trustworthy
- we do not want scan-heavy imports polluting normal photo events yet
- scans can be handled in a later milestone after better date-estimation logic exists

So:
- do not assign is_scan=True assets to events in this milestone
- report them as skipped

2. Time gap default
Yes, confirm default threshold = 4 hours (14,400 seconds), configurable via settings.

3. Label behavior
For this milestone, label should be None.

Reason:
- keep Event as a structural grouping object only
- naming/labeling can come later

4. Single-asset events
Yes, a lone asset should become a valid event of size 1.

Reason:
- it is still a meaningful capture moment
- better to preserve than discard

5. Verification preference
Create a separate check_events_in_db.py script.

Reason:
- keeps asset checking and event checking cleanly separated
- easier to reason about event output
