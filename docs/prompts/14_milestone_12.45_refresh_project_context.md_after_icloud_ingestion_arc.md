# Milestone 12.45 — Refresh PROJECT_CONTEXT.md After iCloud Ingestion Arc

## Goal

Update `PROJECT_CONTEXT.md` so it accurately reflects the current system after milestones 12.19–12.44.1.

This should be a clean documentation refresh, not a code milestone.

The updated document should become a reliable source of truth for future ChatGPT/Copilot sessions.

---

## Context

The current `PROJECT_CONTEXT.md` is useful but stale.

It still describes several items as future/unsupported that are now implemented or partially implemented, including:

```text
cloud ingestion
HEIC preview support
Live Photo handling
video metadata handling
Admin operational controls
Source Registry / Source Intake workflow
iCloud acquisition
iCloud staging cleanup
background job controls
```

Milestones and coder responses from **12.33 onward** are present in the workspace and should be used as source material.

Key milestone range to review:

```text
12.19 — Ingestion stabilization / Drop Zone control
12.20 — Background duplicate processing
12.20.x — performance/optimization work
12.25 / 12.25.1 — Source Registry and source-label controls
12.26 — iCloud export intake design
12.27 / 12.28 — iCloud export readiness / trial
12.29 — Display Preview support for TIFF/content mismatch
12.30 — Display Preview naming generalization
12.31 — Live Photo pairing design
12.32 — Live Photo pairing implementation/Admin control
12.33 — Direct iCloud / PyiCloud feasibility
12.34 — Direct iCloud connector hardening
12.35 — Direct iCloud staging adapter
12.36 — Direct iCloud adapter Source Intake trial
12.37 / 12.37.1 — direct iCloud new-asset insertion and album targeting
12.38 — icloudpd evaluation
12.39 — Live Photo pairing support for icloudpd naming
12.40 — MOV / video metadata trust handling
12.41 — icloudpd connector service design
12.42 — icloudpd backend acquisition service
12.43 — Admin UI for iCloud Acquisition
12.44 — iCloud Acquisition to Source Intake handoff
12.44.0 — iCloud source model and acquisition completeness rules
12.44.1 — Delete successfully ingested iCloud staging files
```

---

## Core Requirement

Produce a refreshed `PROJECT_CONTEXT.md` that describes what the system **is now**, not the historical path of how it got there.

Do not turn this into a milestone history document.

Do not include long debugging history.

Do not include back-and-forth decisions unless they are now active architecture rules.

---

## Primary Source Materials

Use:

```text
existing PROJECT_CONTEXT.md
milestone prompt files from 12.33 onward
coder response files from 12.33 onward
current code structure if needed
```

If there is disagreement between old context and recent milestone responses, prefer the recent completed implementation unless code inspection says otherwise.

---

## Required Updates

---

## 1. Overview

Update the overview to mention:

```text
local-first photo organizer
safe ingestion
deduplication
metadata canonicalization
faces/events/places
human-in-the-loop curation
Admin-controlled operational workflows
cloud acquisition support through icloudpd
```

Keep it concise.

---

## 2. Tech Stack

Preserve current tech stack, but update if needed.

Should include:

```text
Backend: Python 3.11, FastAPI
Frontend: Next.js / React
Database: PostgreSQL
Redis: planned / partial / background-job support depending current status
Docker: Postgres + Redis
ExifTool / pyexiftool
icloudpd as external/helper acquisition tool
DeepFace / FaceNet
OpenCV YuNet
imagehash / pHash
```

Clarify that `icloudpd` is used as a cloud acquisition adapter, not as an ingestion system.

---

## 3. Core Architecture

Update storage layout.

Current document says:

```text
storage/exports/ # reserved
```

This is no longer correct.

Update to something like:

```text
storage/
  vault/                 # immutable canonical storage
  drop_zone/             # internal ingestion staging
  exports/icloud/        # cloud acquisition staging, especially icloudpd
  quarantine/            # rejected/unknown files
  logs/                  # reports and operational logs
  review/                # face crops
  previews/              # generated display previews
  thumbnails/            # reserved/future if applicable
```

