# 📘 CANONICAL_PARKING_LOT v3 — Photo Organizer

## Purpose

Track **deferred, future, and refinement work** while maintaining:

- focus on active milestones
- architectural clarity
- system evolution visibility

This document is:

- decision-oriented
- de-duplicated
- structured by system

---

# 🔥 1. ACTIVE CANDIDATES (Next Milestones)

These are **approved for near-term execution**

---

## IN-011 — Batch Staging (Ingestion Stabilization)

### Problem

- Drop Zone overloaded with large imports
- unclear active vs pending state

### Desired

- stage only working batch
- process → clear → next batch

### Importance

- critical for real-world ingestion
- prerequisite for cloud ingestion

---

## IN-009 — Background Near-Duplicate Processing

### Problem

- duplicate lineage consumes ~90% of ingest time
- blocks pipeline performance

### Desired

- ingestion completes without lineage
- lineage runs asynchronously
- admin control over execution

### Importance

- major architectural bottleneck
- required for scaling

---

## IN-013 — Cloud Ingestion (iCloud Priority)

### Problem

- no direct ingestion from cloud
- real-world data primarily resides in iCloud

### Desired

- ingest from iCloud with:
  - batch limits
  - total limits
- integrate with batch staging

### Notes

- iCloud = first priority
- OneDrive later (post NAS migration)
- Google Drive last

### Importance

- required for real-world validation

---

## IN-014 — Source Ingestion Session Control (Large Folder Staging)

### Problem

- large source folders (10K–20K+ files) cannot be safely ingested in a single run  
- repeated ingestion sessions may:  
  - re-select the same files  
  - lack visibility into progress  
- no clear mechanism to determine when a source has been fully ingested  

### Desired

- deterministic staging from source folders across multiple sessions  
- ability to:  
  - stage only “new” (not yet ingested) files  
  - avoid reprocessing already ingested files  
- clear progress visibility:  
  - total eligible files  
  - already ingested  
  - remaining  

### Design Considerations

- stateless scan vs source manifest tracking  
- use of:  
  - provenance (source + relative path)  
  - file metadata (size, modified time)  
  - hashing (cost vs accuracy)  
- handling of:  
  - renamed/moved files  
  - partially available cloud files (iCloud placeholders)  
  - failed or deferred files  
- interaction with:  
  - INGEST_TOTAL_LIMIT  
  - Drop Zone batch staging (12.19)  

### Constraints

- must remain deterministic and repeatable  
- must not introduce silent assumptions about file identity  
- must integrate cleanly with provenance system  

### Status

⚠️ **Design-first milestone required before implementation**  

### Importance

- critical for cloud ingestion (iCloud)  
- required for large real-world datasets  
- prevents ingestion loops and operator confusion

---

## MV-006 — HEIC Native Support (Viewing + Processing)

### Problem

- HEIC images not reliably viewable
- conversion to JPG is undesirable

### Desired

- native HEIC viewing
- no forced conversion
- preserve original format in Vault

### Constraints

- must not duplicate storage
- must preserve canonical integrity

---

## PX-016 — Undated Asset Discovery

### Problem

- no way to locate assets missing `captured_at`

### Desired

- explicit “Undated” filter
- timeline bucket

### Importance

- small, high-impact UX improvement

---

PX-017 — Location Intelligence System (Master Track)

Includes:

- geographic hierarchy
- user-defined places (12.17 started)
- landmark recognition
- image-based inference
- learned place recognition

⚠️ multi-phase system

---

## PX-018 — Manual Date Trust Override / Physical Media Detection

### Problem

Some assets have valid digital EXIF timestamps but are actually photos of physical media, such as:

- slides
- printed photos
- documents
- albums
- negatives

The system currently classifies these as high trust because the camera timestamp is valid, but the timestamp reflects digitization date, not the original capture date.

### Desired

Allow the user to manually override capture-time trust from Photo Review.

Examples:

