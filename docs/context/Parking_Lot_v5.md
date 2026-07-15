# CANONICAL_PARKING_LOT_v5 — Photo Organizer

## Purpose

Track deferred, future, completed, and refinement work while maintaining:

- focus on active milestones

- architectural clarity

- system evolution visibility

- clean separation between active roadmap and deferred ideas

- a durable record of what has been completed, superseded, or intentionally parked

This document is:

- decision-oriented

- de-duplicated

- structured by system area

- limited to incomplete, intentionally deferred, completed/superseded reference items, or future work that may affect architecture

Completed items are retained only when useful to explain why a prior parking-lot item is no longer active.

---

## Current Near-Term Direction

The current near-term priority has changed.

iCloud ingestion is now considered good enough for v1.0 after the unified iCloud Intake work and a successful 1000-logical-asset live run.

The new near-term direction is:

```text
A. Documentation checkpoint
   - project workflow
   - coding-agent rules
   - project context
   - project architecture
   - parking lot
   - milestone history / new-chat handoff as needed

B. Unified external/local/NAS source identity design
   - stop treating drive letter as durable identity
   - define source device / endpoint identity
   - clarify Source Profile vs device identity vs provenance
   - support external drive, thumb drive, optical media, local folder, NAS/network share

C. External/local/NAS intake workflow redesign
   - reuse useful iCloud Intake patterns where appropriate
   - source readiness
   - candidate preparation / scan
   - Source Intake execution
   - result summary
   - Advanced Details

D. v1 hardening and UX simplification
   - ingestion tab simplification
   - binary/near-binary readiness
   - operational history
   - runtime diagnostics
   - BMP preview support

E. Return to curation and enrichment polish
   - people/faces
   - source review
   - timeline/events
   - places
   - visual enrichment
   - non-geolocated asset place assignment
```

---

# 0. Completed / Superseded Since v4

These items were high-priority in v4 but are now completed, absorbed, or superseded by the unified iCloud Intake work.

---

## ~~ICL-CLEAN-001 — Verified iCloud Staging Cleanup Execution~~

### Status

Completed / absorbed into unified iCloud Intake.

### Resolution

Guarded local iCloud staging cleanup execution is now part of the durable iCloud Intake chunk flow. Cleanup still acts only on verified local staging files and preserves the safety boundary:

```text
no remote iCloud deletion
no Vault deletion
no DB record deletion
no provenance deletion
no Source Profile / source registry deletion
```

### Remaining Follow-Up

No separate near-term item needed.

Any future cleanup work should be framed as:

```text
broader local/external/NAS cleanup safety
operational report viewer
iCloud performance/timing refinement
```

---

## ~~ICL-CLEAN-002 — Cleanup / Reacquire / Non-Repeat Validation Loop~~

### Status

Completed / superseded by unified iCloud Intake behavior.

### Resolution

The old concept of separate acquire → intake → cleanup → reacquire validation has been superseded by:

```text
Refresh / Prepare Next 1000
Import Next 1000
durable prepared candidate snapshot
chunked acquisition / Source Intake / guarded cleanup
resume support
remote identity known/unknown accounting
```

The remaining issue is no longer whether cleanup causes repeated simple redownload loops. The remaining future issue is deeper provider-completeness proof and performance/timing refinement.

### Remaining Follow-Up

Tracked under:

```text
ICL-PERF-001 — iCloud Intake Phase Timing and Performance Baseline
ICL-COMPLETE-001 — iCloud Provider Cursor / Exhaustion Completeness
ICL-PROV-001 — Cloud-Native iCloud Provenance
```

---

## ~~ICL-UX-001 — Consolidated Cloud Ingestion Flow~~

### Status

Completed for iCloud.

### Resolution

iCloud now has a unified `iCloud Intake` operator model:

```text
Refresh / Prepare Next 1000
Import Next 1000
```

The normal UI path no longer treats acquisition, Source Intake, and cleanup as separate top-level mental models.

### Remaining Follow-Up

Do not reopen this as an iCloud UX item unless real usage shows a v1 blocker.

