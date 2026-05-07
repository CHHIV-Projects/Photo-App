# Milestone 12.29 — Display Preview Robustness for TIFF and Mislabeled Images

## Goal

Improve browser display robustness for non-browser-friendly image files and mislabeled image files by generating browser-safe display previews while preserving originals unchanged.

This milestone addresses two related issues found during real iCloud/export testing:

1. TIFF/TIF files ingest successfully but may not display in browser UI.
2. Some files may have misleading extensions, such as `.jpg` path/metadata but TIFF-encoded bytes.

---

## Context

Milestone 12.21 added HEIC preview generation and browser display support.

Milestone 12.28 real export testing found:

```text
TIF files ingested and provenance succeeded,
but display_preview_path remained null.
```

It also uncovered a confirmed edge case:

```text
Asset path/extension says .jpg
file bytes decode as TIFF
browser render fails when served as JPEG
```

This is likely to occur in inherited/family archives, scans, edited exports, or manually renamed files.

The system should remain non-destructive:

```text
Vault original = preserved truth
Display preview = browser-safe derivative
```

---

## Core Principle

> Do not trust file extension alone for display compatibility.

---

## Scope

### In Scope

- Add TIFF/TIF preview generation
- Detect extension/content mismatch where practical
- Generate browser-safe preview derivatives for TIFF and mismatched image files
- Reuse/extend existing preview infrastructure from HEIC support
- Preserve original files unchanged in Vault
- Ensure Photos/Search/Review views use preview URL when available
- Add report/logging for preview failures or content mismatch if practical
- Validate known 12.28 edge case

### Out of Scope

- RAW file support
- PSD/AI/complex document support
- PDF preview support
- video playback
- Live Photo pairing
- image editing
- rewriting original file extensions
- renaming Vault files
- changing asset identity
- modifying source files
- broad MIME database redesign unless needed

---

## Required Behavior

### 1. TIFF/TIF Preview Support

For assets with extensions:

```text
.tif
.tiff
```

Generate a browser-compatible display preview.

Preferred preview format:

```text
JPEG
```

or existing project preview format if already standardized.

Behavior:

```text
original TIFF remains unchanged in Vault
preview derivative is generated separately
asset display uses preview URL
```

---

### 2. Mislabeled Image Detection

Add content-format detection where practical.

Example problem:

```text
filename/path: example.jpg
actual bytes: TIFF
browser attempts JPEG rendering
display fails
```

The system should detect that the actual content is not consistent with the expected browser-renderable format and generate a preview derivative.

Do not rename the original.

Do not rewrite the Vault file.

Do not change SHA256 identity.

---

### 3. Preview Generation Eligibility

Preview generation should consider:

```text
HEIC / HEIF
TIFF / TIF
known image files that fail direct browser rendering
extension/content mismatches if detectable
```

This does not require a full redesign of HEIC preview job, but if low-risk, consider generalizing:

```text
HEIC Preview Generation
```

toward:

```text
Display Preview Generation
```

If renaming/generalization is too broad, keep existing HEIC job and add TIFF/mismatch support with minimal changes.

---

### 4. Preview Storage

Continue treating previews as derived cache artifacts.

Required:

- preview stored separately from Vault original
- preview path stored on Asset if current model supports it
- original Vault file remains authoritative
- previews are regeneratable

---

### 5. UI Display

Photos/Search/Review should display preview URL when available.

Expected:

```text
asset has display_preview_path
→ frontend displays preview URL

asset has no preview and raw browser display works
→ raw URL may still display

asset has no preview and raw browser display fails
→ placeholder/failure behavior remains acceptable
```

---

## Content Detection Guidance

Coder should inspect best current library support.

Preferred options may include:

- Pillow format detection
- `imghdr`-style detection if already used
- MIME sniffing by file header
- existing image loader behavior

The implementation should be conservative.

At minimum, detect:

```text
TIFF bytes
```

even when extension is not `.tif/.tiff`.

Suggested logic concept:

```text
open file with Pillow
actual_format = image.format

if actual_format in {"TIFF"}:
    generate JPEG preview
```

Do not build a large content-sniffing framework unless needed.

---

## Admin / Job Behavior