- High → Low
- High → Unknown
- Low → High, if user confirms correctness

### Design Considerations

- use existing `capture_time_trust_override`
- preserve original EXIF metadata
- do not rewrite source files
- show both original system trust and user override
- optionally allow notes/reason later

### Future Intelligence Option

Later AI/ML or visual heuristics may suggest likely physical-media photos, but should not automatically change trust.

Possible signals:

- visible slide borders
- photos of printed photographs
- scanner bed/background
- document-like framing
- camera model/date mismatch with image content

### Status

Deferred — manual workflow first, AI-assisted detection later.

### Importance

Improves date quality and timeline trust without changing original metadata.
---

---

## PX-ICLOUD-001 — iCloud Credential / Session Manager

### Summary

Design a longer-term credential/session strategy for iCloud acquisition.

### Current State

Photo Organizer currently does **not** store:

```
Apple ID password2FA codeiCloud session cookiesiCloud auth tokens
```

Authentication is handled externally by `icloudpd`.

Photo Organizer launches `icloudpd` and relies on `icloudpd` having a valid session.

### Why Deferred

Credential/session handling is security-sensitive and should not be rushed into the ingestion workflow.

### Future Questions

- Should Photo Organizer ever manage iCloud sessions directly?
- Can `icloudpd` session status be checked safely?
- Where are session files stored?
- Can sessions be separated per Apple ID?
- How should this work on NAS?
- Should there be an Admin “authentication status” indicator?
- Should there be a documented manual re-auth workflow?
- Is password/2FA entry in UI ever acceptable, or should it remain external?

### Suggested Future Milestone

```
iCloud Credential / Session Handling Design
```

---

## PX-ICLOUD-002 — Multi-iCloud Account Support

### Summary

Define how multiple iCloud accounts should be represented and operated.

### Current Assumption

Normal production use should be:

```
1 iCloud account/library = 1 stable iCloud source
```

Example:

```
Source Label: chuck_icloudpdApple ID: chhendersoniv@gmail.comRoot Path: storage/exports/icloud/chuck_icloudpd/
```

### Why Deferred

12.44.0 should define the single-source production model first. Multi-account behavior can be layered later.

### Future Questions

- Can `icloudpd` support multiple accounts/sessions on the same machine cleanly?
- Does each Apple ID need separate session storage?
- Should each iCloud source store an associated username?
- How does Admin prevent running the wrong Apple ID against the wrong source?
- What happens if two sources accidentally use the same Apple ID?
- How should staging folders be named for family/shared accounts?

### Suggested Future Milestone

```
Multi-Account iCloud Acquisition Support
```

---

## PX-ICLOUD-003 — Cloud-Native iCloud Provenance

### Summary

Extend provenance to include iCloud-specific remote identity.

### Current State

Current provenance is based on local Source Intake concepts:

```
ingestion_source_idsource_relative_pathasset SHAingestion run
```

For iCloud acquisition, `source_relative_path` points to the local staged file downloaded by `icloudpd`.

### Future Desired State

Capture additional cloud-native provenance where available:

```
remote iCloud asset IDApple ID / account identityicloudpd run IDdownload timestampdownload methodoriginal iCloud filenamepossibly Live Photo resource relationship
```

### Why Deferred

The current Source Intake provenance is sufficient for local ingestion and cleanup. Cloud-native provenance is valuable but not required before 12.44.1.

### Future Questions

- Does `icloudpd` expose stable cloud asset IDs in a usable report/log?
- Can those IDs be mapped to downloaded filenames?
- Should remote IDs live on Provenance or a separate cloud provenance table?
- How should Live Photo still/MOV resources share cloud identity?
- How should edited/original versions be represented?

### Suggested Future Milestone

```
Cloud-Native iCloud Provenance Model
```

---

## PX-ICLOUD-004 — Automatic Recent Acquisition / Until-Found Strategy

### Summary

Improve acquisition completeness beyond fixed `recent_count`.

