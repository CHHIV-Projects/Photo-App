# Milestone 12.44 — iCloud Acquisition + Source Intake Workflow Integration

## Goal

Improve the Admin workflow that connects iCloud Acquisition to Source Intake.

This milestone should make the operator flow clearer and easier:

```text
Run iCloud Acquisition
→ review staged files
→ prepare/run Source Intake for the same source
→ review intake result
```

This milestone should **not** delete staged files yet.

Staging cleanup will be handled separately in:

```text
12.44.1 — Delete Successfully Ingested iCloud Staging Files
```

---

## Context

Milestone 12.43 added an Admin UI card for iCloud Acquisition.

Current workflow:

```text
Admin UI launches iCloud Acquisition
→ icloudpd downloads files into storage/exports/icloud/<source_label>/
→ acquisition report is written
→ operator must manually use Source Intake separately
```

The architecture remains:

```text
icloudpd
→ storage/exports/icloud/<source_label>/
→ Source Intake
→ Drop Zone
→ Vault / DB / Provenance
```

Important boundaries:

- iCloud Acquisition does not write directly to Drop Zone
- iCloud Acquisition does not write directly to Vault
- iCloud Acquisition does not create DB Asset rows
- iCloud Acquisition does not create provenance
- Source Intake remains the ingestion authority
- staged files currently remain in `storage/exports/icloud/<source_label>/`

---

## Core Principle

> iCloud Acquisition downloads. Source Intake ingests.

12.44 improves the handoff between those two steps.

Do not collapse them into a fully automatic one-click workflow yet.

---

## Scope

### In Scope

- improve Admin handoff from iCloud Acquisition to Source Intake
- allow acquisition result to prepare/pre-fill Source Intake controls
- show staged file count clearly
- show recommended Source Intake settings
- show acquisition-to-intake next-step guidance
- show latest Source Intake result for the same source where practical
- reduce operator risk of choosing the wrong source label/path
- make it clear that staged files remain after intake
- prepare for 12.44.1 cleanup milestone

### Out of Scope

- automatic Source Intake execution immediately after acquisition
- deleting staged files
- moving staged files
- cleanup report generation
- iCloud credential storage
- scheduled sync
- NAS automation
- automatic post-intake enrichment chaining
- Live Photo playback
- iCloud mutation operations
- cloud-native iCloud provenance schema

---

## Required Workflow

### Desired Admin Flow

After iCloud Acquisition completes, the Admin UI should guide the operator:

```text
1. iCloud Acquisition completed.
2. X files are currently staged.
3. Next step: run Source Intake for this same source.
4. Click "Prepare Source Intake" or equivalent.
5. Source Intake controls are filled with the matching source/settings.
6. Operator explicitly clicks "Run Source Intake."
7. Source Intake result is shown.
```

Source Intake should still require an explicit operator action.

---

## Part 1 — Acquisition Card Next-Step Improvement

Update the iCloud Acquisition card so that after a completed acquisition run, it clearly displays:

```text
Files currently staged
Source label
Source root path
Report path
Recommended Source Intake command
Next step guidance
```

Suggested wording:

```text
Next step: Run Source Intake for this same registered source.
```

Also show:

```text
Staged files remain in the exports folder after intake. Cleanup will be handled by a separate explicit cleanup action.
```

Do not add cleanup behavior in this milestone.

---

## Part 2 — Prepare Source Intake from Acquisition

Add a UI action, button, or link such as:

```text
Prepare Source Intake
```

or:

```text
Use This Source for Intake
```

Behavior:

- takes the completed acquisition source label/source root
- fills or selects the corresponding Source Intake controls
- suggests source limit based on acquisition recent count or staged file count
- uses existing/default batch size
- scrolls/focuses Source Intake section if low-risk

The operator must still click:

```text
Run Source Intake
```

Do not auto-run intake.

---

## Part 3 — Source Intake Form Pre-Fill

When prepared from iCloud Acquisition, Source Intake should use:

```text
source_label = acquisition source label
source_type = cloud_export
source_root_path = acquisition staging path / registered source root
source_limit = staged file count or acquisition recent count
ingest_batch_size = existing default
```

Preference for `source_limit`:

```text
If file_inventory_count is available:
    source_limit = file_inventory_count
Else:
    source_limit = recent_count
```

Do not set source limit above normal safety bounds.

If staged file count is zero, show warning:

```text
No staged files currently available for intake.
```

---

## Part 4 — Source Registry Consistency