The broader unresolved item is:

```text
UX-INGEST-003 — Unified Local / External / NAS Intake Workflow
```

---

## ~~UX-INGEST-002 — Unified Workflow Summary for Acquisition / Intake / Cleanup~~

### Status

Completed for iCloud; still conceptually relevant for other source types.

### Resolution

iCloud Intake now reports current run progress, logical/resource counts, cleanup counts, resume state, retryable failures, and timing summary in one workflow surface.

### Remaining Follow-Up

For non-iCloud sources, fold into:

```text
UX-INGEST-003 — Unified Local / External / NAS Intake Workflow
OPS-001 — Unified Operational History
```

---

## ~~ICL-RECENT-001 — Recent Sync / Historical Split~~

### Status

Superseded.

### Resolution

The product direction is unified iCloud Intake, not separate historical/current user workflows.

Unified rule:

```text
Scan newest-first.
Skip known remote identities.
Prepare/import unknown eligible logical assets.
Record adjusted/ambiguous/unsupported as deferred/needs-policy.
After full source accounting, the same routine naturally imports new/current assets.
```

### Remaining Follow-Up

Only provider completeness and performance remain parked.

---

# 1. Highest-Priority Promotion Candidates

These are the strongest candidates for upcoming milestones after the documentation refresh.

---

## SRC-ID-001 — Unified Source Identity Architecture

### Summary

Define the durable source identity architecture for local folders, external drives, removable media, optical media, NAS/network shares, and cloud-staged sources.

### Current Issue

Current local/external source handling is too dependent on user labels, root paths, or drive letters.

Drive letters can change. User nicknames are display aliases, not reliable identity.

### Desired

Define and document the relationship between:

```text
Source Profile
Source Device / Endpoint
Ingestion Source / Source Registry
Provenance Observation
Observed Mount / Path
Alias / Display Name
```

### Target Model

```text
Source Profile
  = user-facing source/workflow container and editable alias

Source Device / Endpoint
  = machine-readable identity evidence for the thing being ingested

Ingestion Source
  = backend compatibility/source record used by Source Intake and existing provenance systems

Provenance Observation
  = this asset was observed at this source-relative path on this source/device context

Observed Mount / Path
  = where the source appeared during a particular run
```

### Identity Evidence Candidates

```text
device serial number
USB VID / PID
volume serial number
filesystem UUID / volume UUID
optical disc/session metadata
network server/share identity
NAS/share identity
UNC path
observed mount/path history
user alias
```

### Importance

Very high.

This should be the next major design milestone before large external/NAS imports.

---

## SRC-ID-002 — External Drive / Removable Device Identity

### Summary

External drive Source Profiles should represent the physical/logical device, not the temporary Windows drive letter.

### Current Issue

Windows drive letters can change.

A source such as:

```text
External 1
```

should not become a different source just because it mounts as:

```text
D:\
E:\
F:\
```

### Desired

Future model:

```text
Source Profile = user-facing alias, e.g. "Chuck External 1"
Device Identity = volume/device fingerprint
Run Path = current observed mount path + selected root folder
Provenance = source/device/profile-based, with observed path retained
```

### Future Questions

- Which identifiers are reliably available on Windows?

- Can the system capture volume label, volume serial number, filesystem UUID, USB VID/PID, and physical device serial?

- What identity confidence should be assigned to each identifier?

- How should the user confirm a device match?

- How should the user update a mount path without changing source identity?

- Should external drive profiles include expected root folder plus device fingerprint?

- How should two drives with the same volume label be disambiguated?

### Importance

Very high before large external imports.

---

## SRC-ID-003 — Local Folder Identity

### Summary

Define how local folders on an internal computer should be represented.

### Current Issue

The external-drive identity model may not directly apply to local folders.

A local path such as:

```text
C:\Users\Chuck\Pictures
```

is partly:

```text
computer identity
volume identity
folder path
```

not necessarily a removable source.

### Desired

Define local-folder identity as a combination of:

