# Visual Enrichment Workspace Foundation 12.60.3

## 1. Purpose
Milestone 12.60.3 establishes a dedicated Visual Enrichment workspace for Google Vision landmark/context review.

This milestone moves landmark/context review toward its product home while keeping Places focused on canonical Place/location editing.

## 2. Workspace Role
Visual Enrichment now serves as the review workspace for Google Vision landmark/context candidates.

Current active scope in this milestone:

- list landmark/context candidates from Google Vision observations
- review with Accept/Reject/Ignore status updates
- display source-asset context and candidate confidence/details

## 3. Why Visual Enrichment Is Separate From Places
Places remains centered on canonical Place data and user-facing location correction.

Visual Enrichment is oriented around image-derived context suggestions, which are evidence/candidates rather than automatic Place assignment.

This separation reduces workflow confusion between:

- geographic canonical location editing
- visual/context enrichment review

## 4. Landmark/Context Candidate Behavior
Visual Enrichment candidate listing uses existing observation APIs and filters:

- source_type = google_vision
- observation_type = landmark
- status default = pending

Displayed candidate data includes:

- thumbnail/preview when available
- filename or short SHA (12 chars) fallback
- suggested context label
- confidence
- status
- created timestamp (if present)
- linked place (informational only, if present)

## 5. Accepted/Rejected/Ignored Status Behavior
Visual Enrichment exposes primary actions:

- Accept
- Reject
- Ignore

Behavior in this milestone:

- updates observation status only
- does not change asset.place_id
- does not create/link Place from this workspace
- does not modify canonical Place fields

## 6. Candidate Selection Placeholder Behavior
A static Candidate Selection panel was added with explanatory text only.

No controls or execution logic were added for selecting pools/running Vision in this milestone.

## 7. Run History / Reports Placeholder Behavior
A static Run History / Reports panel was added with reference text to existing report output path:

- storage/logs/google_vision_reports/

No report browser or run controls were added.

## 8. Label/Object Placeholder Behavior
A static Future Labels / Objects panel was added to indicate current report-only state and future planning.

No label/object persistence or workflow was added.

## 9. No-GPS Placeholder Behavior
A static Future No-GPS Location Candidates panel was added to indicate separate future workflow.

No no-GPS location inference/apply behavior was added.

## 10. Safety Boundaries
Implemented boundaries for 12.60.3:

- no Google Vision execution from UI
- no asset.place_id changes
- no automatic Place creation/linking
- no canonical Place overwrite
- no label/object persistence
- no propagation to duplicates

Allowed write path in Visual Enrichment:

- observation status update only (accepted/rejected/ignored)

## 11. Validation Performed
Validated in this milestone:

- frontend diagnostics on touched files: clean
- Visual Enrichment tab is registered and renders
- candidate list uses pending default and status filter options:
  - pending
  - accepted
  - rejected
  - ignored
- row actions execute via existing patch endpoint and update list state
- Open Asset uses existing onOpenPhoto flow
- linked place displays informationally when present
- existing Places view remains intact
- frontend production build passes

## 12. Limitations
Current limitations by design:

- no candidate pool execution controls yet
- no run history browser yet
- no label/object review persistence yet
- no no-GPS location inference/apply workflow
- no propagation workflows (duplicates/selected sets) yet

## 13. Recommended Next Milestone
Likely next:

- 12.60.4 - Landmark/Context Persistence and Propagation Planning

Alternative:

- 12.60.4 - Visual Enrichment Candidate Selection and Run Controls
