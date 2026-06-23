# CANONICAL_PARKING_LOT_v4 — Photo Organizer

## Purpose

Track deferred, future, and refinement work while maintaining:

- focus on active milestones
- architectural clarity
- system evolution visibility
- clean separation between active roadmap and deferred ideas

This document is:

- decision-oriented
- de-duplicated
- structured by system area
- limited to incomplete or intentionally deferred work

Completed items have been removed or reclassified as follow-up polish items.

---

## Current Near-Term Direction

The current near-term priority is to finish ingestion confidence before returning to broader curation and enrichment polish.

The intended order is:

```text
A. Finish ingestion confidence
   - real iCloud staging cleanup, not just dry run
   - cleanup + reacquire + non-repeat validation
   - external import identity independent of drive letter

A/B bridge. Consolidate cloud ingestion steps
   - make cloud acquisition + Source Intake feel like one coordinated intake flow
   - reduce chances of mismatched acquisition and intake volumes
   - consolidate status and workflow summary

B. Simplify ingestion UX
   - fewer duplicated technical tiles
   - binary readiness
   - Advanced Details for backend diagnostics
   - same general workflow feel for local, external, and cloud sources

C. Then revisit review/curation systems
   - people
   - source review
   - timeline/events
   - places
   - visual enrichment
   - assigning places to non-geolocated assets
```

---

# 1. Near-Term Promotion Candidates

These are the strongest candidates for upcoming milestones after the documentation refresh.

---

## ICL-CLEAN-001 — Verified iCloud Staging Cleanup Execution

### Summary

Enable real cleanup execution after the cleanup dry-run process has been validated.

### Current State

The guided iCloud flow currently supports cleanup dry run. The dry run can identify eligible staged files and reports:

```text
eligible files
bytes eligible
skipped/protected
deleted = 0
bytes deleted = 0
```

### Desired

Add explicit, operator-confirmed cleanup execution for local iCloud staging files only.

The cleanup execution must:

- delete only verified local staged files
- require a recent successful dry run
- require explicit confirmation
- show exactly what will be deleted
- produce a cleanup report
- never delete iCloud cloud-library data
- never delete Vault files
- never delete DB records
- never delete provenance
- never delete Source Profile/source registry rows

### Safety Requirements

Before deletion, each candidate must have positive verification evidence, such as:

```text
staged local file exists
asset/provenance evidence exists
Vault file exists
candidate belongs to selected Source Profile
candidate is not protected/skipped
```

### Importance

Very high.

This is the final safety step needed before cloud ingestion feels operationally complete.

---

## ICL-CLEAN-002 — Cleanup / Reacquire / Non-Repeat Validation Loop

### Summary

Validate the full production-like iCloud loop:

```text
Acquire
→ Source Intake
→ Cleanup
→ Reacquire
→ Confirm non-repeat behavior
```

### Current Issue

A cleanup process is only useful if it does not cause the same recent files to be repeatedly downloaded again.

### Desired

Run and validate:

1. Acquire from iCloud.
2. Run Source Intake.
3. Run cleanup dry run.
4. Execute verified cleanup.
5. Run acquisition again in non-repeat mode.
6. Confirm previously acquired/ingested/cleaned assets are not redownloaded unnecessarily.
7. Confirm the workflow reports whether it is caught up, incomplete, or unknown.

### Importance

Very high.

This validates real-world cloud ingestion safety.

---

## ICL-UX-001 — Consolidated Cloud Ingestion Flow

### Summary

Make iCloud acquisition and Source Intake feel like one coherent cloud-ingestion workflow from the user perspective.

### Current Issue

Today, the user sees multiple separate steps:

```text
Acquire from iCloud
Run Source Intake
View acquisition status
View workflow summary
Run cleanup dry run
```

This is architecturally safe but visually and cognitively fragmented.

### Desired

Create one guided cloud ingestion flow:

```text
1. Check readiness
2. Download from iCloud
3. Import downloaded files into Photo Organizer
4. Review results
5. Cleanup dry run / cleanup
```

Internally, acquisition and Source Intake may remain separate operations, but the UI should coordinate them.