```text
host/computer identity, if available
volume identity
root path
Source Profile alias
observed scan path
```

### Questions

- Should local folder identity be path-based or device+path-based?

- How should folder moves be handled?

- Should a local folder be allowed to migrate to a NAS path while preserving source identity?

- How should provenance reflect local path changes?

- What information is safe and useful to store?

### Importance

High.

Needed before unifying local and external workflows.

---

## SRC-ID-004 — NAS / Network Share Source Identity

### Summary

Define source identity for NAS folders and network shares.

### Current Issue

A NAS or network share may be mounted as:

```text
Z:\
\\NAS\Photos
\\192.168.1.10\Photos
```

These can all represent the same source, but they are not the same string.

### Desired

Represent NAS/network identity using evidence such as:

```text
server name
server address
share name
UNC path
NAS volume/share identity if available
observed mapped drive letter
authenticated user, if safely useful
root folder within share
Source Profile alias
```

### Questions

- Should a mapped network drive be normalized to UNC?

- How should IP vs hostname differences be reconciled?

- How should NAS share rename/move be handled?

- Can Synology expose stable share or volume identifiers that are useful?

- Should NAS source identity include credentials?  
  Desired answer: no secrets; only non-secret identity/status if needed.

### Importance

Very high for production/NAS-backed workflows.

---

## SRC-ID-005 — Provenance Model for Source Device / Endpoint Identity

### Summary

Clarify how new source identity records should connect to existing provenance.

### Current Issue

Existing provenance is source/path-oriented. Future identity should preserve explainability while avoiding drive-letter dependence.

### Desired

Provenance should answer:

```text
Which asset?
Observed from which source profile?
On which device/endpoint/volume/share?
At what source-relative path?
During which intake run?
Using which observed mount/path?
```

### Requirements

- Do not delete or rewrite historical provenance casually.

- Preserve compatibility with existing Source Intake.

- Additive schema preferred.

- Backfill/migration must be non-destructive.

- Existing provenance should remain explainable.

- User-facing aliases must be editable without corrupting provenance.

### Importance

Very high.

This should be part of the source identity design milestone or its immediate follow-up.

---

## UX-INGEST-001 — Guided Source Profile / Ingestion Tab Simplification

### Summary

Simplify the Ingestion tab and Source Profile workflow.

### Current Issue

The current UI exposes too many technical fields and repeated details:

```text
normalized label
effective path
source root compatibility identity
managed staging path
source registration
operational conflicts
blocking reasons
warnings
run IDs
report paths
cleanup counters
multiple refresh/status areas
```

### Desired

A simplified user-facing model:

```text
Source
Readiness
Prepare / Scan
Action
Progress
Result
Next safe action
Advanced Details
```

### Specific UX Direction

- Readiness should be binary or near-binary:
  
  - Ready
  
  - Blocked
  
  - Unknown
  
  - Needs Review
  
  - Resume Available

- Warnings should become:
  
  - automatic fixes,
  
  - blockers,
  
  - or Advanced Details.

- Technical path/identity fields should move to Advanced Details.

- “Recommended Next Action” should be accurate and state-based.

- Source identity warnings should be understandable to non-programmer operator.

### Importance

Very high.

This remains a major v1 usability item.

---

## UX-INGEST-003 — Unified Local / External / NAS Intake Workflow

### Summary

Apply useful iCloud Intake lessons to local, external, and NAS source workflows where appropriate.

### Desired

The backend may differ, but the UI grammar should feel consistent:

```text
Select Source
Check Readiness
Prepare / Scan Candidates
Import / Source Intake
Review Result
Advanced Details
```

### Key Question

Should local/external/NAS intake use a prepared candidate snapshot like iCloud?

Possible answer:

```text
For small/local runs: maybe not required.
For large external/NAS runs: likely useful.
```

### Desired Outcome

A user should not need to understand whether a source is:

```text
local folder
external USB drive
thumb drive
optical disc
NAS share
cloud-staged source
```

to understand the workflow.

### Importance

Very high after source identity design.

---

## PREVIEW-001 — BMP Display Preview Support

