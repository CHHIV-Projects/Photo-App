# Milestone 12.26 — iCloud Export Intake Design

## Goal

Define the project’s first iCloud intake strategy using **local iCloud export/download folders**, not direct iCloud API integration.

This is a **design-first milestone**.

The goal is to clearly define how iCloud-origin photos should enter the system using:

- source registry
- Admin-launched intake
- HEIC support
- MOV/video preservation
- background enrichment
- existing provenance model
- source intake reporting
- future cloud-readiness concepts

---

## Context

The system now has the required foundation for controlled iCloud-origin intake:

- HEIC/HEIF viewing support via generated previews
- MOV/video preservation as unsupported/stored media
- Admin source registry
- explicit source labels
- source label reuse controls
- Admin-launched source intake
- source intake limits
- ingest batch size controls
- skip-known logic using:

```text
ingestion_source_id + source_relative_path
```

- source intake reports
- background enrichment for:
  - duplicate processing
  - place geocoding
  - face processing
  - HEIC preview generation

Direct iCloud API integration is intentionally deferred.

---

## Core Decision

For the first iCloud intake implementation, use:

```text
iCloud export/download folder intake
```

Do NOT implement:

```text
direct iCloud API / cloud connector intake
```

in this milestone.

---

## Core Principle

> Treat iCloud export/download folders as controlled local sources first. Preserve originals. Avoid cloud-auth complexity until the local export workflow is proven.

---

## Architecture Position

The iCloud export-folder workflow is not throwaway.

It should be treated as a valid long-term source type within the broader source intake framework.

Long-term source intake architecture should support:

```text
Source Intake Framework
│
├── Local Folder Source
├── External Drive Source
├── Cloud Export Folder Source
└── Future Direct Cloud Connector
```

The export-folder workflow remains useful even if direct iCloud/API intake is implemented later.

---

## Direct iCloud API Deferral

Direct iCloud API / PyiCloud-style integration is deferred.

Reason:

- Apple authentication is complex
- 2FA/session handling adds risk
- credential/token storage requires security design
- provider behavior may change
- direct API introduces cloud identity and retry complexity
- current source-intake architecture can already support controlled local exports

Future direct iCloud connector should not bypass source intake.

Future direct API concept:

```text
iCloud connector
→ controlled download/staging area
→ source intake framework
→ Drop Zone / Vault / DB
```

The connector may eventually bypass the manual export-folder step, but it should not bypass:

- source identity
- batch limits
- skip-known behavior
- hashing
- deduplication
- provenance
- failure routing
- reports

---

## Definitions

### iCloud Export Folder

A local folder containing files downloaded/exported from iCloud Photos.

Examples:

```text
C:\Users\chhen\Pictures\iCloud Export
D:\iCloud Photos Export
/volume1/photo_sources/icloud_export
```

This folder may contain:

- HEIC / HEIF images
- JPG / JPEG images
- MOV video files
- MP4 video files
- PNG or other image derivatives
- possible sidecar files
- Live Photo HEIC + MOV pairs

---

### Unmodified Original

The preferred archival input.

For Apple/iCloud workflows, this generally means the original photo/video file as captured or stored by iCloud, rather than an edited/exported derivative.

Examples:

```text
IMG_1234.HEIC
IMG_1234.MOV
```

Preferred over:

```text
IMG_1234.JPG
Edited_IMG_1234.JPG
```

when the goal is archival intake.

---

### Export / Acquisition

The process of getting files out of iCloud and into a local/export/staging folder.

Examples:

- iCloud for Windows download
- Apple Photos export
- iCloud web download
- future direct connector download

---

### Intake

The Photo Organizer process that scans a local source folder, applies source limits / batch limits / skip-known logic, and ingests files into Vault/DB/provenance.

---

## Scope

### In Scope