### Design Principle

There should be no routine opportunity for incongruent asset volumes between acquisition and intake.

If acquisition downloads 29 files, Source Intake should clearly use the acquisition inventory or explain any difference.

### Importance

Very high.

This is the bridge between ingestion confidence and UX simplification.

---

## UX-INGEST-001 — Guided Source Profile / Ingestion Tab Simplification

### Summary

Simplify the Ingestion tab and Source Profile workflow.

### Current Issue

The current UI exposes too many technical fields and repeated tiles:

```text
normalized label
effective path
source root compatibility identity
managed staging path
source registration
operational conflicts
blocking reasons
warnings
last acquisition status
cleanup status
overall result / next step
multiple refresh buttons
```

### Desired

A simplified user-facing model:

```text
Source
Readiness
Action
Progress
Result
Next safe action
Advanced Details
```

### Specific UX Direction

- Readiness should be binary:
  - Ready
  - Blocked
- Warnings should become:
  - automatic fixes,
  - blockers,
  - or Advanced Details.
- Technical path/identity fields should move to Advanced Details.
- Refresh buttons should generally be automatic or secondary.
- “Recommended Next Action” / “Overall Result” should be replaced by accurate workflow state.

### Importance

Very high.

This is likely the next major UX milestone after cleanup execution and cloud-flow consolidation.

---

## UX-INGEST-002 — Unified Workflow Summary for Acquisition / Intake / Cleanup

### Summary

Replace separate acquisition, intake, cleanup, and next-step tiles with one unified workflow summary.

### Current Issue

iCloud currently shows several related status areas:

```text
iCloud Acquisition Status
iCloud Workflow Summary
Source Intake Result
Cleanup Dry Run Status
Overall Result / Next Step
```

Some are redundant or stale.

### Desired

One workflow summary showing:

```text
Acquisition: completed / failed / not run
Source Intake: completed / failed / not run
Cleanup Dry Run: completed / failed / not run
Cleanup Execution: completed / not run / deferred
Files downloaded
Files imported
Files skipped/known
Files failed/deferred
Files eligible for cleanup
Files deleted locally
Report paths
Next safe action
```

### Importance

Very high.

This improves trust and reduces confusion.

---

## EXT-001 — External Drive Identity Independent of Drive Letter

### Summary

External drive Source Profiles should represent the physical/logical device, not the temporary Windows drive letter.

### Current Issue

Windows drive letters can change.

A source such as:

```text
External 1
```