The handoff must use the registered source, not a free-text path.

Expected behavior:

- iCloud Acquisition card knows selected source
- Source Intake receives same source identity
- path displayed in Source Intake matches the registered source root
- avoid accidental duplicate labels or wrong roots

If source registry data is stale, refresh it before preparing Source Intake if low-risk.

---

## Part 5 — Source Intake Result Context

After Source Intake runs for an iCloud source, show or retain a summary that helps the operator know what happened.

Important fields:

```text
scanned
skipped known
selected
staged
processed new unique
DB skipped existing
failed/rejected
deferred/unready
remaining unknown
source_complete
report path
```

If this data already exists in the Source Intake card, no duplication is required.

But the iCloud Acquisition workflow should make it easy to understand:

```text
Acquisition staged files.
Source Intake processed them.
```

---

## Part 6 — Staging Folder Status Visibility

Show clear staging status:

```text
Files currently staged: X
```

If available, also show:

```text
extension counts
total bytes
```

Do not rely solely on `icloudpd reported downloads`.

Important distinction:

```text
icloudpd reported downloads = what icloudpd counted internally
Files currently staged = actual local files available for Source Intake
```

The UI should keep those labels distinct.

---

## Part 7 — Cleanup Notice Only

Add a visible note:

```text
Staged iCloud files are retained after Source Intake for now.
A future cleanup action will delete successfully ingested staging files after verification.
```

Do not implement deletion in 12.44.

Cleanup will be a separate milestone:

```text
12.44.1 — Delete Successfully Ingested iCloud Staging Files
```

---

## Backend Expectations

Prefer frontend/state integration if backend already provides enough data.

Backend changes are acceptable only if needed for safe handoff.

Potential backend/API needs:

- expose latest acquisition source label/staging path/recent count
- expose staged file count already added in 12.43
- expose recommended Source Intake command already added in 12.43
- expose source intake report summary if existing endpoints already provide it

Do not create a large new orchestration backend in 12.44.

---

## Frontend Expectations

Likely files/components:

```text
IcloudAcquisitionCard.tsx
SourceIntake card/component or AdminView source intake state
frontend API types
AdminView.tsx shared state
```

Preferred implementation:

- keep `IcloudAcquisitionCard` separate
- add a callback/event to prepare Source Intake
- avoid tightly coupling cards if possible
- no major refactor unless needed

If Source Intake is currently inline in `AdminView.tsx`, coder should choose the lowest-risk way to pre-fill it.

---

## Coder Reconnaissance Required

Before coding, confirm:

1. Where Source Intake form state currently lives
2. Whether Source Intake is inline in `AdminView.tsx` or separate component
3. Whether iCloud Acquisition card can pass selected source to Source Intake
4. Whether existing source registry data can be reused
5. Whether Source Intake can be safely pre-filled without refactor
6. Whether staged file count is available in frontend state
7. Whether source intake result summary is already displayed
8. Whether a small cross-card state lift is needed

Pause before a major AdminView refactor.

---

## Coder Clarification Expectations

Before implementation, answer:

1. What is the lowest-risk way to connect iCloud Acquisition to Source Intake?
2. Will this require extracting Source Intake into its own component?
3. How will `Prepare Source Intake` set the target source?
4. Will it use staged file count or recent count as source limit?
5. Will Source Intake still require an explicit Run click?
6. How will the UI make staged files / cleanup status clear?

---

## Validation Plan

### 1. Acquisition Completion

Run or use an existing completed acquisition.

Expected:

```text
iCloud Acquisition card shows completed status
file_inventory_count visible
report path visible
next-step guidance visible
```

---

### 2. Prepare Source Intake

Click:

```text
Prepare Source Intake
```

Expected:

```text
Source Intake controls select same source
source label matches acquisition source
source root path matches registered source root
source limit populated sensibly
batch size remains default
operator still must click Run Source Intake
```

---

### 3. Run Source Intake

Operator clicks Source Intake run.

Expected:

```text
Source Intake runs normally
Drop Zone used normally
Vault/DB/provenance updated only through Source Intake
```

---

### 4. Result Display

Expected:

```text
Source Intake result visible
selected/staged/new/skipped/failed/deferred counts understandable
source_complete visible
```

---

### 5. Staging Retention Notice

Expected:

```text
UI clearly states staged files remain after intake
no delete/move occurs
```

---

### 6. Frontend Build

Run:

```powershell
npm run build
```

Expected:

```text
passes
```

---

## Safety Requirements

- Do not auto-run Source Intake
- Do not delete staged files
- Do not move staged files
- Do not write acquisition output to Drop Zone
- Do not write acquisition output to Vault
- Do not store Apple password or 2FA
- Do not trigger iCloud mutation
- Do not hide Source Intake result
- Do not silently create sources

---

## Deliverables

- improved iCloud Acquisition card next-step UI
- `Prepare Source Intake` or equivalent handoff action
- Source Intake pre-fill behavior
- staged file retention notice
- validation summary
- frontend build result
- note of any remaining workflow gaps for 12.44.1

---

## Definition of Done

12.44 is complete when:

- completed iCloud Acquisition clearly points operator to Source Intake
- operator can prepare Source Intake for the same source with one action
- Source Intake remains explicitly operator-run
- staged file count is visible
- intake result remains visible and understandable
- staged file retention/cleanup status is clearly explained
- no cleanup/deletion is implemented
- frontend build passes
- no iCloud acquisition backend behavior regresses

---

## Explicit Deferrals

The following remain deferred:

```text
Delete successfully ingested staged files
automatic Source Intake execution
automatic post-intake enrichment chaining
scheduled iCloud sync
credential/session manager
NAS automation
Live Photo playback
iCloud mutation operations
```

---

## Planned Follow-Up

Next milestone:

```text
12.44.1 — Delete Successfully Ingested iCloud Staging Files
```

Planned cleanup direction:

```text
explicit operator-triggered deletion
only files verified as successfully ingested
no deletion from iCloud
no deletion from Vault
cleanup report required
```

---

## Notes

This milestone is about workflow clarity and operator safety.

It should make the two-step process feel guided without removing the operator’s explicit control.

# 12.44 Clarification Answers## 1. If acquisition source no longer maps to a registered sourceFail with a warning.`Prepare Source Intake` should not proceed if the acquisition source label/root no longer maps to a currently registered source.Show message such as:```textThe acquisition source is no longer registered or its path no longer matches. Please review the Source Registry before running Source Intake.

Reason:

Source Intake should use registered source identity

silent fallback/free-text behavior can create duplicate labels or wrong paths

source consistency is the whole point of this milestone

2. Intake limit overwrite behavior
   Overwrite the intake limit when the operator explicitly clicks:
   Prepare Source Intake
   Reason:

the click is an intentional handoff action

the source limit should reflect the acquisition result

otherwise stale values from a previous intake run could remain

Use:
file_inventory_count firstrecent_count fallback
Keep existing batch size default unless the user already changed it during the current session and changing it would be disruptive.
Minimum acceptable:
source_limit = file_inventory_count if available, else recent_countbatch_size unchanged/default

3. Scroll vs highlight
   Do both if low-risk.
   Required:
   scroll to Source Intake
   Preferred:
   brief visual highlight / focus on Source Intake section
   If highlight adds complexity, just scroll is enough for 12.44.

4. What should acquisition card pass?
   Pass both:
   source_labelsource_root_path
   Also pass if available:
   file_inventory_countrecent_count
   AdminView should verify that the source label and root path still match a registered source before prefill.
   Reason:

source_label alone may be ambiguous if historical duplicate labels exist

root path verification helps prevent wrong-source intake

this stays frontend-only and avoids backend changes

Approved implementation direction
Proceed with coder’s recommended low-risk approach:

keep Source Intake state in AdminView.tsx

do not extract Source Intake into a new component for 12.44

add callback prop from IcloudAcquisitionCard.tsx to AdminView.tsx

Prepare Source Intake resolves selected acquisition source against current source registry

prefill Source Intake with same registered source

use staged file count first, recent count fallback

Source Intake still requires explicit Run click

scroll to Source Intake after prefill

add brief highlight if easy

no backend work unless needed

no cleanup/deletion in this milestone

# 12.44 Batch Size Clarification

`Prepare Source Intake` should preserve a user-edited intake batch size if the operator already changed it in the current session.

Behavior:

```text
source/source label: overwrite from acquisition handoff
source limit: overwrite from staged file count, fallback to recent count
batch size: preserve current user-edited value

If the batch size field is empty, invalid, or untouched/default, use the existing Source Intake default.

Reason:

acquisition handoff should control the source and source limit
batch size is an operator tuning/control value
silently resetting it could be annoying or surprising

So:

Prepare Source Intake should not reset batch size unless the current value is invalid or missing.