### Current Issue

Current acquisition asks for a fixed recent window:

```
recent_count = 25
```

If those 25 files are already staged/acquired, there may still be unacquired items beyond that window.

### Future Desired State

Support acquisition logic such as:

```
download/check recent items until N consecutive already-known items are found
```

or:

```
maintain checkpoint by cloud asset ID / added date
```

### Why Deferred

12.44.0 should define the conceptual rule, but full checkpoint/until-found implementation can be a future hardening milestone.

### Future Questions

- Can `icloudpd --until-found` solve this directly?
- Does `icloudpd` maintain its own local state robustly enough?
- Should Photo Organizer maintain a cloud acquisition checkpoint?
- Should completeness be based on staged file presence, provenance, Vault presence, or cloud asset ID?
- What should Admin report: “caught up,” “partial window,” or “unknown completeness”?

### Suggested Future Milestone

```
iCloud Acquisition Until-Found / Checkpoint Strategy
```

---

## PX-ICLOUD-005 — Admin iCloud Authentication Status

### Summary

Show whether `icloudpd` is authenticated and ready before running acquisition.

### Current State

Admin can launch iCloud Acquisition. If authentication is missing or expired, backend returns an error such as:

```
AUTH_REQUIREDSESSION_EXPIRED
```

### Future Desired State

Admin displays:

```
iCloud session readyauthentication requiredsession expiredlast successful auth/run
```

### Why Deferred

Requires understanding `icloudpd` session behavior and possibly a safe status probe. Not required for basic workflow.

### Future Questions

- Is there a safe `icloudpd` command to validate auth without downloading?
- Can session status be checked per username/account?
- Should Admin display manual re-auth instructions?
- Can auth status be refreshed without exposing secrets?

### Suggested Future Milestone

```
iCloud Authentication Status UI
```

---

## PX-ICLOUD-006 — Source Registry Archive / Inactive Sources

### Summary

Provide a safe way to retire old test sources without deleting provenance history.

### Current Issue

Development/testing created multiple iCloud source labels and staging folders.

Hard-deleting source registry rows could damage provenance explainability if rows are referenced.

### Future Desired State

Allow source records to be marked:

```
activeinactivearchivedtest/deprecated
```

instead of deleted.

### Why Deferred

This is broader than iCloud cleanup. It affects source registry semantics across all source types.

### Future Questions

- Should sources have `is_active`?
- Should archived sources remain visible in provenance views?
- Should inactive sources be hidden from acquisition/intake dropdowns?
- How should old test sources be labeled?
- Should source deletion ever be allowed if provenance exists?

### Suggested Future Milestone

```
Source Registry Archive / Inactive Source Support
```

---

## PX-ICLOUD-007 — Test iCloud Source Cleanup

### Summary

Clean up historical test source folders and source registry clutter created during milestones 12.33–12.43.

### Current Issue

Several folders exist under:

```
storage/exports/icloud/
```

Many were created for feasibility/testing.

### Why Deferred

Do not manually delete/alter registry records until we define source archive/inactive behavior and cleanup safety rules.

### Future Tasks

- Identify test-only iCloud source labels
- Identify which folders contain only already-ingested files
- Decide whether to delete local test staging files
- Mark test sources inactive/archived if source model supports it
- Preserve provenance explainability

### Suggested Future Milestone

```
iCloud Test Source Cleanup
```

---

## PX-ICLOUD-008 — iCloud Acquisition Run History / Reports UI

### Summary

Improve Admin visibility into historical iCloud acquisition runs.

### Current State

The UI shows current/latest status and report path.

### Future Desired State

Add a run history table:

```
run idsource labelusernamerecent countstatusstarted/completedstaged file countskipped existingfailed countreport link
```

### Why Deferred

Useful, but not required before 12.44.0 / 12.44.1.

### Future Questions

- How many runs should be shown?
- Should reports be expandable in UI?
- Should run history include Source Intake linkage?
- Should acquisition and intake be displayed as a combined workflow history?