should not become a different source just because it mounts as `E:\` instead of `D:\`.

### Desired

Future model:

```text
Source Profile = External 1
Run path = current mount path + canonical subfolder
Provenance = source-profile-based
Observed mount/path retained as evidence
```

### Future Questions

- Can the system capture volume label, volume serial number, or stable device identity?
- Should each run verify that the current path matches the expected external source?
- How should the user update a mount path without changing source identity?
- Should external drive profiles include expected root folder and device fingerprint?

### Importance

Very high before large external imports.

---

## PREVIEW-001 — BMP Display Preview Support

### Summary

Add BMP files to the display-safe/review preview generation pipeline.

### Current State

HEIC/HEIF and TIFF preview handling exist. The suspected HEIC rendering issue during 12.62.10 validation was corrected as process-order/user error.

However, BMP files need display-safe/review processing.

### Desired

- Add BMP to supported display-preview inputs.
- Generate browser-friendly previews for BMP assets.
- Ensure Photo Review uses generated preview where appropriate.
- Add regression test/sample coverage.
- Confirm HEIC/TIFF/JPEG/PNG behavior is not affected.

### Importance

High.

Needed for broader legacy media compatibility.

---

## OPS-RUNTIME-001 — Docker/WSL Ghost Listener Diagnostics

### Summary

Improve runtime scripts to diagnose ghost port listeners and unresolved owning PIDs.

### Current Observation

Port `8001` remained in LISTENING state with nonexistent PID `14992` even after:

```text
Photo Organizer shutdown
Docker process kills
WSL shutdown
hns/winnat restart
```

Reboot was required.

### Desired

Start/stop scripts should detect:

```text
port occupied
owning PID cannot be resolved
possible Docker/WSL/Windows NAT ghost listener
```

and provide a clear recovery message.

### Candidate Recovery Guidance

```text
1. Run stop script.
2. Check netstat/Get-NetTCPConnection.
3. Shut down WSL.
4. Restart Docker Desktop.
5. Restart hns/winnat if needed.
6. Reboot if listener persists with nonexistent PID.
```

### Importance

High before v1 and mini-server deployment.

---

## DEPLOY-001 — Mini-Server + NAS Deployment Architecture

### Summary

Plan production-like deployment on the dedicated mini server with NAS-backed durable storage.

### Current Decision

The user plans to build and use a mini server for larger test environment and/or v1.

Initial target:

```text
Case: Fractal Terra
CPU: AMD Ryzen 9 7900
Cooler: Noctua NH-L12S
Motherboard: ASUS ROG Strix B650E-I
GPU: RTX 4070 Super dual fan
RAM: 64GB DDR5-6000
SSD: Samsung 990 Pro 2TB
PSU: Corsair SF850L 850W SFX-L
OS: Ubuntu Server 24.04
```

### Intended Roles

Mini server:

```text
Photo Organizer runtime
backend/frontend
Dockerized services
local/mobile web server
local AI semantic search
GPU-assisted processing
background jobs
```

NAS:

```text
durable media storage
backup/snapshot layer
long-term archive storage
```

### Desired

Plan:

- Docker layout
- PostgreSQL/Redis placement
- GPU/CUDA setup
- NAS mount strategy
- Vault path strategy
- backup and restore
- service supervision
- local/mobile access
- dev/test/prod separation

### Importance

High before larger test environment or v1.

---

## ICL-001 — iCloud Acquisition Until-Found / Checkpoint Strategy

### Summary

Improve iCloud acquisition completeness beyond fixed `recent_count`.

### Current Issue

Standard recent-window acquisition can download the requested recent assets without proving whether there are unacquired older assets beyond the fixed window.

### Desired

Support acquisition logic such as:

```text
download/check recent items until N consecutive already-known items are found
```

or:

```text
maintain checkpoint by cloud asset ID / added date / provenance state
```

### Future Questions

- Can `icloudpd --until-found` solve this directly?
- Does `icloudpd` maintain enough local state for reliable incremental acquisition?
- Should Photo Organizer maintain its own acquisition checkpoint?
- Should “known” mean staged file exists, provenance exists, Vault asset exists, or cloud asset ID seen?
- How should the UI report recent window checked, likely caught up, incomplete, or unknown completeness?

### Importance

High.

Needed for production confidence beyond recent-window tests.

---

## PX-016 — Undated Asset Discovery

### Summary

Add explicit discovery tools for assets missing reliable capture dates.

### Desired

- explicit “Undated” filter
- optional timeline bucket for undated / unknown-date assets
- Photo Review filter integration
- metadata completeness workflow

### Importance

High-impact usability improvement.

---

## PX-018 — Manual Date Trust Override / Physical Media Detection

### Summary

Allow the user to manually override capture-time trust, especially for photos of physical media.

### Problem

Some assets have valid digital EXIF timestamps but are actually photos of slides, printed photos, documents, albums, or negatives.

The system may classify these as high trust because the camera timestamp is valid, but the timestamp reflects digitization date, not original capture date.

### Desired

Allow manual override from Photo Review:

```text
High → Low
High → Unknown
Low → High, if user confirms correctness
```

### Design Considerations

- preserve original EXIF metadata
- do not rewrite source files
- show both system trust and user override
- allow optional notes/reason later
- potential future AI suggestions only, never automatic changes

### Importance

High for timeline correctness.

---

# 2. iCloud / Cloud Acquisition Track

---

## ICL-AUTH-001 — iCloud Session Health and Authentication Helper

### Summary

Define a safe UI-guided path for iCloud authentication/session health without storing Apple credentials in Photo Organizer.

### Desired

Future UI may provide:

```text
Check iCloud Session
Authentication required
Open iCloud authentication helper
Show session ready / expired / failed
```

The helper may launch or guide an isolated `icloudpd` auth flow, but Photo Organizer must not store secrets.

### Safety Boundaries

- No Apple password storage in DB.
- No 2FA code storage.
- No secrets in logs.
- No secrets in command history.
- `icloudpd` owns session storage.
- Photo Organizer records only non-secret status.

### Importance

High before scheduled or unattended cloud acquisition.

---

## ICL-AUTH-002 — icloudpd Version and Environment Diagnostics

### Summary

Add `icloudpd` version and environment diagnostics to iCloud readiness/status UI.

### Current Observation

During iCloud validation, an older project-local `icloudpd` version caused 2FA/authentication issues. Updating project-local `icloudpd` resolved the issue.

### Desired

Readiness/status UI should show:

```text
icloudpd found
icloudpd version
project-local path
Python/environment path if relevant
auth/session status if safely checkable
```

### Importance

High.

This will reduce confusion around iCloud authentication failures.

---

## ICL-003 — Multi-iCloud Account Support

### Summary

Define how multiple iCloud accounts should be represented and operated.

### Current Assumption

Normal production use:

```text
1 iCloud account/library = 1 stable iCloud Source Profile
```

### Desired

Support multiple iCloud accounts safely without mixing source folders or account sessions.

### Importance

Medium.

---

## ICL-004 — Cloud-Native iCloud Provenance

### Summary

Extend provenance to include iCloud-specific remote identity.

### Desired

Capture additional cloud-native provenance where available:

```text
remote iCloud asset ID
Apple ID / account identity
icloudpd run ID
download timestamp
download method
original iCloud filename
Live Photo resource relationship
```

### Importance

Medium-high for future cloud synchronization.

---

## ICL-005 — iCloudPD Advanced Options

### Summary

Expose safe advanced `icloudpd` options.

### Candidate Options

```text
--until-found
--album
--folder-structure
--skip-videos / include videos
Live Photo related flags
size/original options
```

### Importance

Medium.

---

## ICL-006 — iCloud Album / Favorites / People Metadata Import

### Summary

Import iCloud organizational metadata beyond files.

### Possible Metadata

```text
album membership
favorites
people labels
shared library info
edited/original variants
```

### Importance

Lower priority than acquisition correctness.

---

# 3. Source Profile / Ingestion / Operations

---

## SRC-001 — Source Profile Lifecycle Polish / Archive UX

### Summary

Polish source lifecycle behavior now that active/inactive/archive-style support exists.

### Desired

- clear Active / Inactive / Archived behavior
- archived sources hidden from normal run lists
- archived sources preserved in provenance/history
- test/deprecated source handling
- safe restore/reactivate workflow
- no deletion if provenance exists

### Importance

Medium-high.

---

## SRC-002 — Test Source Cleanup and De-Cluttering

### Summary

Clean up historical test source folders and source registry/profile clutter created during iCloud development.

### Desired

- identify test-only source labels
- identify test-only staging folders
- determine which folders contain already-ingested files
- delete safe local staging files where appropriate
- mark test sources inactive/archived
- preserve provenance explainability

### Importance

Medium-high after lifecycle polish and cleanup execution are trusted.

---

## IN-001 — Drop Zone Reprocessing Behavior

### Summary

Define how Drop Zone contents should be handled if a run is interrupted or files remain after partial processing.

### Importance

Medium.

---

## IN-002 — Provenance vs Ingestion Run Separation

### Summary

Clarify and, if needed, refactor separation between durable provenance and ingestion run history.

### Importance

Medium.

---

## IN-003 — Large Source Progress / Completion Reporting

### Summary

Improve progress reporting for large local, external, or cloud source folders.

### Importance

Medium-high for large real-world imports.

---

## OPS-001 — Unified Operational History

### Summary

Create a unified operational view showing source/profile workflows across acquisition, intake, cleanup, and post-intake jobs.

### Desired

The system can show:

```text
Source Profile
→ acquisition run, if applicable
→ staged files
→ Source Intake run
→ new/skipped/failed/deferred
→ cleanup dry run / cleanup execution
→ post-intake jobs
→ reports
```

### Importance

High for operational trust and troubleshooting.

---

## OPS-002 — Operational Report Browser / Viewer

### Summary

Provide UI access to operational reports under `storage/logs/`.

### Importance

Medium.

---

## OPS-003 — Automatic / Suggested Post-Intake Enrichment Chain

### Summary

Optionally run or suggest post-intake jobs after Source Intake.

### Importance

High after ingestion is stable.

---

## OPS-004 — Launcher Already-Running / Port Conflict Handling

### Summary

Improve startup scripts so they detect when Photo Organizer is already running and provide clear operator guidance.

### Importance

Medium-high.

---

# 4. Photo Review / General UX

---

## UX-001 — Photo-Centric Unified Correction Workspace

### Summary

Create a single photo-centric correction workspace.

### Importance

High after ingestion stabilization.

---

## UX-002 — Multi-Surface UI Architecture

### Summary

Clarify and separate UI modes:

```text
Viewer
Workbench
Admin
```

### Importance

Medium-high.

---

## UX-003 — Auto-Advance Workflow

### Summary

After certain actions, automatically advance to the next item.

### Importance

Medium.

---

## UX-004 — Smart Filtering Expansion

### Summary

Expand filtering capabilities across Photo Review and related views.

### Candidate Filters

```text
undated
low date trust
missing location
has location
has faces
unassigned faces
demoted
Live Photo motion companion
video
specific media formats
BMP / HEIC / TIFF / JPG / PNG
```

### Importance

Medium-high.

---

## SEARCH-004 — Photo Review Search Hierarchy and Search Bar Improvements

### Summary

Revisit Photo Review search/filter behavior to support smarter hierarchical filtering and less rigid search behavior.

### Importance

Important before production-level usability.

---

## UX-007 — Collection Polish

### Summary

Defer Collection UI/UX polish until broader Source Review / Album / Collection workflow has more real usage and testing.

### Priority

Deferred.

---

# 5. Face / Identity System

---

## ID-001 — Create Cluster from Face

Allow user to create a new cluster/person workflow from an individual unassigned face.

## ID-002 — Friendlier Cluster Selection

Improve UI for selecting or moving faces between clusters.

## ID-003 — Representative Faces

Allow users to choose representative face thumbnails for people or clusters.

## ID-004 — Cluster Confidence Signals

Show confidence/quality indicators for clusters and suggested identities.

## FW-001 — Bulk Face Actions

Support bulk operations on selected faces.

## FW-002 — Suggested Cluster Improvements

Improve cluster suggestions and assignment flow.

## FW-003 — Face Comparison Tool

Allow side-by-side comparison of faces/clusters/person candidates.

## FW-004 — Suggestion Dismissal System

Allow user to dismiss incorrect face/person suggestions.

## FW-005 — Large Image Face Assignment Mode

Add a larger-image face assignment mode for photos where thumbnail/card overlays are too small.

## FACE-005 — Backfill Protected Manually Unassigned Faces

Backfill and protect manually unassigned faces so later processing does not undo the user’s decision.

## FACE-006 — Face Review Visual Polish and Cluster Thumbnail Cards

Improve Face Review scannability after more real-world usage.

---

# 6. Location / Places / Non-Geolocated Assets

---

## PL-001 — Location Intelligence Master Track

Expand location intelligence beyond reverse geocoding.

## PL-002 — Location Filtering

Add richer location filters.

## PL-003 — Place Normalization

Resolve inconsistent or duplicate place names.

## PL-004 — Missing Location Handling

Define and expose behavior for assets without GPS/location.

## PL-005 — Provenance vs Location Reconciliation

Resolve cases where source/provenance location and GPS/geocoded location imply different places.

## PL-006 — Assign Place to Non-Geolocated Assets

### Summary

Allow user-approved place assignment for assets without GPS.

### Desired

Use evidence from:

```text
visual enrichment
landmark/context labels
source/provenance paths
event membership
nearby dated/geotagged assets
user selection
```

### Constraint

No automatic canonical place assignment from AI/provider output without user confirmation.

### Importance

High after ingestion stabilization and visual enrichment review.

---

# 7. Source Review / Timeline / Events / Collections

---

## SR-001 — Source Review Timeline Integration

Improve source-derived review by integrating source path, timeline, and event context.

## CO-001 — Event ↔ Album Integration

Enable event-to-album workflows.

## CO-002 — Collections System Expansion

Define whether albums, collections, smart collections, and saved filters should become a unified collection system.

## EV-001 — Event Date Range Consistency

Ensure date range recalculation is consistent across merge, assign, remove, manual correction, and incremental clustering.

---

# 8. Media / Video / Live Photo

---

## MV-001 — Live Photo Playback UI

Add Apple-like or simplified playback for paired Live Photos.

## MV-002 — Live Photo Motion Companion Filtering

Allow UI to hide or filter Live Photo motion companion MOV files.

## MV-003 — Video Canonicalization Recompute Parity

Bring video support into any remaining canonical metadata recompute paths that are still image-only.

## MV-004 — Video Strategy / Playback System

Define full video handling strategy.

## MV-005 — Legacy Camcorder Format Support

Evaluate support for older video formats.

---

# 9. Duplicate System

---

## DUP-001 — Hamming Distance Threshold Tuning

Tune pHash Hamming distance thresholds for near-duplicate detection.

## DUP-002 — Duplicate Group Review Improvements

Improve duplicate review usability.

## DUP-003 — Cross-Format Detection Gap

Improve detection across HEIC/JPG/PNG/TIFF/video derivatives where pHash or metadata differs.

## DUP-004 — Cross-Format Auto Grouping

Explore safe auto-grouping for likely cross-format duplicates.

## DUP-005 — Multi-Signal Duplicate Scoring

Combine multiple signals beyond pHash.

## DUP-006 — Canonical Asset Locking

Support optional canonical “lock” behavior where user-selected canonical assets are preserved.

---

# 10. Demotion / Visibility

---

## DS-001 — Non-Duplicate Demotion

Allow reversible demotion of non-duplicate unwanted assets.

## DS-002 — Demoted Asset Management

Provide UI to view and restore demoted assets.

---

# 11. Deployment / Mini-Server / NAS / Scheduling

---

## DEPLOY-002 — Production Bootstrap / Runtime Validation

Validate the production bootstrap foundation against the real mini-server/NAS-backed production path before real production archive ingestion.

## NAS-001 — NAS Storage Readiness Plan

Prepare NAS-backed durable media storage.

## SCHED-001 — Scheduled iCloud Acquisition

Run iCloud acquisition automatically on mini-server or always-on host.

---

# 12. Intelligence / AI Long-Term

---

## AI-001 — Semantic Search Expansion

Improve natural-language and semantic search over assets.

## AI-002 — Landmark / Scene Intelligence

Identify landmarks, venues, or meaningful scenes beyond reverse geocoding.

## AI-003 — Physical Media Detection Suggestions

Use visual signals to suggest likely scanned/photographed physical media.

## AI-004 — EXIF / Metadata Inference Assistance

Explore assisted inference for missing dates or metadata.

## AI-005 — Local AI Service Boundary

Define how local AI services should run on the mini-server.

---

# 13. Working Priority Stack

Current recommended priority stack:

```text
1. Verified iCloud staging cleanup execution
2. Cleanup → reacquire → non-repeat validation loop
3. Consolidated cloud ingestion flow
4. Guided Source Profile / Ingestion Tab simplification
5. Unified acquisition/intake/cleanup workflow summary
6. External drive identity independent of drive letter
7. Local/external/cloud workflow shell unification
8. BMP display-preview support
9. Runtime ghost-listener diagnostics
10. Mini-server + NAS deployment architecture
11. Post-intake review-readiness checklist / job recommendations
12. Undated/date-trust/photo-review filters
13. Source Review / Timeline / Events refinement
14. Places for non-geolocated assets
15. People/Face workflow tuning
16. Visual enrichment refinement
17. Semantic search / local AI expansion
```

The guiding decision is:

```text
Finish ingestion confidence first.
Then simplify and consolidate ingestion UX.
Then return to people, events, places, source review, visual enrichment, and semantic search with a stronger foundation.
```
