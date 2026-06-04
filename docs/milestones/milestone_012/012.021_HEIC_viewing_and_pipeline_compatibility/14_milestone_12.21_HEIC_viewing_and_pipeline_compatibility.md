# Milestone 12.21 — HEIC Viewing + Pipeline Compatibility

## Goal

Add full HEIC ingestion and viewing compatibility while preserving original HEIC files unchanged in the Vault.

This milestone focuses on:

- HEIC ingestion compatibility
- metadata extraction compatibility
- preview/thumbnail generation for browser viewing
- cross-platform UI display consistency

This milestone does NOT implement Live Photo pairing or full video playback workflows.

---

## Context

HEIC is now a dominant real-world photo format, especially from:

- iPhone
- iCloud
- modern Apple ecosystems

The system already preserves unsupported/video assets in the Vault.

Current architecture goals:

- preserve original files unchanged
- maintain deterministic/non-destructive behavior
- support browser-based viewing across:
  - Windows
  - macOS
  - iOS
  - Android
  - future mobile/web clients

Browser HEIC support is inconsistent across platforms.

Therefore:

> viewing compatibility should be solved programmatically through generated preview derivatives, not OS/browser plugins.

---

## Core Principle

> Preserve HEIC originals unchanged. Generate compatible previews for viewing.

---

## Target Architecture

### Original Asset

Vault preserves:

```text
IMG_1234.HEIC
```

unchanged.

This remains:

- archival truth
- export/edit source
- canonical original media

---

### Derived Preview

System generates browser-compatible preview derivative such as:

```text
IMG_1234_preview.jpg
```

or:

```text
IMG_1234_preview.webp
```

Used for:

- UI display
- thumbnails
- grids
- mobile compatibility
- browser rendering

Derived previews are:

- disposable
- regeneratable
- not canonical truth

---

## Scope

### In Scope

- HEIC ingestion support
- HEIC metadata extraction validation
- HEIC thumbnail generation
- HEIC preview generation
- UI display compatibility using previews
- preserving HEIC originals unchanged
- preserving existing duplicate/metadata workflows
- ensuring HEIC assets appear normally in:
  - Photos
  - Events
  - Places
  - Timeline
  - Review views

### Out of Scope

- Live Photo pairing
- MOV/video playback
- HEIC editing
- replacing originals with JPG
- OS/plugin dependency installation
- mobile app implementation
- video transcoding pipeline
- RAW workflow redesign

---

## Important Behavior

### 1. Preserve Original HEIC

The original HEIC file must remain unchanged in Vault.

Do NOT:

- convert originals to JPG
- overwrite originals
- replace original format
- discard HEIC source

---

### 2. Generate Display Derivatives

Generate browser-compatible derivatives for viewing.

At minimum:

- thumbnail derivative
- preview/display derivative

Coder should evaluate whether existing thumbnail infrastructure can be reused safely.

---

### 3. Browser/UI Compatibility

The UI should display HEIC-backed assets consistently across:

- Windows browsers
- macOS browsers
- iPhone/mobile browsers
- Android/mobile browsers

Do not rely on:

- Windows HEIC codecs
- macOS-specific browser support
- local OS extensions/plugins

Viewing should work because the backend serves compatible preview derivatives.

---

### 4. Existing Media Behavior

Current behavior already stores unsupported/video media in Vault.

Continue current behavior for:

```text
MOV/video files
```

For now:

- preserve them
- ingest/store consistently
- do not attempt Live Photo pairing yet

---

## Live Photo Handling (Deferred)

Apple Live Photos typically include:

```text
IMG_1234.HEIC
IMG_1234.MOV
```

This milestone should NOT attempt to:

- pair HEIC + MOV
- create unified Live Photo assets
- synchronize playback
- determine canonical Live Photo representation

Future milestone:

```text
MV-007 — Live Photo Handling
```

For now:

- HEIC behaves as normal image asset
- MOV behaves as current unsupported/video asset

---

## Preview/Thumbnail Requirements

### Preview Quality

Preview derivatives should be visually high quality for normal viewing.