### Summary

Add BMP files to the display-safe/review preview generation pipeline.

### Current State

HEIC/HEIF and TIFF preview handling exist. BMP files need display-safe/review processing.

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

Port `8001` remained in LISTENING state with nonexistent PID even after:

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

High before larger test environment or v1 production-like deployment.

---

# 2. iCloud / Cloud Acquisition Track

iCloud Intake is currently good enough for v1.0. Items in this section are future refinements, not near-term blockers unless real usage exposes a new issue.

---

## ICL-PERF-001 — iCloud Intake Phase Timing and Performance Baseline

### Summary

Break the observed iCloud Intake runtime into meaningful phases.

### Current Observation

A full iCloud Intake run completed successfully.

Rough baseline:

```text
100 logical assets ≈ 10 minutes
1 logical asset ≈ 6 seconds
1000 logical assets ≈ 100 minutes
```

### Desired

Record clearer phase timing for:

```text
iCloud helper/listing/re-resolution
download/staging
Source Intake
Vault / DB / provenance writes
cleanup dry run
cleanup execution
inter-chunk orchestration gap
```

### Current Limitation

The current durable chunk ledger has timing fields, but lower-level acquisition does not yet expose precise sub-phase timings.

### Importance

Medium.

Parked. Not required for v1 unless performance becomes a blocker.

---

## ICL-COMPLETE-001 — iCloud Provider Cursor / Exhaustion Completeness

### Summary

Improve the system’s ability to prove iCloud source exhaustion or continue deeper through provider inventory.

### Current State

Unified iCloud Intake can scan newest-first, skip known identities, and prepare unknown eligible candidates.

There is still no persisted provider cursor/page-token/date-boundary continuation.

### Desired

Support a stronger completeness strategy such as:

```text
provider cursor
page token continuation
date boundary
until-found style continuation
known-boundary strategy
```

### Questions

- Does `icloudpd` or helper expose reliable cursor/page behavior?

- Should Photo Organizer maintain its own checkpoint?

- How should the UI distinguish:
  
  - source exhausted
  
  - likely caught up
  
  - scan ceiling reached
  
  - unknown completeness

- What should count as “known”?
  
  - remote identity seen
  
  - provenance exists
  
  - Vault asset exists
  
  - acquisition completed

### Importance

Medium.

Useful, but not required for v1 given current successful intake behavior.

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

Medium-high before scheduled or unattended cloud acquisition.

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

Medium.

Useful troubleshooting improvement.

---

## ICL-PROV-001 — Cloud-Native iCloud Provenance

### Summary

Extend provenance to include iCloud-specific remote identity where available.

### Desired

Capture additional cloud-native provenance such as:

```text
remote iCloud asset ID / stable helper item id
Apple account/source identity, non-secret
icloudpd run ID
download timestamp
download method
original iCloud filename
Live Photo resource relationship
resource roles
```

### Importance

Medium-high.

Useful for future cloud synchronization, account migration, and explainability.

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

## ICL-005 — iCloudPD Advanced Options

### Summary

Expose safe advanced `icloudpd` options.

### Candidate Options

```text
--until-found
--album
--folder-structure
include/exclude videos
Live Photo related flags
size/original options
```

### Importance

Low-medium.

Only after core v1 workflows settle.

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

Lower priority than acquisition correctness and source identity.

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

Medium.

Only after lifecycle polish and cleanup safety are trusted.

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

Improve progress reporting for large local, external, NAS, or cloud source folders.

### Importance

Medium-high for large real-world imports.

---

## IN-004 — Prepared Candidate Pattern for Large Local / External / NAS Sources

### Summary

Investigate whether large local/external/NAS intake should use a prepared-candidate snapshot similar to iCloud.

### Desired

For large source runs:

```text
scan/prepare exact candidate set
review candidate readiness
import through Source Intake
record durable progress
resume safely if interrupted
```

### Importance

High after source identity design.

---

## OPS-001 — Unified Operational History

### Summary

Create a unified operational view showing source/profile workflows across acquisition, intake, cleanup, and post-intake jobs.