- define recommended iCloud export-folder workflow
- define source labeling convention for iCloud exports
- define source type usage
- define how HEIC, MOV/video, and JPG files should be treated
- define how Live Photo pairs should be handled for now
- define expected metadata behavior and known limitations
- define retry/deferred behavior for unavailable files
- define iCloud export reliability / acquisition tracking concerns
- define what the next implementation milestone should build
- define operator instructions for preparing an iCloud export folder

### Out of Scope

- direct iCloud API integration
- Apple login/authentication
- OAuth/session/token handling
- direct cloud downloads
- cloud asset IDs
- iCloud album sync
- Apple Photos library database parsing
- Live Photo pairing implementation
- video playback implementation
- edited-photo reconciliation
- sidecar/XMP ingestion
- mobile app behavior
- automated scheduling
- full iCloud download manager

---

## Required Design Decisions

---

### 1. Intake Method

Approved first method:

```text
local iCloud export/download folder
```

The operator is responsible for placing iCloud-origin files into a local folder visible to the backend.

The system then ingests that folder using existing Admin-launched source intake.

---

### 2. Source Registration

iCloud export folders should be registered through the existing Admin Source Registry.

Recommended source type:

```text
cloud_export
```

Recommended source label examples:

```text
chuck_icloud
audrey_icloud
family_icloud_shared
```

The source label should represent the iCloud account/library/source family, not a temporary folder name.

The source root path identifies the specific backend-visible export folder.

Example:

```text
Source Label: chuck_icloud
Source Type: cloud_export
Root Path: C:\Users\chhen\Pictures\iCloud Export 2026
```

---

### 3. Multiple iCloud Accounts

Multiple iCloud accounts/libraries should be represented as separate source labels.

Examples:

```text
chuck_icloud
audrey_icloud
family_shared_icloud
```

This prevents provenance confusion and avoids accidental mixing of sources.

---

### 4. Repeat Intake Behavior

Use existing source intake behavior:

```text
known source file =
ingestion_source_id + source_relative_path
```

For local export folders, this means repeated intake sessions from the same registered source will skip already-ingested source-relative paths.

This is acceptable for the first iCloud export-folder workflow.

Limitations:

- if the same export is downloaded into a different root path, it becomes a different registered source unless intentionally registered otherwise
- if files are renamed or reorganized before intake, relative-path-based skip-known may not recognize them as already known
- SHA256 exact dedupe remains the final safety net
- additional provenance may be recorded if the same file appears from a different source/path

---

### 5. File Format Handling

#### HEIC / HEIF

Behavior:

- ingest as image asset
- preserve original unchanged in Vault
- generate JPEG preview through existing HEIC preview process
- metadata extraction/canonicalization should run normally
- participate in duplicate processing where supported
- support face processing through existing HEIC-compatible image loading

#### JPG / JPEG

Behavior:

- ingest normally
- preserve original unchanged
- participate in existing metadata/duplicate/preview behavior

#### MOV / MP4 / Video

Behavior:

- ingest/store consistently with current system behavior
- preserve in Vault
- treat as unsupported/video media for now
- do not attempt full video playback or interpretation in this milestone

#### Sidecar / XMP / Unknown Files

For design:

- do not implement sidecar ingestion yet
- if current filter rejects unsupported files, route according to existing ingest failure behavior
- preserve future parking-lot item for sidecar handling if needed

---

### 6. Live Photo Handling

For this phase, do NOT implement Live Photo pairing.

Current behavior should be:

```text
IMG_1234.HEIC → image asset
IMG_1234.MOV  → stored video/unsupported asset
```

Do not yet create a unified Live Photo object.

However, the design should preserve enough context for later pairing where practical:

- source label
- source-relative path
- original filename
- basename
- capture timestamp
- provenance records
- file extension
- source folder relationship

Future Live Photo milestone should evaluate pairing by:

- same basename
- same source folder
- matching/nearby timestamps
- Apple metadata if available
- HEIC/MOV companion roles

---

## Metadata Expectations

Preferred input is unmodified originals because they are most likely to preserve:

- original capture timestamp
- camera/device metadata
- GPS coordinates
- dimensions
- original format

Known metadata limitations of export-folder intake:

- filesystem created/modified date may reflect download/export date
- Apple Photos album membership may not be embedded
- Apple People/Faces labels likely do not transfer usefully
- edits/favorites/shared-library context may not be preserved
- Live Photo pairing is not yet represented
- sidecars may be ignored for now
- edited exports may have different or weaker metadata than unmodified originals
- portrait/depth/HDR semantics may not be fully represented

The system should continue relying on:

```text
metadata observations + canonicalization
```

rather than filesystem timestamps alone.

---

## Provenance Considerations

The current export-folder provenance model is acceptable for the first iCloud workflow:

```text
source label + source type + root path + relative path
```

However, future direct cloud/API intake may require stronger cloud-native provenance.

Potential future cloud provenance fields:

- provider
- cloud account/source label
- remote asset ID
- remote version ID
- original filename
- exported/staged path
- asset role:
  - original
  - edited derivative
  - sidecar
  - video companion
- relationship to local Vault asset

### Known Provenance Risks

#### Export Path Instability

The same iCloud file may appear under different local export paths across downloads.

Example:

```text
C:\iCloud Export 2026\IMG_1234.HEIC
D:\iCloud Export Backup\Vacation\IMG_1234.HEIC
```

This may produce additional provenance records.

SHA256 exact dedupe remains the safety net.

---

#### Export Method Differences

Different export methods may produce different files for the same visual image:

```text
unmodified HEIC
edited JPG
resized export
sidecar-adjusted version
```

These may not hash the same and may become separate assets or near-duplicates.

This is acceptable for now and should be handled later by duplicate/canonical workflows.

---

#### Live Photo Split

HEIC and MOV Live Photo components are separate provenance records until Live Photo pairing exists.

This is acceptable for now.

---

#### Multiple iCloud Libraries

The same photo may appear in multiple iCloud accounts/shared libraries.

Different source labels should create distinct source identities.

Same SHA256 may have multiple provenances.

This is desired behavior.

---

## iCloud Export Reliability / Acquisition Tracking

Large iCloud exports/downloads may be unreliable or incomplete.

Observed/expected issues:

- download pauses or stalls
- partially downloaded files
- placeholder/cloud-only files
- locked files
- files appearing before fully written
- interrupted export sessions
- duplicate retry attempts
- inconsistent folder completion state

### Design Requirement

The iCloud export-folder workflow must distinguish between:

```text
acquisition state
```

and:

```text
intake state
```

Acquisition state means whether the file has been successfully downloaded/exported and is ready for intake.

Intake state means whether the Photo Organizer has successfully ingested the file into Vault/provenance.

---

### Recommended Future Folder Model

Consider a staged export layout:

```text
icloud_export_source/
  incoming/   # iCloud/export tool writes here
  ready/      # files confirmed stable/readable
  failed/     # acquisition or readiness failures
```

For early implementation, this folder split may be optional, but the design should preserve the concept.

---

### Stable File Readiness Rules

Before a file is selected for intake, future logic should be able to verify:

- file exists
- file size is greater than zero
- file size is unchanged across a configurable interval
- file can be opened/read
- file is not locked
- file extension is allowed
- file is not a known temporary/partial download artifact

If a file fails readiness checks:

```text
do not mark it as ingested
do not create provenance
do not move it to Vault
leave it eligible for retry
report it as deferred/unready
```

---

### Pause / Restart Behavior

The system should support repeated export/intake cycles.

If iCloud export pauses or fails:

- already ingested files remain known via provenance
- incomplete/unready files remain eligible for later retry
- source intake reports should distinguish:
  - skipped known
  - selected
  - ingested
  - failed
  - deferred/unready

---

### Operator Visibility

Future Admin/source intake reports should show:

- files scanned
- files ready
- files deferred/unready
- files failed
- files ingested
- remaining unknown
- latest intake/export attempt

The operator should be able to answer:

```text
Did intake fail because the file was bad,
or because iCloud had not fully downloaded it yet?
```

---

