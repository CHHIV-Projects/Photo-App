```
# Milestone 12.60.6 — Context Label Propagation to Duplicate Group Members## GoalImplement the first controlled propagation workflow for accepted asset context labels.This milestone builds on:```text12.60.5 — Asset Context Label Model Foundation
```

12.60.5 introduced:

```
asset_context_labelsAccept as Contextcontext_type = landmarksource_observation_id linkageasset-level accepted context labels
```

12.60.6 should allow the user to explicitly apply an accepted context label from one asset to other assets in the same duplicate group.

Important terminology correction:

```
Do not call this “exact duplicate propagation.”
```

In this project:

```
Exact byte duplicates = same SHA256 / same file bytes
```

Those should generally not exist as separate Vault files because ingestion deduplicates by SHA256.

The useful propagation target is:

```
duplicate group members
```

meaning visually related / near-duplicate / alternate-encoded / resized / exported versions of the same or similar photo.

---

## Product Purpose

If Google Vision identifies a landmark/context label on one asset, the user may want to apply that accepted label to related duplicate-group members.

Example:

```
Source asset:  IMG_4819.jpgAccepted context label:  landmark: Midgley BridgeDuplicate group:  IMG_4819.jpg  IMG_4819_export.jpg  IMG_4819_HEIC_version.heicUser action:  Apply landmark: Midgley Bridge to other duplicate-group members
```

This avoids repeated manual review and avoids repeated Google Vision calls.

---

## Critical Safety Rule

Propagation must be explicit.

Do not automatically apply context labels to:

```
same lat/lonsame Placesame Collectionsame Albumall visually similar assets outside duplicate groupentire library
```

Default behavior remains:

```
this asset only
```

User must explicitly choose propagation.

---

## Scope

### In Scope

Implement:

- duplicate-group propagation preview for existing active context labels
- ability to view other assets in the same `duplicate_group_id`
- explicit confirmation before propagation
- propagate one active context label to selected duplicate-group members
- idempotent add behavior:
  - add if missing
  - count already-present if existing
- result counts:
  - requested
  - added
  - already present
  - skipped
  - failed
- Visual Enrichment UI action for propagation
- documentation and closeout response

### Conditional Scope

If safe and low-risk:

- allow checkbox selection of which duplicate-group members receive the label
- show thumbnails/filenames for duplicate-group members
- default checked only for obvious duplicate-group members if confidence data is available
- show canonical/source asset clearly
- show whether each target already has the label

### Out of Scope

Do not implement:

- automatic propagation
- same-lat/lon propagation
- same-Place propagation
- selected Album propagation
- selected Collection propagation
- near-duplicate confidence threshold redesign
- duplicate grouping algorithm changes
- Google Vision execution from UI
- label/object context propagation
- no-GPS location inference
- asset.place_id assignment
- Place creation
- Place linking
- canonical Place overwrite
- search changes
- Source Review integration
- ingestion/source changes
- media/vault changes
- captured_at changes

---

## Required Reconnaissance Before Coding

Inspect the current codebase and document relevant structures.

Likely files:

```
backend/app/models/asset.pybackend/app/models/asset_context_label.pybackend/app/api/asset_context_labels.pybackend/app/services/context_labels/service.pybackend/app/services/photos/photos_service.pybackend/app/services/photos/search_service.pybackend/app/services/duplicates/frontend/src/components/VisualEnrichmentView.tsxfrontend/src/lib/api.tsfrontend/src/types/ui-api.tsdocs/operations/asset_context_label_model_foundation_12_60_5.md
```

Document:

```
how duplicate_group_id is representedhow is_canonical is representedhow to query duplicate-group memberswhether duplicate group can contain source asset onlywhether exact/near distinction exists in current stored fieldshow context labels are currently listedhow Accept as Context creates labelshow filename/thumb URL can be returned for target assets
```

---

## Terminology Requirements

Use these terms in documentation and UI:

```
source assetduplicate groupduplicate-group memberspropagate context label
```

Avoid these terms unless explicitly discussing SHA256:

```
exact duplicatebyte duplicatesame file
```

Clarify:

```
Exact byte duplicates are normally eliminated by SHA256 deduplication.Duplicate-group members are related assets preserved as distinct assets.
```

---

## Propagation Behavior

## 1. Source Label

Propagation starts from an existing active context label.

Example:

```
asset_context_label:  asset_sha256 = source asset  label = Midgley Bridge  context_type = landmark  status = active
```

Only active labels are eligible.

For 12.60.6, support:

```
context_type = landmark
```

Do not implement object/scene/theme propagation yet.

---

## 2. Target Assets

Candidate targets are assets with the same `duplicate_group_id`.

Rules:

```
source asset must have duplicate_group_idtarget assets must share duplicate_group_idtarget assets must not be the source assettarget assets must exist
```

If no duplicate group exists:

```
show message:This asset is not part of a duplicate group.
```

If duplicate group has no other members:

```
show message:No other duplicate-group members are available.
```

---

## 3. Preview

Before propagation, show a preview.

Preview should show:

```
source asset filename/thumbnailcontext labelcontext typeduplicate group idtarget counttarget asset thumbnails/filenames if availablewhich targets already have the label
```

Example:

```
Propagate landmark: Midgley BridgeSource:  IMG_4819.jpgDuplicate group:  #739Targets:  IMG_4819_export.jpg — missing label  IMG_4819_HEIC.heic — already has label[Confirm Propagation]
```

---

## 4. Confirmation

User must confirm.

Required warning:

```
This will apply the accepted context label to selected duplicate-group members.It will not change Places, locations, source files, or metadata.
```

---

## 5. Add Behavior

For each selected target:

```
If target already has active label with same context_type + label_normalized:  do not duplicate  count as already_presentIf target does not have label:  create asset_context_labels row  source_type = propagated  source_observation_id = original source_observation_id if useful, or null if not appropriate  confidence = copied from source label if appropriate  status = active
```

Recommended:

```
source_type = propagated
```

Add optional fields only if current model supports them.

If model does not have propagation source tracking beyond `source_type`, document limitation.

---

## API Requirements

Add project-consistent endpoint(s).

Possible endpoints:

```
GET /api/asset-context-labels/{label_id}/propagation-previewPOST /api/asset-context-labels/{label_id}/propagate
```

### Preview endpoint

Response should include:

```
source context labelsource asset summaryduplicate_group_idtarget assetsalready_present status per targeteligible target count
```

Target asset summary:

```
asset_sha256filenamethumbnail_url if availableis_canonicalduplicate_group_idalready_has_label
```

### Propagate endpoint

Payload:

```
{  "target_asset_sha256s": ["...", "..."]}
```

If omitted and coder thinks safe, endpoint may default to all eligible duplicate-group members, but UI should still explicitly confirm.

Preferred:

```
UI sends explicit selected target_asset_sha256s.
```

Response:

```
{  "source_label_id": 123,  "requested_count": 2,  "added_count": 1,  "already_present_count": 1,  "skipped_count": 0,  "failed_count": 0}
```

---

## Frontend Requirements

Update Visual Enrichment.

### Where to show propagation action

Show action on accepted active context labels, not pending observations.

Possible UI placement:

```
Existing context labels for asset:  landmark: Midgley Bridge  [Propagate to Duplicate Group]
```

If the current row shows an accepted observation with an existing active context label, show propagation action there.

Do not show propagation action for:

```
pending observations without context labelrejected observationsignored observationsassets not in duplicate group
```

### Preview dialog/panel

Add simple preview panel/dialog:

```
Propagate Context LabelLabel:  landmark: Midgley BridgeSource:  IMG_4819.jpgTargets:  [x] IMG_4819_export.jpg  [x] IMG_4819_HEIC.heic[Confirm] [Cancel]
```

If checkbox selection is too much, show all eligible targets and confirm all. But checkbox selection is preferred if low-risk.

### Result display

After propagation, show counts:

```
Added: 1Already present: 1Skipped: 0Failed: 0
```

Refresh visible context labels if needed.

---

## Backend Requirements

### Service behavior

Implement propagation in context label service.

Requirements:

```
validate source label existsvalidate source label status = activevalidate source label context_type = landmark for this milestonevalidate source asset has duplicate_group_idvalidate targets are in same duplicate_group_idprevent source asset from being targetprevent duplicate active labelscreate labels idempotentlyreturn counts
```

### Transaction behavior

Preferred:

```
atomic per propagation request
```

If one target fails due to validation, decide whether to:

```
skip invalid target and report skipped/failed
```

or:

```
fail whole request
```

Recommended for v1:

```
Validate all targets first.If invalid target is supplied, reject request clearly.For already-present labels, count without failing.
```

---

## Duplicate Group Safety

Do not alter duplicate groups.

Do not recompute duplicates.

Do not change canonical asset selection.

This milestone only reads:

```
duplicate_group_idis_canonical
```

---

## Safety Requirements

Allowed writes:

```
create asset_context_labels rows on target duplicate-group members
```

Do not:

```
run Google Visionsend images externallycreate Placeslink Placeschange asset.place_idchange canonical Place fieldsmodify place_observations except if already existing UI does sochange duplicate groupschange is_canonicalmodify source/provenancemodify media/vaultchange ingestionchange captured_atcreate label/object persistenceperform broad propagation
```

---

## Validation Requirements

Validate:

### Preview

```
source asset with duplicate_group_id shows propagation previewtargets are same duplicate_group_id onlysource asset excludedalready-present target labels are identifiedasset without duplicate group shows clear message
```

### Propagation

```
propagate active landmark context label to duplicate-group membernew asset_context_labels row createdsource_type = propagatedcontext_type = landmarklabel copied correctlyasset/place/location fields unchanged
```

### Idempotency

```
run propagation twicesecond run does not create duplicatesalready_present_count increments
```

### Safety

```
cannot propagate to asset outside duplicate groupcannot propagate inactive/hidden/rejected labelcannot propagate non-landmark context type in this milestone
```

### UI

```
Visual Enrichment loadsexisting context labels displayPropagate action appears only where appropriatepreview displays targetsconfirmation runsresult counts display
```

### Regression

```
Accept as Context still worksReject/Ignore still worksPlaces view still loadsGoogle Vision harness still worksPhoto Review still loadsSource Review still worksfrontend build passesbackend diagnostics/tests pass
```

---

## Documentation Requirements

Create or update:

```
docs/operations/context_label_propagation_duplicate_group_12_60_6.md
```

Document:

1. purpose
2. terminology correction:
   - exact byte duplicate vs duplicate group
3. propagation scope
4. preview behavior
5. confirmation behavior
6. backend validation rules
7. idempotency behavior
8. safety boundaries
9. validation performed
10. limitations
11. recommended next milestone

---

## Deliverables

Required deliverables:

1. duplicate-group propagation preview
2. explicit propagation endpoint/action
3. idempotent propagation to duplicate-group members
4. Visual Enrichment UI action and confirmation
5. result count reporting
6. documentation
7. coder closeout response

Expected closeout file:

```
docs/prompts/Coder response 12.60.6.md
```

---

## Definition of Done

12.60.6 is complete when:

```
active landmark context label can be propagated to selected duplicate-group memberspropagation is explicit and confirmedsource asset is excluded from targetstargets must be in same duplicate_group_idduplicate labels are not createdresult counts are shownno Place/location/asset assignment changes occurno duplicate group/canonical logic changes occurdocumentation clearly distinguishes exact byte duplicates from duplicate-group propagation
```

---

## Required Coder Closeout Response

Create:

```
docs/prompts/Coder response 12.60.6.md
```

The closeout response should include:

1. Milestone title and date
2. Scope completed
3. Files inspected
4. Files modified or added
5. Duplicate-group findings
6. Propagation preview behavior
7. Propagation write behavior
8. Idempotency behavior
9. UI behavior
10. Safety confirmation
11. Validation performed
12. Deviations from prompt
13. Known limitations
14. Recommended next milestone

---

## Recommended Next Milestone

Possible next milestone:

```
12.60.7 — Visual Enrichment Candidate Selection and Run Controls
```

Potential scope:

```
choose candidate poolsrun Google Vision from Visual Enrichment on manually selected or canonical duplicate-group assetskeep propagation conservative
```

Alternative:

```
12.61 — No-GPS Visual Location Candidate Planning
```

Potential scope:

```
separate workflow for assets without geolocation metadatause Vision landmark/context as possible location cluesrequire explicit user confirmation before applying any location data
```

# Answers to Coder Questions — Milestone 12.60.6

## 1. Existing context label visibility

Yes. Update the Visual Enrichment context-label fetch so it includes both:

```text
source_type = google_vision
source_type = propagated