### Desired

The system can show:

```text
Source Profile
→ candidate preparation / scan, if applicable
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

### Desired

After intake completes, suggest or run:

```text
display preview generation
Live Photo pairing
duplicate processing
face detection
place geocoding
visual enrichment
semantic indexing
```

### Importance

High after ingestion/source identity stabilizes.

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

### Desired

A user should be able to correct or review major photo facts in one place:

```text
date/time trust
people/faces
place/location
event
album/collection
source/provenance
duplicate/canonical status
visibility/demotion
metadata notes
```

### Importance

High after ingestion/source identity stabilization.

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

### Candidate Workflows

```text
face assignment
duplicate adjudication
date trust review
place assignment
visual enrichment acceptance/rejection
```

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
source/device/profile
import run
needs preview
needs post-intake processing
```

### Importance

Medium-high.

---

## SEARCH-004 — Photo Review Search Hierarchy and Search Bar Improvements

### Summary

Revisit Photo Review search/filter behavior to support smarter hierarchical filtering and less rigid search behavior.

### Desired

- clearer hierarchy between global search and facet filters

- better filename/path/source search behavior

- saved search or smart collection potential

- easier filtering by source, event, place, person, date, media type, and quality state

### Importance

Important before production-level usability.

---

## UX-007 — Collection Polish

### Summary

Defer Collection UI/UX polish until broader Source Review / Album / Collection workflow has more real usage and testing.

### Priority

Deferred.

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

# 5. Face / Identity System

---

## ID-001 — Create Cluster from Face

Allow user to create a new cluster/person workflow from an individual unassigned face.

### Importance

Medium.

---

## ID-002 — Friendlier Cluster Selection

Improve UI for selecting or moving faces between clusters.

### Importance

Medium.

---

## ID-003 — Representative Faces

Allow users to choose representative face thumbnails for people or clusters.

### Importance

Medium.

---

## ID-004 — Cluster Confidence Signals

Show confidence/quality indicators for clusters and suggested identities.

### Importance

Medium-low.

---

## FW-001 — Bulk Face Actions

Support bulk operations on selected faces.

### Importance

Medium.

---

## FW-002 — Suggested Cluster Improvements

Improve cluster suggestions and assignment flow.

### Importance

Medium.

---

## FW-003 — Face Comparison Tool

Allow side-by-side comparison of faces/clusters/person candidates.

### Importance

Medium.

---

## FW-004 — Suggestion Dismissal System

Allow user to dismiss incorrect face/person suggestions.

### Importance

Medium.

---

## FW-005 — Large Image Face Assignment Mode

Add a larger-image face assignment mode for photos where thumbnail/card overlays are too small.

### Importance

Medium-high for real-world family archive review.

---

## FACE-005 — Backfill Protected Manually Unassigned Faces

Backfill and protect manually unassigned faces so later processing does not undo the user’s decision.

### Importance

Medium.

---

## FACE-006 — Face Review Visual Polish and Cluster Thumbnail Cards

Improve Face Review scannability after more real-world usage.

### Importance

Medium.

---

## FACE-007 - Multi-Prototype Person / Cluster Consolidation

Large manually merged face clusters can contain the same person across different ages, lighting, poses, hairstyles, and image qualities. A single averaged cluster centroid can become a poor matcher for any one appearance period, causing later face-processing runs to create new similar-looking fragment clusters instead of assigning them to the established reviewed/person cluster.

Future improvement: add a post-run consolidation/review pass that compares new or unreviewed clusters against existing clusters and person-linked appearance prototypes. For a reviewed person or heavily merged cluster, preserve multiple internal prototype centroids rather than relying only on one blended centroid.

### Desired

```text
Person identity can have multiple appearance prototypes.
New/unreviewed clusters are compared to each prototype.
High-confidence, non-ambiguous matches can be suggested for merge/consolidation.
Reviewed/person-linked clusters are preferred as consolidation targets.
Blind transitive merges are avoided unless the group is internally coherent.
```

### Triggering Observation