Mention that `exports/icloud/<source_label>/` is a temporary/local cloud staging area and not the Vault.

---

## 4. Data Flow / Pipeline

Replace the old single flow:

```text
Source → Drop Zone
```

with a more accurate split:

```text
Local source
→ Source Registry
→ Source Intake
→ Drop Zone
→ Vault / DB / Provenance
→ metadata / previews / faces / duplicates / places

iCloud source
→ icloudpd acquisition
→ storage/exports/icloud/<source_label>/
→ Source Intake
→ Drop Zone
→ Vault / DB / Provenance
→ post-intake jobs
→ optional verified staging cleanup
```

Important:

```text
icloudpd never writes directly to Vault or DB.
Source Intake remains the ingestion authority.
```

---

## 5. Core Concepts

Update or add concepts:

```text
Asset
Provenance
Ingestion Source
Source Registry
Source Intake
Cloud Source
iCloud Acquisition
Account Username
Vault
Drop Zone
Exports / iCloud staging folder
Display Preview
Live Photo Pair
Live Photo Motion Companion
Video Metadata Trust
Place
Duplicate Lineage
Canonical Metadata
```

Add definitions for:

### iCloud Acquisition

```text
Download-only acquisition step using icloudpd into local exports staging.
```

### Cloud Source

```text
Registered source representing one iCloud account/library staging identity.
```

### Account Username

```text
Non-secret Apple ID/account identifier associated with a source; not a password/token/session.
```

### iCloud Staging Cleanup

```text
Operator-triggered deletion of local staging files after provenance + Vault verification.
```

---

## 6. Active Systems

This section needs meaningful updates.

Add or revise sections for:

### Source Registry / Source Intake

Include:

```text
registered source identity
source_label/source_type/source_root_path
account_username for cloud/iCloud sources
explicit Source Intake run/status workflow
path normalization and project-root-relative handling
```

### iCloud Acquisition System

Include:

```text
icloudpd is preferred acquisition adapter
raw PyiCloud remains experimental/diagnostic
Admin UI supports run/status/stop
downloads to storage/exports/icloud/<source_label>/
recent_count default 25, max 500
recent window semantics; completeness not guaranteed
account_username prefill and override warning
no password/2FA/session storage in app
```

### iCloud Staging Cleanup

Include:

```text
dry-run/preview-first cleanup
operator-triggered delete
deletes only local staging files
requires provenance + Asset + Vault file proof
writes cleanup reports
does not delete iCloud/Vault/DB/provenance/source registry
```

### Display Preview System

Update to reflect:

```text
HEIC/HEIF preview support
TIFF / TIFF-bytes mismatch support if implemented
display preview generation Admin control
```

### Live Photo System

Update to reflect:

```text
pairing implemented
standard basename pairing
icloudpd _HEVC.MOV pairing
Live Photo / Live Photo Motion badges
playback deferred
motion companion hiding/filtering deferred
```

### Video Metadata System

Update to reflect:

```text
MOV/MP4/M4V video-native metadata extraction
QuickTime/container date support
capture_time_trust high/low/unknown
MOV missing image EXIF no longer automatically low trust
video playback/thumbnails deferred
```

### Admin System

Update substantially.

Mention Admin supports:

```text
Source Registry
Source Intake
iCloud Acquisition
iCloud Staging Cleanup
Display Preview Generation
Live Photo Pairing
Duplicate Processing
Face Processing
Place Geocoding
stale-run recovery for selected background jobs
```

---

## 7. API Layer

Update core domains and Admin endpoints conceptually.

Include:

```text
/api/admin/source-intake/...
/api/admin/icloud-acquisition/...
/api/admin/icloud-staging-cleanup/...
display preview / live photo / duplicate / face / geocoding admin controls as applicable
```

Do not list every endpoint unless useful.

---

## 8. Key Constraints / Architecture Rules

Add current iCloud/source rules:

```text
Source Intake is the only ingestion authority.
Cloud acquisition may only write to exports staging.
icloudpd must not write directly to Drop Zone, Vault, DB, or provenance.
Vault is immutable canonical storage.
DB/provenance explain asset origin.
Local iCloud staging cleanup is allowed only after positive provenance + Vault verification.
Photo Organizer does not store Apple ID passwords, 2FA codes, session cookies, or auth tokens.
One stable iCloud source per iCloud account/library is the production rule.
```