or otherwise does not hide propagated labels.

Reason:

After propagation, the user should immediately see the propagated context labels in the same Visual Enrichment area.

Preferred behavior:

Visual Enrichment should show active landmark context labels regardless of whether source_type is google_vision or propagated.

Do not limit displayed accepted context labels to only google_vision.

2. Target asset eligibility and visibility

For 12.60.6, propagate only to visible/active assets.

Preferred rule:

Eligible target assets:
  same duplicate_group_id
  not the source asset
  visible / not demoted / not ignored / not deleted

If the exact field is visibility_status, then exclude demoted/hidden/rejected assets unless coder finds that the current app semantics say otherwise.

Reason:

Demoted assets may represent lower-quality, intentionally hidden, or less user-facing items.
We should not apply new user-facing context labels to them by default.

If this filter is hard to implement, show demoted assets as non-default / unchecked, but preferred behavior is to exclude them from automatic eligibility for 12.60.6.

Document the exact rule used.

3. Target selection default

Yes. When the preview opens:

eligible missing-label members should be preselected by default
already-present targets should be shown but non-selectable

Preferred display:

[x] IMG_4819_export.jpg — will add
[ ] IMG_4819_HEIC.heic — already present

Already-present targets should count in the preview and result, but should not be selected for write.

4. Canonical member behavior

