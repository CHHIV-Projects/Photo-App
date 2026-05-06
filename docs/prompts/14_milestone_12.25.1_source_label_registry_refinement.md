# Milestone 12.25.1 — Source Label Registry Refinement

## Goal

Reduce source-label typos and duplicate logical source names by making source labels selectable/reusable in the Admin Source Registry UI.

This milestone refines the source creation workflow introduced in 12.25.

The operator should no longer need to repeatedly type source labels from memory.

---

## Context

Milestone 12.25 added Admin-launched source intake, including:

- source registration
- source dropdown for intake
- source intake run/status/stop controls
- persistent `SourceIntakeRun` tracking
- shared ingestion orchestration
- Admin status polling

Current issue:

The Source Registry form allows manually typing a source label each time.

This can create accidental label variants, such as:

```text
Chuck PC
Chuck's PC
Charles PC
Chuck Laptop
```

These may represent the same logical source but become separate source identities, weakening provenance clarity and source-intake history.

---

## Core Principle

> Source labels should be intentional, stable, and reusable.

---

## Scope

### In Scope

- Add source-label reuse support in Admin Source Registry
- Display existing source labels in a dropdown/select control
- Allow creating a new label intentionally
- Reduce accidental duplicate labels from typos
- Preserve existing source identity model
- Preserve existing source registration and intake behavior

### Out of Scope

- source edit
- source delete
- source merge
- source deactivation/archive
- changing provenance identity rules
- changing skip-known logic
- iCloud/cloud source modeling
- two-level source database redesign
- source path browsing/folder picker

---

## Desired Admin Workflow

The Source Registry form should guide the operator through:

```text
1. Choose existing source label
   OR intentionally create new source label

2. Choose source type

3. Enter source root path

4. Register source path
```

This avoids repeated free-text label entry when the label already exists.

---

## UI Requirements

### 1. Existing Source Label Dropdown

In the Register New Source form, replace or augment the free-text Source Label field with a source label selector.

Recommended UI:

```text
Source Label
[ dropdown of existing labels ]

[ + New Label ]
```

Behavior:

- existing labels are selectable
- new labels can still be created intentionally
- selected label populates the source registration request
- new-label entry should be visually distinct from selecting an existing label

---

### 2. New Label Creation

If the operator chooses “New Label”:

- show text input for source label
- require non-empty value
- normalize consistently with backend source identity behavior
- reject or warn if it matches an existing label after normalization

Do not auto-generate labels.

The operator must choose or create the label.

---

### 3. Source Type

Keep source type simple.

For now, likely:

```text
local_folder
```

Do not add cloud types yet.

---

### 4. Source Root Path

Continue using text input for backend-visible source root path.

Make clear this is the path visible to the backend/server.

No folder browser required.

---

### 5. Registered Sources Display

Known Sources table should continue showing:

- source label
- source type
- source root path
- latest intake/report fields

If multiple sources share the same label but different root paths, this should remain visible and understandable.

---

## Backend Requirements

### Required

- provide existing distinct source labels to frontend
- ensure source creation still uses existing source identity logic
- prevent accidental duplicate labels if the normalized label already exists and user is trying to create a new label
- preserve source creation behavior from 12.25

### Preferred

Add or reuse endpoint support for distinct labels.

Possible options:

```text
GET /api/admin/source-intake/source-labels
```

or include distinct labels in the existing sources response.

Use existing Admin conventions.

---

## Important Identity Rule

Do not change the current source identity model in this milestone.

Existing identity remains based on the current system logic, approximately:

```text
source_label_normalized + source_type + source_root_path_normalized
```

Known source file logic remains:

```text
ingestion_source_id + source_relative_path
```

This milestone only improves how the operator selects/reuses labels.

---

## Validation Rules

### Existing Label Selection

Given an existing label:

```text
Chuck PC
```

The operator can select it from dropdown and register a new root path under that label.

Expected:

- no typo-prone retyping required
- source registration succeeds
- registered source appears in source list

---

### New Label Creation

Given a new label:

```text
Audrey iPhone Backup
```

The operator can intentionally create it.

Expected:

- source registration succeeds
- new label appears in future label dropdown

---

### Duplicate Label Warning

If operator selects “New Label” and types a label that normalizes to an existing label:

```text
Chuck PC
chuck pc
CHUCK PC
```

Expected:

- UI or backend should warn/reject and suggest selecting existing label instead

Do not silently create confusing duplicate labels.

---

## Safety Requirements

- no source records deleted
- no source records edited
- no provenance records changed
- no Vault changes
- no ingestion behavior changes
- no skip-known behavior changes
- no automatic labels

---

## Step 2.5 — Codebase Reconnaissance Required

Before coding, coder should confirm:

1. Existing `IngestionSource` fields and normalized label behavior
2. Whether distinct source labels can be derived from existing sources
3. Whether source creation currently detects duplicate normalized labels
4. Best way to expose labels to frontend:
   - existing sources endpoint
   - new source-label endpoint
5. Whether frontend form can support:
   - select existing label
   - create new label
6. Whether any backend validation change is needed

Pause if preventing duplicate normalized labels conflicts with existing source identity behavior.

---

## Coder Clarification Expectations

Before coding, coder should answer:

1. Can existing labels be derived safely from the current sources table?
2. Should duplicate label validation happen frontend-only, backend-only, or both?
3. Can the existing source registration endpoint accept both selected and newly typed labels without API change?
4. Is a new endpoint needed for distinct labels?
5. Are any schema changes required?

---

## Validation Checklist

### UI

- existing labels appear in dropdown
- user can select existing label
- user can intentionally create new label
- duplicate/new-label typo is warned or rejected
- source root path input still works
- source type input still works

### Backend

- source registration still works
- source identity rules unchanged
- no duplicate source record created for exact same identity
- distinct labels endpoint or equivalent works

### Regression

- Admin-launched intake still works
- source dropdown for Run Intake still works
- recent source reports still display
- CLI intake still works

---

## Deliverables

- source label dropdown/reuse UI
- intentional new-label creation path
- duplicate normalized label warning/rejection
- backend support if needed
- validation summary

---

## Definition of Done

Milestone 12.25.1 is complete when:

- operator can reuse existing source labels without retyping
- operator can intentionally create a new source label
- accidental label variants are reduced/prevented
- source registration still works
- Admin-launched intake still works
- source identity and skip-known logic remain unchanged

---

## Notes

This is a source-quality and operator-safety refinement.

It prepares the system for future larger imports and iCloud workflows by making source labels more stable and less typo-prone.

Future milestones may add:

- source edit
- source delete/deactivate
- source merge
- logical source hierarchy
- iCloud account/source registry

# 12.25.1 Clarification Answers## 1. New Label conflict behaviorUse hard reject.If the operator chooses “New Label” and enters a label that normalizes to an existing label, do not allow creation.Show a clear message:```textThis label already exists. Please select it from the existing label dropdown.
Reason:


source labels should be stable


this milestone exists specifically to prevent typo-driven variants


soft confirm still allows accidental fragmentation



2. Canonical label display
Show one deduped canonical label in the dropdown.
Do not show every raw historical variant.
Preferred display rule:


group by normalized label


show the best/first existing display value as the label text


optionally show count if there are multiple sources using that label


Example:
Chuck PC
not:
Chuck PCchuck pcCHUCK PC
If historical variants already exist, do not fix/merge them in 12.25.1. Just avoid making the dropdown worse.

3. Label source for dropdown
Use the existing /source-intake/sources response.
No new endpoint required unless implementation becomes awkward.
Reason:


no schema change


no new API surface


source list already contains labels


frontend can derive distinct labels safely



4. Source Type scope
Keep the current type options:
local_folderexternal_drivecloud_exportscan_batchother
Do not constrain to local_folder only.
Reason:


type options already exist


source registry should remain flexible


future iCloud/cloud export work benefits from preserving type vocabulary


But do not add new source types in this milestone.

5. UX preference
Use:
dropdown + explicit New Label toggle
This is preferred over a combo box.
Reason:


clearer distinction between reusing a known label and creating a new label


reduces accidental typo labels


easier for the operator to understand


Expected flow:
Source Label:  [dropdown of existing labels][Create New Label]  → reveals text input

Approved implementation approach
Proceed with your recommendation:


frontend + backend validation


no schema changes


reuse existing /source-intake/sources response for labels


hard block duplicate-normalized label only in New Label mode


show message directing user to select the existing label instead