During face review, cluster `225` appeared visually similar to established merged cluster `661`, but the current single-centroid comparison scored below the assignment threshold. The same cluster was much closer to several smaller unreviewed fragments, suggesting a missing post-run cluster-fragment consolidation step rather than simple first-pass assignment failure.

### Importance

Medium-high for family archives with the same people across many life stages.

---

## FACE-008 - Face Modal Full-Image Context Preview Contract

In Face Clusters and Unassigned Faces, clicking a face thumbnail can open a modal that hangs on `Loading full image context...` for some HEIC-backed assets. The same asset may have a working face thumbnail, a working Photo Review full-image display, and a working Photo Detail response, which suggests the issue is specific to the face workflow/modal display path rather than missing media or missing photo detail data.

Future improvement: make the face full-context modal follow the same centralized display URL contract used by Photo Review and Photo Detail. The modal should prefer `display_url` / `image_url` from `PhotoDetail`, avoid raw original HEIC/HEIF/TIFF image fallbacks in browser `<img>` elements, and show a clear unavailable/error state instead of an indefinite loading message.

### Desired

```text
Face modal uses generated display previews for non-browser-safe originals.
Face modal does not attempt raw HEIC/HEIF/TIFF fallback as a full-image source.
If no display preview is available, show the face crop and a clear full-image-unavailable message.
Apply the behavior consistently in FaceGrid and UnassignedFacesView.
Keep face highlight overlay when a display preview and matching face bbox are available.
```

### Triggering Observation

An HEIC-backed face example was reported as hanging in the Face Clusters full-context modal while thumbnail, Photo Review full-image display, and Photo Detail were otherwise available.

### Importance

Medium for face review usability.

---

# 6. Location / Places / Non-Geolocated Assets

---

## PL-001 — Location Intelligence Master Track

Expand location intelligence beyond reverse geocoding.

### Importance

Medium.

---

## PL-002 — Location Filtering

Add richer location filters.

### Importance

Medium.

---

## PL-003 — Place Normalization

Resolve inconsistent or duplicate place names.

### Importance

Medium-high.

---

## PL-004 — Missing Location Handling

Define and expose behavior for assets without GPS/location.

### Importance

Medium-high.

---

## PL-005 — Provenance vs Location Reconciliation

Resolve cases where source/provenance location and GPS/geocoded location imply different places.

### Importance

Medium.

---

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

### Importance

Medium-high after source identity redesign.

---

## SR-002 — Source Review by Device / Endpoint

### Summary

Once source device/endpoint identity exists, add source review views based on actual device/source identity rather than only labels or paths.

### Desired

Review assets by:

```text
Source Profile
Device / Endpoint
Volume / Share
Import run
Observed folder path
Original source-relative path
```

### Importance

Medium-high.

---

## CO-001 — Event ↔ Album Integration

Enable event-to-album workflows.

### Importance

Medium.

---

## CO-002 — Collections System Expansion

Define whether albums, collections, smart collections, and saved filters should become a unified collection system.

### Importance

Medium.

---

## EV-001 — Event Date Range Consistency

Ensure date range recalculation is consistent across merge, assign, remove, manual correction, and incremental clustering.

### Importance

Medium.

---

# 8. Media / Video / Live Photo

---

## MV-001 — Live Photo Playback UI

Add Apple-like or simplified playback for paired Live Photos.

### Importance

Medium.

---

## MV-002 — Live Photo Motion Companion Filtering

Allow UI to hide or filter Live Photo motion companion MOV files.

### Importance

Medium.

---

## MV-003 — Video Canonicalization Recompute Parity

Bring video support into any remaining canonical metadata recompute paths that are still image-only.

### Importance

Medium.

---

## MV-004 — Video Strategy / Playback System

Define full video handling strategy.

### Importance

Medium-high.

---

## MV-005 — Legacy Camcorder Format Support

Evaluate support for older video formats.

### Importance

Medium.

---

# 9. Duplicate System

---

## DUP-001 — Hamming Distance Threshold Tuning