### Scope Boundary for Reliability

For 12.26, this is design guidance only.

Do not implement a full iCloud download manager yet.

Do not implement direct iCloud API pause/resume yet.

But the next implementation milestone should consider adding readiness/deferred classification for export-folder intake if current failure handling cannot clearly distinguish incomplete cloud files.

---

## Production Operating Model

The eventual production model should be semi-parallel but controlled.

### Recommended Two-Stage Model

```text
Stage 1 — Acquisition / Export
  iCloud or export tool downloads files into export/staging folder

Stage 2 — Source Intake
  Photo Organizer ingests only files that are stable/ready
```

The two stages may run independently, but intake should only process files that are complete and readable.

---

### Serial vs Semi-Parallel

#### Fully Serial

```text
download/export entire iCloud library
then ingest all files
```

Pros:

- simplest
- fewer partial-file issues

Cons:

- slow
- large staging footprint
- poor for ongoing production

---

#### Fully Parallel

```text
download and ingest at the same time without coordination
```

Pros:

- fastest theoretical throughput

Cons:

- risk of ingesting half-downloaded files
- locked-file failures
- confusing reports
- harder troubleshooting

---

#### Recommended: Semi-Parallel

```text
export/download runs continuously or in batches
intake scans only files that appear stable/complete
```

This is the preferred long-term direction.

---

## Operator Workflow

Recommended first workflow:

```text
1. Download/export iCloud originals into local folder
2. Register source in Admin:
   - label: chuck_icloud
   - type: cloud_export
   - root path: <local export folder>
3. Run Admin source intake:
   - source intake limit: operator-selected
   - batch size: operator-selected
4. Run / allow background jobs:
   - HEIC preview generation
   - duplicate processing
   - face processing
   - place geocoding
5. Review source intake report
6. Repeat source intake as needed
```

---

## Design Questions for Coder

Coder should inspect current implementation and answer:

1. Does current source type vocabulary already include `cloud_export`?
2. Do HEIC/MOV/JPG files from an iCloud export folder currently pass the source scanner/filter correctly?
3. Are MOV/video files currently preserved consistently in Vault?
4. Are unsupported sidecar files routed safely?
5. Does source intake reporting include enough file-format breakdown to validate iCloud export intake?
6. Does current Admin Source Registry support `cloud_export` cleanly?
7. Does current failure handling properly distinguish unreadable placeholder files from unsupported files?
8. Are there any current assumptions that source type `cloud_export` behaves differently from `local_folder`?
9. Does the current scanner risk selecting files that are still downloading or unstable?
10. Does current failure routing clearly distinguish:
    - unsupported
    - unreadable
    - locked
    - hash failure
    - copy failure
    - suspected placeholder/unready
11. What minimal implementation is needed for 12.27?
12. What should remain deferred?

---

## Proposed Output of This Milestone

This milestone should produce a design decision document / implementation plan for 12.27.

The design should answer:

- how operator prepares iCloud export folder
- how source should be registered
- what source type to use
- what formats are accepted
- what formats are deferred/unsupported
- how unavailable files behave
- how repeated intake works
- how Live Photos are treated for now
- how acquisition reliability issues are handled or deferred
- what 12.27 must implement
- what remains parked

---

## Proposed 12.27 Implementation Scope

Likely next implementation milestone:

```text
12.27 — iCloud Export Folder Intake Compatibility
```

Expected scope:

- ensure `cloud_export` source type is available
- validate HEIC/JPG/MOV intake from export folder
- improve source intake reports with file-format counts if needed
- add readiness/deferred classification if current failure handling is insufficient
- ensure unreadable/placeholder files fail safely and remain retryable
- provide Admin/operator guidance for iCloud export-folder workflow
- no direct iCloud API
- no Live Photo pairing yet

---

## Validation Plan for 12.27

Future test set should include:

```text
HEIC original
JPG image
MOV video
HEIC + MOV Live Photo-style pair
unsupported sidecar file, if available
zero-byte file
locked/unreadable file if practical
duplicate HEIC already ingested
same file in later repeated source session
file that changes size between scans, if practical
```