If existing HEIC preview generation is Admin-triggered, extend it if practical.

Preferred long-term direction:

```text
Display Preview Generation
```

covering:

- HEIC/HEIF
- TIFF/TIF
- extension/content mismatch images

For 12.29, acceptable options:

### Option A — Generalize existing preview job

Rename UI/job from:

```text
HEIC Preview Generation
```

to:

```text
Display Preview Generation
```

and support HEIC + TIFF + mismatch cases.

### Option B — Minimal extension

Keep current HEIC preview job name but extend backend to include TIFF/mismatch preview generation.

If Option B is chosen, document that UI naming should be cleaned up later.

Coder should choose the lower-risk path and report tradeoff.

---

## Reporting Requirements

Add basic operational visibility where practical.

Preview generation report/status should include:

- total pending previews
- HEIC previews generated
- TIFF previews generated
- mismatch previews generated
- failed previews
- failure reasons
- sample failed asset IDs/paths if practical

If extending existing HEIC preview reporting, preserve existing behavior.

---

## Metadata / Audit Considerations

If low-risk, record detected content mismatch in a non-destructive way.

Possible options:

- preview job report only
- asset diagnostic field if already available
- metadata observation note if appropriate

Do not add schema solely for mismatch audit unless coder determines it is very low-risk and useful.

For 12.29, report-level visibility is sufficient.

---

## Safety Requirements

### 1. Original Preservation

Do not modify:

- source files
- Vault files
- file extensions
- SHA256 identity
- provenance records

### 2. Non-Destructive Preview

Preview is derivative only.

It must not become canonical truth.

### 3. Existing HEIC Behavior

Do not regress HEIC preview generation.

### 4. Existing JPG/PNG Behavior

Do not unnecessarily generate previews for normal browser-renderable JPG/PNG files unless a mismatch or display failure is detected.

### 5. Failure Handling

If preview generation fails:

- record/report failure
- leave original intact
- UI may show placeholder
- do not block ingestion

---

## Step 2.5 — Codebase Reconnaissance Required

Before coding, coder should confirm:

1. Current preview generation service entry points
2. Current HEIC preview job model/status/UI naming
3. Current `display_preview_path` behavior on Asset
4. Where Photos/Search/Review choose preview URL vs raw URL
5. Whether Pillow can decode the observed TIFF/mislabeled JPG case
6. Whether TIFF multi-page files need special handling
7. Whether current preview storage can support TIFF/mismatch previews
8. Whether job/UI should be renamed to general Display Preview Generation
9. Whether any schema changes are needed
10. Whether existing HEIC validation remains covered

Pause and ask if generalizing the preview job would be risky.

---

## Coder Clarification Expectations

Before coding, coder should answer:

1. Can existing HEIC preview service be safely generalized?
2. Should Admin UI label change from HEIC Preview Generation to Display Preview Generation?
3. How will TIFF assets be identified?
4. How will extension/content mismatch be detected?
5. Will the known `.jpg`-extension / TIFF-bytes edge case be covered?
6. Are multi-page TIFFs handled by first page only?
7. Are any new dependencies required?
8. What report fields will distinguish HEIC, TIFF, and mismatch previews?

---

## Validation Test Plan

### Test Case 1 — Normal TIFF

Use a `.tif` or `.tiff` file.

Expected:

- asset ingests or already exists
- preview generation creates browser-safe preview
- `display_preview_path` populated
- UI displays image via preview

---

### Test Case 2 — Mislabeled TIFF as JPG

Use the known 12.28 edge case:

```text
extension/path says .jpg
actual bytes decode as TIFF
```

Expected:

- content mismatch detected
- JPEG preview generated
- UI displays preview successfully
- original Vault file unchanged
- no source/provenance mutation

---

### Test Case 3 — Existing HEIC

Run preview generation against HEIC asset.

Expected:

- existing HEIC preview behavior still works
- no regression in HEIC display

---

### Test Case 4 — Normal JPG

Use normal JPG.

Expected:

- no unnecessary preview generated unless already existing logic does so
- display still works

---

### Test Case 5 — Failed Preview

Use a corrupt image if practical.

Expected:

- preview generation fails gracefully
- failure recorded in report/status
- original untouched
- job continues processing other assets

