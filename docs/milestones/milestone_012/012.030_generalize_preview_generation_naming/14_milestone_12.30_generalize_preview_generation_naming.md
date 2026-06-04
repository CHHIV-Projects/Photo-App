# Milestone 12.30 — Generalize Preview Generation Naming

## Goal

Rename the operator-facing preview generation concept from:

```text
HEIC Preview Generation
```

to:

```text
Display Preview Generation
```

This milestone is a cleanup/refinement milestone after 12.29 expanded the preview job beyond HEIC.

---

## Context

Milestone 12.21 introduced HEIC preview generation.

Milestone 12.29 expanded the same preview-generation workflow to support:

- HEIC / HEIF
- TIFF / TIF
- JPG/JPEG/PNG assets whose actual bytes decode as TIFF

However, the Admin UI and some backend/report wording still refer to this broader job as:

```text
HEIC Preview Generation
```

That name is now misleading.

The actual purpose is:

```text
Generate browser-safe display previews for assets that cannot reliably render directly in the browser.
```

---

## Core Principle

> Rename the operational concept without changing preview behavior.

This milestone should not alter storage semantics, ingestion behavior, preview eligibility, or existing preview generation logic.

---

## Scope

### In Scope

- Rename Admin UI card from `HEIC Preview Generation` to `Display Preview Generation`
- Update user-facing labels/help text
- Update status/report wording where low-risk
- Update frontend type/display naming where low-risk
- Update documentation/operator guide wording
- Preserve existing API behavior unless renaming routes is clearly low-risk
- Preserve existing preview generation behavior from 12.29

### Out of Scope

- changing preview storage layout
- changing `display_preview_path`
- regenerating previews
- adding RAW preview support
- adding PDF preview support
- adding video playback
- Live Photo pairing
- changing ingestion
- changing source intake
- changing duplicate/face/place processing
- broad backend model/table renaming if risky
- breaking existing Admin API routes

---

## Required Behavior

### 1. Admin UI Naming

The Admin card should display:

```text
Display Preview Generation
```

instead of:

```text
HEIC Preview Generation
```

The card should make clear that it covers:

```text
HEIC / HEIF
TIFF / TIF
mislabeled TIFF-content images
```

Suggested description:

```text
Generate browser-safe previews for HEIC, TIFF, and other assets that need display derivatives.
```

---

### 2. Existing API Compatibility

Do not break existing endpoints unless coder confirms all callers are updated and route change is trivial.

Preferred approach:

- keep existing backend route paths if they are named `heic-preview`
- optionally add aliases for future `display-preview`
- update only user-facing labels now

If route/model renaming is broad or risky, defer internal/API renaming.

This milestone is primarily operator-facing cleanup.

---

### 3. Report / Status Wording

Where low-risk, update report/status wording from HEIC-specific to display-preview-specific.

Examples:

```text
heic preview run
```

may become:

```text
display preview run
```

But do not perform large database/model renames merely for wording.

Existing per-type counts should remain visible:

- HEIC generated
- TIFF generated
- mismatch generated
- failed

---

### 4. Documentation Update

Update operator-facing documentation where relevant.

Likely files:

- iCloud export intake guide
- Admin/source intake operator notes if present
- milestone notes if appropriate

Update language from:

```text
HEIC Preview Generation
```

to:

```text
Display Preview Generation
```

where the broader job is intended.

Do not rewrite historical milestone records unless needed.

---

## Backend Requirements

### Required

- preserve existing preview generation behavior
- preserve existing job execution behavior
- preserve existing status/progress behavior
- preserve existing preview reports
- update user-facing response labels only if safe

### Preferred

- add a backward-compatible alias endpoint if coder thinks useful:

```text
/api/admin/display-preview/...
```

while preserving:

```text
/api/admin/heic-preview/...
```

But this is optional.

Do not introduce churn for route renaming if not needed.

---

## Frontend Requirements

### Required

- Admin card title changed to `Display Preview Generation`
- Admin card description updated
- button labels updated if needed
- status labels updated if needed
- per-type counts remain visible:
  - HEIC
  - TIFF
  - mismatch
  - failed

### Preferred

- update frontend type/interface names if low-risk
- preserve API client compatibility

---

## Safety Requirements

### 1. No Behavior Change