Validation should confirm:

- originals preserved unchanged
- HEIC previews generated
- MOV/video preserved as unsupported/stored media
- source intake report accurate
- repeated intake skips known source-relative paths
- failed/unreadable files are retryable
- unready/deferred files are distinguishable if implemented
- background enrichment works after intake

---

## Explicit Deferrals

The following are deferred:

```text
Direct iCloud API integration
PyiCloud/direct connector
Apple login/authentication
Live Photo pairing
Video playback
Apple album/favorites import
Apple People/Faces import
Sidecar/XMP interpretation
Edited-photo reconciliation
Cloud scheduling
Mobile app intake
Full iCloud download manager
```

---

## Definition of Done

12.26 is complete when:

- iCloud export-folder strategy is formally defined
- direct iCloud API is explicitly deferred
- source registry usage is defined
- source labeling for multiple iCloud accounts is defined
- format handling expectations are clear
- metadata limitations are documented
- provenance risks are documented
- Live Photo handling is deferred with preservation strategy
- iCloud export reliability concerns are documented
- 12.27 implementation scope is clear
- open questions and parking-lot items are identified

# 12.26 Clarification Answers (Final)

## 1. Deliverable Scope

12.26 is design-only.

Expected repository deliverables:

- final 12.26 iCloud export intake design document
- concrete 12.27 implementation checklist
- code reconnaissance notes showing current behavior and gaps

No production code changes are required for 12.26.

---

## 2. Readiness/Deferred Model (for 12.27)

Introduce deferred/unready as a separate reporting category.

Do not merge deferred/unready into failed.

Rationale:

- failed = system attempted ingest and could not complete it
- deferred/unready = system should not attempt ingest yet (still downloading, locked, placeholder-only, unstable)

Recommended report categories for 12.27:

```text
scanned
eligible
skipped_known
selected
staged
ingested
failed
deferred_unready
remaining_unknown
```

---

## 3. Readiness Defaults (for 12.27)

Initial defaults should be conservative and simple:

- size stability checks: 2
- interval: 5 seconds apart
- minimum size: > 0 bytes
- must be readable/openable
- must not match known temporary/partial artifact patterns

A file is considered ready when all readiness checks pass.

---

## 4. Source Registration Guidance

Operators should reuse one stable registered source root path per iCloud account/export stream where possible.

Rationale:

- skip-known depends on ingestion_source_id + source_relative_path
- frequent root-path churn reduces skip-known effectiveness
- stable paths improve report/history clarity

Recommended:

```text
Source Label: chuck_icloud
Source Type: cloud_export
Root Path: C:\PhotoSources\iCloud\Chuck
```

Avoid rotating temporary roots such as date-stamped download folders unless intentionally creating a new source.

---

## 5. Sidecar Handling Policy

For 12.26/12.27 planning, sidecars remain unsupported.

Policy:

- unsupported sidecar files route through existing unsupported/failure handling
- sidecars are not classified as deferred/unready

Interpretation:

- deferred = try again later
- unsupported sidecar = not ingestible under current feature set

---

## 6. Live Photo Guidance

Operator guidance should explicitly recommend preserving Live Photo companions together:

- keep HEIC and MOV files in the same folder
- keep original filenames unchanged

For now:

- HEIC ingests as image asset
- MOV ingests as preserved video/unsupported media asset
- pairing remains deferred

This preserves future pairing potential by basename/folder/timestamp relationships.

---

## Approved Defaults for 12.26/12.27 Planning

- 12.26 remains design-only with reconnaissance notes and a 12.27 checklist
- 12.27 introduces deferred_unready as separate reporting category
- readiness defaults start at 2 checks, 5 seconds apart, non-zero, readable/openable
- stable root-path reuse is documented as recommended operating practice
- sidecars remain unsupported (not deferred)
- Live Photo companions should remain co-located with original names preserved

---