They do NOT need to preserve full original fidelity for:

- pixel-perfect editing
- archival export

Original HEIC remains authoritative for those workflows.

---

### Suggested Derivative Sizes

Coder may adapt existing infrastructure, but recommended concepts:

```text
thumbnail:
small grid-friendly image

preview:
larger browser-display image
```

Examples only:

```text
thumbnail: ~300px
preview: ~2048px
```

Do not over-engineer multi-tier image pyramids yet.

---

### Derivative Storage

Derived previews should be treated as:

```text
cache artifacts
```

They should be:

- regeneratable
- non-authoritative
- separable from Vault originals

Coder should reuse existing review/export/thumbnail infrastructure where practical.

---

## Metadata Requirements

HEIC assets must continue supporting:

- EXIF extraction
- metadata normalization
- metadata observations
- canonicalization
- GPS extraction
- capture time extraction
- camera/device metadata

HEIC should participate normally in:

- duplicate processing
- timeline grouping
- events
- places
- search

---

## Duplicate Handling

HEIC assets should participate normally in:

- SHA256 exact duplicate detection
- pHash generation if supported
- near-duplicate grouping

Important:

HEIC vs JPG versions of same photo may have different metadata richness.

Existing canonicalization logic should continue determining preferred metadata deterministically.

Do not special-case HEIC canonical preference unless current rules already imply it.

---

## Backend Requirements

### Required

- validate HEIC ingestion compatibility
- generate display-compatible derivatives
- serve HEIC-backed assets through previews
- preserve original HEIC files unchanged
- preserve existing metadata pipeline behavior
- preserve existing duplicate pipeline behavior

### Preferred

- reuse existing thumbnail infrastructure
- avoid duplicate derivative generation
- add derivative existence tracking if low-risk

---

## Frontend Requirements

### Required

HEIC-backed assets must display normally in:

- Photos view
- Events
- Timeline
- Places
- Review/detail views

Frontend should consume compatible preview URLs rather than relying on browser-native HEIC rendering.

---

### Out of Scope

Do not redesign image viewer UX.

No:

- advanced zoom viewer
- Live Photo playback
- mobile app work
- streaming pipeline

---

## Safety Requirements

### 1. Original Preservation

Original HEIC files must remain:

- unchanged
- exportable
- authoritative

No destructive conversion.

---

### 2. Derivative Separation

Preview/thumbnail derivatives must not become canonical truth.

Canonical truth remains:

- Vault original
- DB metadata

Derived previews are cache/display artifacts only.

---

### 3. Existing JPG/PNG Behavior

Do not regress existing image display behavior.

HEIC support should integrate cleanly alongside:

- JPG
- JPEG
- PNG
- WEBP
- existing formats

---

## Validation Checklist

### Ingestion

- HEIC files ingest successfully
- HEIC metadata extracts correctly
- HEIC assets appear in DB normally
- HEIC assets appear in Photos/Event/Timeline views

### Viewing

- thumbnails render
- preview images render
- browser displays work on Windows browser
- browser displays work on mobile browser if testable

### Metadata

- GPS extraction works
- captured_at extraction works
- canonicalization works
- duplicate processing works

### Preservation

- original HEIC remains unchanged in Vault
- previews are separate derivative files
- no JPG replacement of original

### Existing Formats

- JPG/PNG workflows still work
- existing thumbnails/previews still work

---

## Step 2.5 — Codebase Reconnaissance Required

Before coding, confirm:

1. Current HEIC ingestion behavior
2. Existing thumbnail/preview generation entry points
3. Existing derivative storage model
4. Whether pHash generation supports HEIC currently
5. Whether browser rendering currently fails because of MIME/browser support
6. Best library/tool for HEIC preview generation
7. Whether existing FFmpeg/Pillow/ImageMagick tooling can safely support HEIC
8. Whether any dependency installation is required
9. Whether HEIC previews can reuse current image serving APIs
10. Whether any schema changes are needed

Pause and ask before introducing large new dependencies or OS-specific assumptions.

---

## Coder Clarification Expectations