Also keep existing rules:

```text
non-destructive handling
deterministic processing
human-controlled identity
local-first architecture
```

---

## 9. Current Capabilities

Update to include current capabilities:

```text
local folder ingestion
cloud/iCloud acquisition through icloudpd
Source Registry and Source Intake
iCloud acquisition Admin UI
iCloud staging cleanup
exact dedupe
near-duplicate processing
metadata observations/canonicalization
HEIC/TIFF display previews
Live Photo pairing
MOV/MP4 metadata trust handling
face processing
place geocoding
duplicate processing
Photo Review/search/timeline/location/person filters
```

Be concise but current.

---

## 10. Known Limitations

Replace stale limitations.

Remove or update outdated items such as:

```text
no cloud ingestion
HEIC viewing not fully supported
Live Photo handling undefined
video handling not implemented
duplicate lineage pending decoupling
```

Suggested current limitations:

```text
iCloud acquisition uses fixed recent windows; full until-found/checkpoint completeness is not implemented.
Fixed-window acquisition may re-download cleaned staging files until checkpoint/until-found logic is added.
Multiple test iCloud sources exist; source archive/inactive support is not implemented.
Cloud-native iCloud asset IDs are not yet captured in provenance.
Photo Organizer does not manage iCloud credentials/sessions directly.
Live Photo playback is not implemented.
Live Photo motion companion filtering/hiding is not implemented.
Video playback and thumbnails are deferred.
Unified Source Profile / one-click intake workflow is not implemented.
NAS deployment is planned but not complete.
Source Registry can still contain confusing/test duplicate labels.
```

---

## 11. Near-Term Direction

Replace “Post 12.18” direction with current direction.

Suggested:

```text
12.45 documentation refresh / architecture consolidation
punchlist and usability review
source registry cleanup / inactive-source model
iCloud until-found/checkpoint strategy
unified Source Profile and Intake Workflow design
iCloud acquisition run history / unified workflow history
production-scale iCloud intake trial
NAS deployment planning
Photo Review / curation UX improvements
```

---

## 12. Storage and Deployment Direction

Update NAS section if needed.

Mention current iCloud work affects deployment:

```text
icloudpd helper environment must be considered for NAS/server deployment
iCloud auth/session handling remains external/manual for now
scheduled iCloud acquisition deferred
Vault migration to NAS remains planned
```

---

## 13. Parking Lot / Deferred Items

Do not paste the full parking lot into `PROJECT_CONTEXT.md`, but include high-level deferred themes:

```text
iCloud until-found/checkpoint strategy
cloud-native provenance
multi-account iCloud session handling
credential/session manager
source archive/inactive support
unified Source Profile workflow
Live Photo playback
Live Photo motion filtering
video thumbnails/playback
NAS scheduled acquisition
```

---

## Style Requirements

- Keep the document concise but complete.
- Prefer current state over history.
- Avoid milestone-by-milestone narration.
- Avoid implementation debugging details.
- Use clear headings.
- Keep it copy/paste friendly.
- Use markdown.
- Keep this as a context file, not a full architecture document.

---

## Validation / Closeout

After updating `PROJECT_CONTEXT.md`, provide a short coder response including:

1. Files changed
2. Major sections updated
3. Stale statements removed
4. New current-state items added
5. Any unresolved uncertainty
6. Recommendation for whether `ARCHITECTURE_ROADMAP.md`, `MILESTONE_HISTORY.md`, and `WORKFLOW.md` also need updates

---

## Definition of Done

12.45 PROJECT_CONTEXT refresh is complete when:

- cloud/iCloud acquisition is accurately described
- `storage/exports/icloud` is no longer described as reserved
- Source Registry / Source Intake model is accurately described
- iCloud staging cleanup is documented
- HEIC/TIFF preview status is current
- Live Photo pairing status is current
- MOV/MP4 video metadata status is current
- Admin capabilities are current
- stale limitations are removed or corrected
- near-term direction reflects post-12.44.1 reality