### Suggested Future Milestone

```
iCloud Acquisition Run History UI
```

---

## PX-ICLOUD-009 — Acquisition + Intake Combined Workflow History

### Summary

Create a unified view showing acquisition runs and their related Source Intake runs.

### Current State

Acquisition and Source Intake are separate systems.

### Future Desired State

Admin can see:

```
iCloud acquisition run→ staged files→ Source Intake run→ new/skipped/failed/deferred→ post-intake jobs
```

### Why Deferred

This requires linking acquisition runs to intake runs and possibly adding workflow-level state.

### Future Questions

- Should Source Intake run record acquisition_run_id?
- Should Admin show a timeline of acquisition → intake → enrichment?
- Should this become a generalized workflow dashboard?

### Suggested Future Milestone

```
Unified Ingestion Workflow History
```

---

## PX-ICLOUD-010 — Automatic Post-Intake Enrichment Chain

### Summary

Optionally run enrichment jobs after Source Intake.

### Current Workflow

Operator manually runs jobs such as:

```
Display Preview GenerationLive Photo PairingDuplicate ProcessingFace ProcessingPlace Geocoding
```

### Future Desired State

After Source Intake, Admin may offer:

```
Run recommended post-intake jobs
```

or eventually an automated chain.

### Why Deferred

Automation can obscure failures and make debugging harder. Manual controls are safer until production intake is stable.

### Future Questions

- Which jobs should run after every iCloud intake?
- Should jobs run only for newly inserted assets?
- How should failures be reported?
- Should this be opt-in per source?
- Should large runs defer heavy jobs?

### Suggested Future Milestone

```
Post-Intake Enrichment Workflow
```

---

## PX-ICLOUD-011 — iCloudPD Configuration / Advanced Options

### Summary

Expose safe advanced `icloudpd` options.

### Current State

Backend uses a strict command allowlist.

### Future Options to Evaluate

```
--until-found--album--folder-structure--skip-videos / include videosLive Photo related flagssize/original options
```

### Why Deferred

The first supported workflow should remain conservative.

### Future Questions

- Which flags are safe?
- Which flags could mutate or delete cloud data?
- Which flags affect folder layout/provenance?
- Should advanced flags be per-source defaults?
- Should Admin expose them or keep them config-only?

### Suggested Future Milestone

```
iCloudPD Advanced Option Support
```

---

## PX-ICLOUD-012 — NAS / Scheduled iCloud Acquisition

### Summary

Run iCloud acquisition automatically on NAS or always-on server.

### Current State

Acquisition is operator-launched from Admin.

### Future Desired State

Scheduled iCloud acquisition such as:

```
daily recent acquisitionweekly larger scannotify if auth expired
```

### Why Deferred

Requires stable credential/session handling, NAS deployment design, and failure notifications.

### Future Questions

- Should acquisition be scheduled by app, cron, or NAS task scheduler?
- How are sessions kept valid?
- What happens on auth expiration?
- Should source intake also be scheduled?
- How are large downloads throttled?

### Suggested Future Milestone

```
Scheduled iCloud Acquisition / NAS Operation
```

---

## PX-ICLOUD-013 — iCloud Album / Favorites / People Metadata Import

### Summary

Import iCloud organizational metadata beyond files.

### Possible Metadata

```
album membershipfavoritespeople labelsshared library infoedited/original variants
```

### Why Deferred

Current goal is reliable file acquisition and local organization. Cloud organizational metadata can come later.

### Future Questions

- Does `icloudpd` expose album/favorite metadata?
- Does raw PyiCloud expose it better?
- How would album membership map to local events/albums/tags?
- Should cloud albums become local collections?
- How should changes over time be handled?

### Suggested Future Milestone

```
iCloud Album / Favorites Metadata Import
```

---

## PX-ICLOUD-014 — Live Photo Playback

### Summary