Before coding, coder should answer:

1. What currently happens when HEIC is ingested?
2. Which stage currently fails:
   - metadata
   - thumbnail generation
   - browser rendering
3. What preview-generation approach is safest?
4. What dependency/tooling is required?
5. Can existing image-serving infrastructure be reused?
6. Does pHash currently work for HEIC?
7. How should missing preview generation failures be surfaced?

---

## Deliverables

- HEIC ingestion compatibility
- HEIC preview generation
- HEIC thumbnail generation
- browser-compatible HEIC viewing
- validation summary
- dependency/setup notes if needed

---

## Definition of Done

Milestone 12.21 is complete when:

- HEIC files ingest successfully
- metadata extraction works
- duplicate processing works
- previews/thumbnails are generated
- HEIC-backed assets display normally in browser UI
- original HEIC files remain unchanged in Vault
- system behavior remains non-destructive and deterministic

---

## Notes

This milestone intentionally avoids:

- Live Photo pairing
- video workflows
- mobile app implementation
- editing/export redesign

Future milestones may add:

- Live Photo support
- video playback
- derivative regeneration jobs
- advanced image viewer
- mobile-native workflows
  ```
# 12.21 HEIC Clarification Answers
## 1. Preview generation — library/output choiceApproved.Use Pillow + pillow-heif in a new preview service.Generate JPEG derivatives for 12.21.Preferred approach:- preserve original HEIC unchanged in Vault- generate browser-compatible JPEG preview- store preview under `storage/previews`- serve through endpoint similar to:```text/media/previews/{sha256}.jpg
JPEG is acceptable for 12.21 because it is universally browser-compatible and simple.
WebP can be considered later if storage/performance warrants it.

2. Preview generation — when it runs
Use background generation as the primary model.
Preferred:
(b) Background job
Add Admin/script-triggered preview generation for HEIC assets missing previews.
Reason:


consistent with background enrichment architecture


avoids adding latency to ingestion


keeps ingestion fast


allows regeneration later if needed


If preview generation is very fast, coder may optionally support on-demand fallback later, but do not make ingestion wait on preview generation.
For 12.21:


ingestion should not block on HEIC preview generation


HEIC assets without previews may show placeholder until preview job runs


Admin should provide a way to generate missing HEIC previews if low-risk



3. DB field for preview path
Yes, add a nullable preview path field to Asset if low-risk.
Suggested field:
preview_path
or more explicit:
display_preview_path
Use whichever naming fits existing model conventions.
Reason:


avoids repeated filesystem scans


makes preview availability queryable


supports Admin pending counts


fits long-term derivative tracking


Important:


this field points to a derivative/cache artifact


it is not canonical truth


original Vault path remains authoritative



4. Face detection on HEIC
Include this in 12.21.
HEIC viewing should behave like other image files, including:


face detection


face boxes


face thumbnails/crops


So yes, update face image loading so HEIC can be read.
Approved approach:


add _load_image(path) helper in face_detector.py


first try OpenCV as today


if OpenCV returns None, fall back to Pillow + pillow-heif


convert to NumPy array for detector


Also apply equivalent HEIC loading fix for crop generation in face processing.
Important:


preserve existing JPG/PNG behavior


do not rewrite face detection logic


only fix image loading compatibility



5. Content tagger HEIC fix
Yes, include the one-line pillow_heif.register_heif_opener() fix in 12.21.
This is low-risk and consistent with HEIC pipeline compatibility.

6. Background process behavior
Background processes should run independently of normal user workflows.
While preview generation, face processing, duplicate processing, or geocoding are running, the user should still be able to:


browse photos


view already-available previews


adjust face clusters already processed


label places


review duplicates


use Admin


The only caveat:


assets not yet processed by a specific background job may not yet have that enrichment available


Examples:


HEIC preview not generated yet → placeholder/fallback


face processing not complete → no face boxes/thumbnails yet


geocoding not complete → coordinate/fallback place label


duplicate processing not complete → duplicate status may be pending


Do not block normal UI use while background jobs run.