# Deliverable 1: Final 12.26 iCloud Export Intake Design

## Final Architecture Decision

First iCloud intake implementation uses local iCloud export/download folders as cloud_export sources via the existing Source Intake framework.

Direct iCloud API integration remains explicitly deferred.

Cloud-export intake is a valid long-term source type and not a temporary workaround.

## Operating Model (Locked)

Two-stage model:

1. Acquisition/export stage: iCloud/export tool writes to local export folder.
2. Intake stage: Photo Organizer ingests files from registered cloud_export source.

Preferred long-term execution mode is semi-parallel with readiness gating in 12.27.

## Source Identity and Provenance Position

Keep current source identity/provenance model unchanged for 12.26:

- source identity anchored by label/type/root normalization
- known-file skip logic anchored by ingestion_source_id + source_relative_path
- SHA256 dedupe remains final safety net across source/path variations

## Format Strategy

- HEIC/HEIF: ingest and preserve originals; preview generation remains post-intake workflow
- JPG/JPEG/PNG: ingest under existing behavior
- MOV/MP4: preserve as stored media under current behavior
- Sidecars/XMP: unsupported for now
- Live Photo pairing: deferred

## Reliability Position

iCloud export reliability concerns are acknowledged and deferred to 12.27 readiness/deferred classification.

12.26 does not implement readiness logic, but defines required direction.

---

# Deliverable 2: 12.27 Implementation Checklist

## A. Intake Compatibility

- validate cloud_export source registration + intake flow end-to-end
- confirm HEIC/JPG/MOV from export folders pass scanner/filter expectations
- confirm preserved originals and expected downstream jobs (preview/duplicates/face/place)

## B. Readiness and Deferred Classification

- add readiness check phase before selection/staging for from-path source intake
- add deferred_unready classification with explicit reasons
- implement default readiness rules:
  - exists
  - size > 0
  - stable size across 2 checks, 5 seconds apart
  - readable/openable
  - extension allowed
  - not temp/partial-pattern

## C. Reporting

- extend source intake report counts to include deferred_unready
- preserve failed as attempted-and-failed only
- include reason breakdown where practical (unsupported, unreadable, locked, unstable, hash/copy failure)

## D. Operator Guidance

- publish stable root-path guidance for cloud_export sources
- publish Live Photo handling guidance (keep HEIC/MOV together with original names)
- clarify sidecar unsupported policy

## E. Validation Matrix

- HEIC original
- JPG image
- MOV video
- HEIC+MOV companion pair
- unsupported sidecar
- zero-byte file
- locked/unreadable file
- duplicate already-ingested file
- repeated intake session on same source
- unstable-growing file across checks

## F. Explicit Deferrals (Remain Deferred in 12.27)

- direct iCloud API/login/token handling
- Live Photo pairing model
- video playback/interpretation
- sidecar ingestion semantics
- Apple album/favorites/people import

---

# Deliverable 3: Code Reconnaissance Notes (Current Behavior and Gaps)

## Confirmed Current Behavior

- source type vocabulary already includes cloud_export
- approved extension defaults already include HEIC/JPG/PNG/MOV/MP4 families
- scanner currently scans readable filesystem entries recursively without readiness stabilization checks
- filter currently classifies unsupported extensions and below-min-size records as rejected
- storage manager preserves files by hash-based vault copy for unique files, independent of media type
- failure manager relocates failed inputs for operator review

## Current Gaps Relative to 12.27 Goals

- no explicit deferred_unready category in source intake reports
- no built-in readiness stabilization checks (size-stability interval, lock/openability retry window)
- no explicit temporary/partial artifact classification in reports
- no separate operator-visible distinction between try-later unready vs attempted-and-failed ingest outcomes

## Architectural Fit Assessment

Current architecture is suitable for 12.27 incremental implementation without redesign:

- source registry and source labels are in place
- admin-launched intake orchestration is in place
- provenance and dedupe safeguards are in place
- reporting pipeline already exists and can be extended with deferred_unready counts/reasons