---

## Validation Checklist

- TIFF preview generated
- mislabeled JPG/TIFF edge case preview generated
- HEIC preview still works
- Photos view displays preview
- Search/list thumbnails display preview
- Photo detail/review displays preview
- original Vault files unchanged
- preview failures logged/reported
- no regression to existing image display

---

## Deliverables

- TIFF/TIF preview support
- content mismatch preview support for TIFF-bytes cases
- updated preview generation service/job
- Admin/report visibility updates if needed
- validation results
- recommendation on whether to rename HEIC Preview Generation to Display Preview Generation

---

## Definition of Done

12.29 is complete when:

- TIFF/TIF assets can display in browser via preview derivative
- the known `.jpg` extension / TIFF bytes edge case displays correctly via preview
- original files remain unchanged
- HEIC preview behavior still works
- UI uses preview paths correctly
- preview generation failures are visible
- no ingestion/provenance/Vault behavior regresses

---

## Notes

This milestone improves archival robustness.

It is especially important for inherited/family photo collections where files may be scanned, renamed, mislabeled, or produced by older workflows.

Future related milestones may include:

- RAW preview compatibility
- PDF/document handling
- video playback
- Live Photo pairing
- source file anomaly reporting
- manual repair tools for mislabeled media

# 12.29 Clarification Answers## 1. UI/API namingUse Option B for 12.29.Keep the existing HEIC Preview job name/UI/API for now, but extend backend eligibility to cover:- HEIC/HEIF- TIFF/TIF- TIFF-bytes extension/content mismatch casesReason:- lower risk- avoids broad UI/API renaming churn- focuses 12.29 on display compatibilityDefer naming cleanup to a future small milestone:```textRename HEIC Preview Generation → Display Preview Generation

2. UI rename timing
   Defer UI/API rename.
   Do not rename the Admin card, API routes, or model names in 12.29 unless coder finds a tiny label-only change that is truly harmless.
   For 12.29, backend behavior may become broader than the current name. Document that naming cleanup is a follow-up.

3. Multi-page TIFF behavior
   First page/frame only is acceptable for this milestone.
   For 12.29:
   multi-page TIFF → generate preview from first page
   Do not implement multi-page TIFF navigation or page selection.

4. Mismatch detection scope
   Yes.
   For 12.29, it is enough to handle the practical case:
   Pillow opens filePillow reports actual format == TIFFextension is not .tif/.tiff→ treat as mismatch requiring preview
   Do not design a broad MIME-sniffing framework yet.
   The known .jpg extension / TIFF-bytes case must be covered.

5. Reporting
   Add lightweight per-type reporting if it does not require schema changes.
   Preferred report-level fields:
   heic_generatedtiff_generatedmismatch_generatedfailed
   Also include failure details if already practical.
   Do not add a schema migration solely for reporting.
   Report-level visibility is sufficient for 12.29.

6. Preview generation eligibility
   Generate derivatives for eligible assets where:
   display_preview_path IS NULL
   This should repair the known broken raw-display cases where no preview exists yet.
   If a preview already exists, do not regenerate it in 12.29 unless there is an existing safe force/regenerate mode.
   No force-regeneration requirement for this milestone.

7. Normal JPG/PNG behavior
   Do not generate previews for normal JPG/PNG files.
   Exception:
   extension says JPG/PNGbut actual Pillow format is TIFF
   or another specifically handled mismatch case.
   For 12.29, normal browser-renderable JPG/PNG should remain on existing raw-display path.

8. Known edge-case validation
   Yes.
   If the known edge-case asset already exists in the DB, include it in 12.29 validation.
   Expected acceptance:

same original Vault file remains unchanged

preview derivative is generated

display_preview_path is populated

UI displays the preview successfully

SHA/provenance/source metadata unchanged

Known edge-case SHA:
1c8ead716ba5b2750c9890f6e941c1de8b31da4599b050e35d3befb3d8873cc0

Approved implementation direction
Proceed with your recommendation:

Option B

first-page TIFF preview

detect TIFF by actual Pillow format

cover TIFF extension and TIFF-bytes mismatch

lightweight report-level counts if no schema change

do not rename UI/API yet

do not generate previews for normal JPG/PNG