Tune pHash Hamming distance thresholds for near-duplicate detection.

### Importance

Medium.

---

## DUP-002 — Duplicate Group Review Improvements

Improve duplicate review usability.

### Importance

Medium.

---

## DUP-003 — Cross-Format Detection Gap

Improve detection across HEIC/JPG/PNG/TIFF/video derivatives where pHash or metadata differs.

### Importance

Medium-high.

---

## DUP-004 — Cross-Format Auto Grouping

Explore safe auto-grouping for likely cross-format duplicates.

### Importance

Medium.

---

## DUP-005 — Multi-Signal Duplicate Scoring

Combine multiple signals beyond pHash.

### Importance

Medium.

---

## DUP-006 — Canonical Asset Locking

Support optional canonical “lock” behavior where user-selected canonical assets are preserved.

### Importance

Medium.

---

# 10. Demotion / Visibility

---

## DS-001 — Non-Duplicate Demotion

Allow reversible demotion of non-duplicate unwanted assets.

### Importance

Medium.

---

## DS-002 — Demoted Asset Management

Provide UI to view and restore demoted assets.

### Importance

Medium.

---

# 11. Deployment / Mini-Server / NAS / Scheduling

---

## DEPLOY-002 — Production Bootstrap / Runtime Validation

Validate the production bootstrap foundation against the real mini-server/NAS-backed production path before real production archive ingestion.

### Importance

High.

---

## NAS-001 — NAS Storage Readiness Plan

Prepare NAS-backed durable media storage.

### Desired

- Vault/media path strategy

- NAS mount reliability

- performance validation

- backup/snapshot plan

- restore test

- avoid live PostgreSQL DB on mapped NAS share unless specifically validated

### Importance

High.

---

## SCHED-001 — Scheduled iCloud Acquisition / Intake

Run iCloud acquisition/intake automatically on mini-server or always-on host.

### Current Status

Deferred.

Unified iCloud Intake works manually. Scheduling should wait until v1 operator workflows and deployment environment are stable.

### Importance

Medium.

---

## SCHED-002 — Scheduled Source Processing

### Summary

Schedule non-cloud post-intake/background work.

### Candidate Jobs

```text
display previews
duplicates
face processing
place geocoding
visual enrichment
semantic indexing
```

### Importance

Medium.

---

# 12. Intelligence / AI Long-Term

---

## AI-001 — Semantic Search Expansion

Improve natural-language and semantic search over assets.

### Importance

Medium-high after mini-server and source identity foundation.

---

## AI-002 — Landmark / Scene Intelligence

Identify landmarks, venues, or meaningful scenes beyond reverse geocoding.

### Importance

Medium.

---

## AI-003 — Physical Media Detection Suggestions

Use visual signals to suggest likely scanned/photographed physical media.

### Importance

Medium-high for date trust workflows.

---

## AI-004 — EXIF / Metadata Inference Assistance

Explore assisted inference for missing dates or metadata.

### Importance

Medium.

---

## AI-005 — Local AI Service Boundary

Define how local AI services should run on the mini-server.

### Desired

- service boundaries

- GPU/CPU fallback

- model storage

- job scheduling

- privacy guarantees

- API boundaries

- resource limits

### Importance

High before substantial local-AI work.

---

# 13. Repository / Workspace Housekeeping

The v4 parking lot included a full repository/workspace surface audit prompt as a deferred stabilization task. The task remains valid, but it should not derail feature development. It is reorganized here as a normal parking-lot item rather than raw prompt text.

---

## REPO-001 — Full Repository / Workspace Surface Audit for v1 Stabilization

### Summary

Perform a full repository and workspace audit before v1 to reduce clutter, improve developer/agent reliability, clarify project structure, and reduce the chance that humans, VS Code, Copilot/Codex, or tests are distracted by stale/generated/irrelevant files.

### Scope

Evaluate both:

```text
1. Git repository bloat:
   files actually tracked by Git

2. Workspace bloat:
   ignored/untracked/generated/local files that still exist in the project folder and may affect VS Code, search, indexing, agent context, or developer confusion
```