Yes. If the source asset is non-canonical, the canonical member should still be selectable as a target as long as it is in the same duplicate_group_id and otherwise eligible.

Rule:

Canonical/non-canonical status does not block propagation.
Same duplicate_group_id and visibility eligibility are the key rules.

Reason:

The user may accept context from a non-canonical asset first.
The label should still be allowed to propagate to the canonical representative if confirmed.
5. Validation policy for invalid target

Reject the whole request if any supplied target is outside the source duplicate group.

Preferred behavior:

Validate all targets first.
If any target is invalid:
  reject the request
  do not partially apply
  return clear error

Reason:

Propagation should be safe and predictable.
Partial application with invalid supplied targets could confuse audit/results.

Already-present labels are not invalid. They should count as already_present.

6. Source observation linkage for propagated rows

Copy source_observation_id from the source context label when present.

Recommended behavior:

source_type = propagated
source_observation_id = source_label.source_observation_id
confidence = source_label.confidence if present

Reason:

This preserves traceability back to the original Google Vision observation while still marking the propagated row as propagated.

If future audit requirements become more complex, we can add a propagation event/run table later. Do not add that now.

7. Where action appears in UI

Show Propagate to Duplicate Group on eligible existing active context labels, regardless of the current observation status filter.

Preferred:

If an asset row displays existing active context labels:
  show Propagate action on the active label when eligible

So if the user is viewing pending observations, but the row already has an active context label, propagation can still be available.

Do not show propagation action for:

pending observation without an active context label
rejected/ignored observation only
inactive/hidden context label
asset without duplicate_group_id

This keeps the action tied to the durable context label, not the observation row status.

Implementation Direction Confirmation

Coder’s recommended approach is approved:

- Add GET propagation preview endpoint for one context label.
- Add POST propagation endpoint with explicit target list.
- Active landmark labels only.
- Same duplicate_group_id only.
- Exclude source asset.
- Exclude non-visible/demoted assets for 12.60.6.
- Idempotent add with already_present counting.
- Reject whole request if any supplied target is outside duplicate group.
- Copy source_observation_id from source label when present.
- Use source_type = propagated on propagated rows.
- Visual Enrichment shows Propagate action on eligible active context labels.
- Preview panel includes target list and confirmation.
- Result banner shows requested, added, already present, skipped, failed.
  Important terminology

Use:

duplicate-group propagation

Do not call this exact duplicate propagation.

Reason:

Exact byte duplicates should generally not exist as separate Vault files because SHA256 deduplication handles them.
The target is duplicate_group_id members, meaning visually related/alternate version assets.