Add Apple-like or simplified playback for paired Live Photos.

### Current State

The system can:

```
preserve still and MOVpair Live Photo componentsshow Live Photo and Live Photo Motion badges
```

Playback is not implemented.

### Why Deferred

Pairing and preservation are more important than playback. Playback is a UI/media feature and can come later.

### Future Options

```
simple play buttonhover playbackpress-and-hold behaviormute/unmuteopen MOV companionApple-like Live Photo preview
```

### Suggested Future Milestone

```
Live Photo Playback UI
```

---

## PX-ICLOUD-015 — Hide / Filter Live Photo Motion Companions

### Summary

Allow UI to hide or filter Live Photo motion companion MOV files.

### Current State

MOV companions are visible as assets and tagged:

```
Live Photo Motion
```

### Future Desired State

Photo browsing may optionally hide motion companions unless explicitly requested.

### Why Deferred

Need user workflow experience first. Hiding should not obscure archival truth.

### Future Questions

- Should companion MOVs be hidden by default?
- Should there be a filter: “Show Live Photo Motion files”?
- How does this interact with video browsing?
- How does this affect search/counts?
- How should detail pages link still ↔ motion?

### Suggested Future Milestone

```
Live Photo Motion Companion Filtering
```

---

## PX-ICLOUD-016 — Video Canonicalization Recompute Parity

### Summary

Bring video support into any remaining canonical metadata recompute paths that are still image-only.

### Current State

12.40 added video metadata extraction and trust handling.

Coder noted one deferred gap:

```
recompute_canonical_metadata_for_assets() video support
```

### Why Deferred

12.40 fixed the immediate MOV/MP4 trust problem. Full recompute parity can be handled later.

### Future Questions

- Which recompute paths remain image-only?
- Should video canonicalization be fully equivalent to image canonicalization?
- Are there video-specific canonical fields needed?
- How should bulk recompute/reporting work?

### Suggested Future Milestone

```
Video Canonicalization Recompute Parity
```

---