This milestone should not change which assets are selected for preview generation.

Preview eligibility remains as implemented in 12.29.

---

### 2. No Data Migration

Do not add schema migration solely for naming cleanup.

Do not rename DB tables unless absolutely safe and justified.

---

### 3. No Preview Regeneration

Do not regenerate existing previews merely because names changed.

---

### 4. No Route Breakage

Existing Admin UI/API behavior must continue working.

If new route names are added, existing route names should remain valid.

---

## Step 2.5 — Codebase Reconnaissance Required

Before coding, coder should confirm:

1. Current Admin card/user-facing labels that say `HEIC Preview`
2. Current API route names
3. Current schema/type names
4. Current backend model/table names
5. Current report wording
6. Current docs/operator guide references
7. Whether route aliasing is easy or unnecessary
8. Whether internal renaming would be risky

Coder should recommend the lowest-risk naming cleanup path before making broad renames.

---

## Coder Clarification Expectations

Before coding, coder should answer:

1. Which references can be safely renamed now?
2. Which internal references should remain `heic` for compatibility?
3. Should new `display-preview` API aliases be added or deferred?
4. Are there any tests/build steps required after renaming?
5. Which documentation files will be updated?

---

## Validation Checklist

### UI

- Admin displays `Display Preview Generation`
- Description correctly mentions HEIC/TIFF/mismatch preview support
- Run button still works
- Stop/status behavior still works
- per-type counts still show

### Backend

- existing preview generation job still runs
- existing routes still work
- no schema issues
- no preview eligibility changes

### Documentation

- operator guide uses new display-preview wording where appropriate
- no misleading HEIC-only wording remains in current user-facing docs

### Regression

- HEIC preview generation still works
- TIFF preview generation still works
- mislabeled TIFF-byte image preview still works
- existing preview paths still resolve

---

## Deliverables

- Admin UI naming updated
- relevant status/report wording updated where low-risk
- docs/operator guide updated
- validation summary
- note identifying any internal names intentionally left unchanged for compatibility

---

## Definition of Done

12.30 is complete when:

- operator-facing UI says `Display Preview Generation`
- user-facing wording no longer implies HEIC-only support
- existing preview job still works
- HEIC/TIFF/mismatch previews still generate
- existing routes/API behavior are not broken
- documentation reflects the broader preview purpose

---

## Notes

This is intentionally a small cleanup milestone.

Internal names may remain HEIC-specific temporarily if renaming them would create unnecessary risk.

Future related work may include:

- internal API/model rename cleanup
- RAW preview support
- PDF/document preview support
- video thumbnail generation



# 12.30 Clarification Answers## 1. Display-preview route aliasesDefer route aliases.For 12.30, keep the API surface unchanged:```text/api/admin/heic-preview/status/api/admin/heic-preview/run/api/admin/heic-preview/stop
Reason:


this milestone is operator-facing naming cleanup


existing routes work


adding aliases is not necessary yet


fewer moving parts means lower risk


We can add /display-preview/* aliases later if/when we do internal naming cleanup.

2. Documentation scope
Update only current operator-facing documentation.
Required:
icloud_export_intake_guide.md
Also update any active/current non-historical operator docs if they clearly describe the current Admin workflow.
Do not rewrite old historical milestone prompt files.
Historical files can retain the names that were true at the time.

3. Frontend internal type/function names
Keep internal frontend type/function names unchanged for 12.30.
Do not rename:
AdminHeicPreview*getHeicPreview*runHeicPreview*stopHeicPreview*
Reason:


internal names are compatibility details


renaming them adds churn with little user benefit


the operator-facing UI is what matters in this milestone



Approved 12.30 Implementation Direction
Proceed with the lowest-risk path:


Rename Admin operator-facing card title to:


Display Preview Generation


Update Admin card description to mention:


HEIC / HEIFTIFF / TIFmislabeled TIFF-content images


Update visible error/status/help text where low-risk.


Keep existing backend routes.


Keep existing backend model/table/schema names.


Keep existing frontend internal type/function names.


Update current operator guide wording.


No schema changes.


No preview behavior changes.


No route changes.


Validation:


frontend build/typecheck


manual Admin smoke test


confirm status/run/stop still work


confirm HEIC/TIFF/mismatch counters still render


