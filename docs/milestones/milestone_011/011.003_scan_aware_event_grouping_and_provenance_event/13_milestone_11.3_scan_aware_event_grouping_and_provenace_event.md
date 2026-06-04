**Milestone 11.3 — Scan-Aware Event Grouping and Provenance-Based Event Assignment**

**Goal**

Improve event grouping so scanned photos are handled differently from born-digital photos, using **provenance metadata** such as original folder structure as a primary signal.

This milestone should make event organization more accurate for scanned archives without disrupting the existing digital-photo event workflow.

**Context**

By the start of Milestone 11.3, the application supports:

-   ingestion and orchestration
-   EXIF extraction and normalization
-   event clustering (currently time-based)
-   face detection, clustering, correction, and people assignment
-   Photos, Events, and Places views
-   search and filtering

You have also identified an important limitation:

-   current event grouping works reasonably for born-digital photos
-   but scans often have weak or misleading timestamps
-   many scans retain **original provenance/folder information**, which is a much stronger grouping signal

This milestone improves the backend event logic so scans are grouped in a more human-meaningful way.

**Problem This Milestone Solves**

Current event grouping is primarily time-based.

That works fairly well for:

-   digital camera photos
-   phone photos
-   short real-world events

But it breaks down for scans because:

-   scan/import time may not reflect the original photo date
-   multiple decades of photos may be scanned in one batch
-   a meaningful album/folder may be more trustworthy than timestamp data

This milestone introduces **scan-aware event assignment**.

**Primary Outcome**

When complete, the system should:

1.  continue using time-based event grouping for born-digital photos
2.  use provenance/folder-based grouping for scanned assets
3.  assign scans into more meaningful events
4.  improve the Events view without requiring manual correction
5.  preserve current UI and workflow stability

**Scope**

Build scan-aware event grouping logic in the backend.

Required:

-   detect or use existing is_scan distinction
-   use provenance/folder information for scans
-   create or assign scan events based on provenance grouping
-   keep current time-based event grouping for non-scan assets
-   ensure Events view continues working with improved assignments

Optional if simple:

-   store a basic event label for scan-derived events using folder name
-   distinguish scan-derived vs time-derived events internally if already easy

Keep this milestone focused on backend grouping behavior, not UI redesign.

**Out of Scope (DO NOT DO)**

-   no event editing UI
-   no event merge/split UI
-   no event naming UI beyond trivial defaults
-   no place-aware event refinement yet
-   no people-overlap event intelligence yet
-   no ML event classifier
-   no major database redesign unless truly required
-   no timeline redesign

This is a targeted event-logic improvement milestone.

**Guiding Principle**

For scanned photos:

Trust human-created provenance (folder/album/source grouping) more than inferred timestamp gaps.

For born-digital photos:

Keep the current time-based grouping unless there is a compelling reason to change it.

**Required Behavior**

**1. Preserve digital event logic**

For non-scan assets:

-   continue using the existing event clustering logic
-   do not regress current digital-photo event behavior

**2. Add scan-aware grouping**

For scan assets:

-   group by provenance source, especially original folder path or equivalent stored provenance metadata
-   assign all scans from the same provenance grouping into the same event by default

Examples:

Scans/

Hawaii Trip 1992/

Christmas 2001/

Audrey Childhood Album/

Each meaningful source folder like the above should naturally become an event grouping signal.

**3. Preferred source of truth for scans**

Use the strongest provenance field already available in the system.

Possible candidates:

-   original folder path
-   source relative path
-   import batch folder
-   stored provenance metadata from ingestion

Before coding:

-   inspect what provenance data is already stored per asset
-   choose the most stable field already available

Do not invent a new metadata system unless absolutely necessary.

**4. Event assignment strategy**

For scans, assign events using provenance grouping rather than timestamp clustering.

Recommended behavior:

-   scans sharing the same provenance group → same event
-   timestamp may remain a secondary field, but should not be the primary grouping key

**5. Event creation behavior**

If a provenance group does not already map to an event:

-   create a new event for that provenance group

If the current event model supports only generic event rows:

-   reuse it
-   no need to create a separate “scan event” table

Keep the implementation simple.

**Optional Enhancement (if simple)**

**Basic event label from folder name**

If trivial and already compatible with your schema, derive a simple display label from provenance folder name.

Examples:

-   Hawaii Trip 1992
-   Christmas 2001

If not already easy:

-   skip it for now
-   continue using date/time ranges in UI

Do not expand scope to full event naming support.

**Backend Design Expectations**

**1. Reuse current event infrastructure**

Build on top of the existing:

-   event table/model
-   event assignment logic
-   Events API
-   Events view

**2. Keep assignment idempotent where possible**

Rerunning event assignment should be predictable.

Avoid generating duplicate event rows for the same provenance group if the same scan assets are reprocessed.

**3. Avoid overfitting one data source**

Use a provenance strategy that works for the current archive structure without hardcoding specific folder names.

**Implementation Suggestions**

Possible structure:

-   inspect assets and separate:
    -   scans
    -   non-scans
-   run:
    -   existing time-based event clustering for non-scans
    -   provenance-based event assignment for scans

If the current codebase has one run_event_clustering.py flow, update it carefully rather than creating a competing event pipeline.

Keep operator experience simple.

**Verification Checklist**

Manually verify:

1.  digital-photo event behavior still works
2.  scan assets from the same provenance folder now group into the same event
3.  scan event grouping no longer depends mainly on scan/import timestamp
4.  Events view still loads correctly
5.  scan-heavy event groups appear more human-meaningful
6.  no explosion of duplicate/stale event rows
7.  existing Photos / Places / People views remain unaffected

Use a small set of known scans with recognizable folder provenance for testing.

**Deliverables**

After completion, provide:

1.  files added or modified
2.  exact repo-relative file paths
3.  provenance field chosen for scan grouping
4.  summary of scan grouping logic
5.  note on whether event labels from folder names were implemented
6.  sample before/after examples of scan event grouping
7.  manual verification notes
8.  known limitations intentionally deferred

**Definition of Done**

Milestone 11.3 is complete when:

-   scans are grouped into events using provenance rather than only timestamps
-   digital-photo event grouping continues to work
-   Events view reflects improved scan-aware grouping
-   implementation remains simple and stable

**Do NOT add in this milestone**

-   event edit UI
-   event merge/split tools
-   place-aware event grouping
-   person-overlap event grouping
-   full trip/occasion hierarchy
-   reverse geocoding or map features

Those belong later.

**Notes for Next Milestone**

After 11.3, likely next candidates are:

1.  event/place refinement tools
2.  smarter move/assignment helpers
3.  usability polish for photo/event navigation
4.  incremental face processing improvements

But 11.3 should focus only on scan-aware event grouping.

**Suggested Commit**

git commit -m "Milestone 11.3: Add scan-aware event grouping using provenance-based assignment"



1. For scan event grouping, use the immediate parent folder of `original_source_path` as the default provenance grouping unit.

2. Keep scans from different provenance folders separate even if timestamps are close.

3. Yes, scan-derived events should appear in the existing Events view alongside digital events.

4. Please enable the optional enhancement now: when a scan-derived event has a usable provenance folder name, set `Event.label` from that folder name in a simple/lightweight way.

5. Yes, you can keep the current full-rebuild event assignment approach for 11.3, as long as the grouping logic remains deterministic and idempotent per run.

Please proceed with that approach.