```
## PX-ICLOUD-017 — Unified Source Profile and Intake Workflow### SummaryThe current ingestion workflow is architecturally safe but too clumsy for end-state production use.Today, cloud ingestion requires multiple visible operator steps:```text1. Create/register source2. Run iCloud Acquisition3. Prepare Source Intake4. Run Source Intake5. Later clean up staged files
```

This separation was appropriate during development and testing, but the long-term Admin workflow should be simpler and more source/profile-centered.

---

### Current State

Current iCloud flow:

```
icloudpd acquisition→ storage/exports/icloud/<source_label>/→ Source Intake→ Drop Zone→ Vault / DB / Provenance
```

Current Admin concepts are separate:

```
Source RegistryiCloud AcquisitionSource IntakeStaging Cleanup, planned separately
```

This creates several usability issues:

```
operator must understand implementation stagesoperator must choose the same source repeatedlycloud workflow differs from local workflowsource label/path mistakes are possiblestaging folder details are too visiblecleanup feels separate from intake
```

---

### Desired Future Direction

Create a unified **Source Profile** model.

A source profile should represent both:

```
where files come fromhow files should be acquired or scanned
```

The operator should select a source/profile and run intake, while the system determines which technical steps are needed.

---

### Proposed Concepts

#### Source Type

Examples:

```
local_folderexternal_drivecloudscan_batchother
```

#### Cloud Type

For cloud sources only:

```
icloudonedrivegoogle_photosdropboxother
```

#### Source Profile

For iCloud:

```
Source Label: chuck_icloudSource Type: cloudCloud Type: icloudAccount Username: chhendersoniv@gmail.comAcquisition Method: icloudpdRoot/Staging Path: storage/exports/icloud/chuck_icloud/
```

For a local folder:

```
Source Label: chuck_pcSource Type: local_folderRoot Path: D:\Photos\
```

---

### Desired End-State Workflow

Operator selects:

```
Chuck iCloud
```

Then clicks:

```
Run Intake
```

System performs the appropriate workflow.

#### For iCloud

```
1. Run cloud acquisition via icloudpd.2. Download into staging folder.3. Run Source Intake against staging folder.4. Report acquisition + intake results together.5. Offer or perform verified cleanup of successfully ingested staging files.
```

#### For Local Folder

```
1. Scan local folder.2. Run Source Intake.3. Report results.
```

The user should not need to think in terms of separate acquisition/intake mechanics unless troubleshooting.

---

### Benefits

```
one unified intake workflowfewer operator stepsless confusion between acquisition and ingestionfewer source label/path mistakeseasier multi-provider cloud support laterclearer source identity and provenancecleaner Admin UIbetter foundation for scheduled intake later
```

---

### Important Design Rules

- Cloud acquisition must still not write directly to Vault or DB.
- Source Intake remains the authority for ingestion.
- Staging folders should become implementation details where possible.
- Passwords, 2FA codes, and session cookies must not be stored in Source Profiles.
- Account username may be stored as non-secret source metadata.
- Cleanup of staging files must remain provenance-verified.
- Local and cloud workflows should share a common operator-facing “Run Intake” concept.

---

### Relationship to Current Milestones

This should not block:

```
12.44.1 — Delete Successfully Ingested iCloud Staging Files12.45 — Documentation Refresh / Architecture Housekeeping
```

The current milestone path should finish the safe, explicit workflow first.

This item should be revisited during the post-12.45 punchlist/usability review.

---

### Suggested Future Milestone

```
Unified Source Profile and Intake Workflow Design
```

---

### Possible Follow-On Implementation Milestones

```
Source Profile schema refinementCloud provider type supportUnified Run Intake Admin UICloud acquisition + intake orchestrationUnified acquisition/intake run historyProvider-specific source settingsSource-level cleanup policyScheduled source profile intake
```

---

### Priority

Medium-high after 12.45.

This is not needed to complete the current iCloud ingestion arc, but it is important before the system becomes a production daily-use tool.

---



## AQ-005 — Hamming Distance Threshold Tuning

### Problem

- current threshold misses real duplicates

### Desired

- adjustable thresholds
- better filtering (resolution, time, format)

---

## UX — Duplicate Group Review Improvements

### Includes

- larger preview
- presentation mode

### Importance

- improves usability immediately

---

# 🧱 2. CORE SYSTEM REFINEMENTS

Important, but **after stabilization**

---

## MV-007 — Live Photo Handling (HEIC + MOV)

### Problem

- Live Photos = HEIC + MOV
- unclear canonical representation

### Desired

- treat as linked asset pair
- define canonical still
- support motion playback

### Status

⚠️ **Design required before implementation**

---

## IN-010 — Drop Zone Rejected Routing

- move failed files to:
  - quarantine / review
- preserve reason + provenance

---

## IN-012 — Provenance vs Ingestion Run Separation

### Concept

- provenance = durable truth
- ingestion run = history

⚠️ Requires careful migration

---

## PL-003 — Location Filtering

- filter by:
  - country / state / city / user_label

---

## PL-006 — Place Normalization

- resolve inconsistent naming

---

## PL-008 — Missing Location Handling

- define behavior for missing GPS

---

## EV-013 — Event Date Range Consistency

- unify recalculation across:
  - merge
  - assign
  - remove

---

# 🧩 3. WORKFLOW & UX EVOLUTION

---

## PX-014 — Photo-Centric Unified Correction Workspace

Single photo → fix:

- faces
- events
- metadata
- duplicates
- location

⚠️ Do after system stabilization

---

## UX-015 — Multi-Surface UI Architecture

Separate UI into:

1. Viewer
2. Workbench (current)
3. Admin

---

## PX-002 — Auto-Advance Workflow

- after action → next item

---

## PX-003 — Smart Filtering Expansion

---

## PX-013 — Person-Based Navigation

---

# 👤 4. FACE / IDENTITY SYSTEM

---

## ID-001 — Create Cluster from Face

## ID-002 — Friendlier Cluster Selection

## ID-003 — Representative Faces

## ID-004 — Cluster Confidence Signals

---

## FW-001 — Bulk Face Actions

## FW-002 — Suggested Cluster

## FW-003 — Face Comparison Tool

## FW-004 — Suggestion Dismissal System

---

# 📍 5. LOCATION SYSTEM (EXPANSION TRACK)

---

## 

## PL-007 — Provenance vs Location Reconciliation

---

# 📦 6. COLLECTIONS / ALBUMS

---

## CO-006 — Event ↔ Album Integration

- create album from event
- add event to album
- preserve independence

⚠️ defer until events stabilize

---

## CO-001 / CO-002 / CO-003 — Collections System

---

# ⚙️ 7. INGESTION & PIPELINE (ADVANCED / FUTURE)

---

## IN-008 — Drop Zone Reprocessing Behavior

---

# 🎥 8. MEDIA / VIDEO SYSTEM

---

## MV-005 — Video Strategy (Full System)

- ingestion
- metadata
- playback
- duplicates

⚠️ separate system track

---

# 🧠 9. DUPLICATE SYSTEM (ADVANCED)

---

## AQ-006 — Cross-Format Detection Gap

---

## AQ-008 — Cross-Format Auto Grouping

---

## AQ-010 — Multi-Signal Duplicate Scoring

⚠️ do after real-world observation

---

## AQ-011 — Canonical Asset Locking (manual canonical preference preservation)

### Problem

Current duplicate processing allows canonical asset selection to change as new duplicate relationships are discovered.

This may conflict with intentional user choices, including:

- manually selected canonical assets
- edited/display-adjusted assets
- exported/shared assets
- user expectations of canonical stability

### Desired

Support optional canonical “lock” behavior where:

- user-selected canonical assets are preserved
- automated duplicate recomputation cannot silently replace locked canonical assets
- manual override remains possible

### Design Considerations

- system-selected vs user-selected canonical distinction
- lock granularity:
  - asset-level
  - duplicate-group-level
- interaction with:
  - new higher-quality duplicates
  - manual merges/splits
  - demotion/restoration
- whether lock should be:
  - hard lock
  - preference/weighting
  - reversible

### Constraints

- must remain non-destructive
- must preserve deterministic duplicate behavior
- should avoid over-constraining future canonical improvements

### Status

⚠️ Observe real-world workflows before implementation

### Importance

- user trust
- canonical stability
- long-term duplicate adjudication integrity

---

# 🤖 10. INTELLIGENCE / AI (LONG-TERM)

---

## AI-001 → AI-005

---

## EXIF Inference (OCR / inferred data)

⚠️ non-deterministic → defer

---

# 🧾 11. PROVENANCE SYSTEM UX

---

## PR-001 → PR-008

## PR-009 — Cloud Provenance Identity Model

### Problem

Export-folder intake uses source-relative paths for known-file tracking, but cloud providers may expose stronger identities such as remote asset IDs. Export paths may change across downloads, and the same cloud photo may appear as original, edited derivative, sidecar, or Live Photo companion.

### Desired

Design a cloud-aware provenance model that can track:

- provider
- cloud account/source
- remote asset ID
- remote version ID if available
- original filename
- exported/staged path
- asset role: original, edited, sidecar, video companion
- relationship to local Vault asset

### Importance

Required before robust direct iCloud/API intake and long-term cloud synchronization.

---

# 🧩 12. DEMOTION SYSTEM (NON-DUPLICATE)

---

## DS-001 — Non-Duplicate Demotion

### Examples

- screenshots
- documents
- errors

### Requirements

- single + batch
- reversible
- hidden from normal views

---

## DS-002 — Demoted Asset Management

- view demoted
- restore

---

# ❌ 13. COMPLETED

All completed items have been removed from active sections.