### Core Principle

Use program relevance, not Git tracking status alone.

A file or folder should be kept only if it is:

```text
required by runtime
required by tests
required as intentional test fixture
required as current documentation
required as final milestone/project history
required for local development setup as a safe template
```

Otherwise classify as:

```text
DELETE CANDIDATE
ARCHIVE CANDIDATE
MOVE CANDIDATE
IGNORE CANDIDATE
NEEDS USER DECISION
```

### Initial Boundary

Reconnaissance only.

Do not:

```text
delete files
move files
edit code
edit docs
edit .gitignore
run destructive cleanup commands
commit or tag
rewrite Git history
expose secret values
```

Reports may list environment variable names, but never values.

### Audit Areas

- workspace size breakdown

- Git-tracked surface

- ignored/untracked workspace surface

- `.gitignore` findings

- VS Code / agent indexing findings

- Python code hygiene

- Python dependency audit

- frontend dependency/build artifact audit

- docs audit

- test fixture/media audit

- branch/tag audit

### Desired Output

A Markdown report answering:

```text
Are local files mostly expected dependency/runtime files?
How many files are actually tracked by Git?
Are generated/log/export/storage files safely ignored?
Are stale docs or generated artifacts confusing agents/humans?
Are tracked files present that should clearly be deleted or moved?
Is VS Code/Copilot likely indexing too much noise?
Are unused Python files/functions/dependencies worth later review?
What cleanup should happen now vs later?
```

### Importance

Medium-high before v1, but not active until explicitly promoted.

---

# 14. Working Priority Stack

Current recommended priority stack:

```text
1. Documentation checkpoint
   - workflow
   - coding-agent rules
   - project context
   - project architecture
   - parking lot
   - milestone history / new-chat handoff if needed

2. Unified external/local/NAS source identity architecture
   - Source Profile vs Source Device / Endpoint
   - provenance relationship
   - aliases vs durable identity
   - external drive / removable / optical / NAS / local folder identity

3. External drive identity independent of drive letter

4. NAS / network share identity

5. Local folder identity and provenance behavior

6. Unified local/external/NAS intake workflow design

7. Guided Source Profile / Ingestion Tab simplification

8. Large-source candidate preparation / progress / resume model

9. BMP display-preview support

10. Runtime ghost-listener diagnostics

11. Mini-server + NAS deployment architecture

12. Post-intake review-readiness checklist / job recommendations

13. Undated/date-trust/photo-review filters

14. Source Review / Timeline / Events refinement

15. Places for non-geolocated assets

16. People/Face workflow tuning

17. Visual enrichment refinement

18. Semantic search / local AI expansion

19. iCloud phase timing / performance baseline, if performance becomes important
```

Guiding decision:

```text
iCloud Intake is good enough for v1.
Move on to source identity, external/local/NAS intake, and v1 operator clarity.
```

---

# 15. Items Explicitly Not Near-Term

These are valid but should not distract from source identity and v1 hardening.

```text
iCloud performance optimization beyond rough baseline
iCloud multi-account support
iCloud album/favorites/people metadata
scheduled unattended iCloud intake
advanced semantic search UX
mobile web client
external sharing/access control
Live Photo playback
large video playback UX
multi-provider cloud expansion
```

---

# 16. Parking Lot Maintenance Rules

When an item is completed:

- strike it through if it is useful to preserve historical context

- otherwise remove it in the next cleanup pass

- note the milestone/commit if known

- move remaining follow-up work into a new focused item

When an item is promoted:

- create a formal prompt with exact prompt/closeout filenames

- start the new milestone arc at `xx.xx.0`

- keep the prompt file as the active instruction record

- do not turn the Parking Lot itself into a prompt unless explicitly requested

When an item becomes too large:

- split into design/reconnaissance first

- then implementation milestones

- avoid combining schema, UX, migration, and destructive behavior in one prompt unless explicitly planned

When an item is stale:

- reclassify as deferred, superseded, or delete candidate

- do not keep obsolete near-term priorities active
