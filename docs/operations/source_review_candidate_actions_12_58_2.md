# Source Review Candidate Actions 12.58.2

## 1. Milestone Goal
Milestone 12.58.2 adds preview-only candidate action cards to Source Review, computed from the selected hierarchy level without writing any state.

This milestone is intentionally non-mutating and frontend-first.

## 2. Scope Implemented
Implemented in Source Review UI:

- Candidate card section driven by selected hierarchy segment.
- Soft action wording using "Could become..." and "Could suggest...".
- Explicit safety copy: "Preview only / No changes will be made."
- Raw segment visibility alongside lightly cleaned proposed labels.
- Conservative person clue hints based on existing People display names and aliases.
- Date clue interpretation that shows raw text and normalized form only when obvious.
- Semantic root presented as disabled concept card only (no behavior change).

Not implemented in this milestone:

- No create/apply actions.
- No reviewed/ignored persistence.
- No semantic-root persistence or source_root_path mutation.
- No ingestion/provenance semantics changes.

## 3. Candidate Heuristics
### 3.1 Label Cleanup
Suggested labels are derived with light cleanup only:

- Remove simple numeric prefixes (example: "001. ", "6. ", "03 - ").
- Remove basic file extension suffix when present.
- Normalize separators/whitespace.
- Preserve original segment text in UI for trust and validation.

### 3.2 Person Clues
Person clue preview is conservative:

- Segment text is compared against existing People display names and aliases.
- Word-boundary matching is used to avoid broad fuzzy guesses.
- If one or more known people match, show matched display names.
- If no known people match, card remains preview-only with fallback suggestion text.

### 3.3 Date Clues
Date clue preview supports obvious patterns only:

- Month/year ranges (example: "6-75 to 12-76").
- Year ranges including decade suffix shorthand (example: "1962 to 90's").
- Single 4-digit years.

Display behavior:

- Show raw + interpreted value when obvious.
- Show raw only when a date-like pattern is present but ambiguous.
- No metadata writes or event assignment.

## 4. Read-Only Guarantees
- No new backend mutation endpoints.
- No new database schema/migrations.
- No persisted candidate table.
- No Source Review write actions enabled.
- Semantic root remains concept-only; no source_root_path updates.

## 5. Backend Change Policy
This milestone keeps backend behavior unchanged.

Data used by candidate previews is already available from existing read-only Source Review endpoints and existing People listing API.

## 6. Action Readiness Matrix
This matrix captures current system readiness and intentional milestone boundaries.

| Candidate Action | Preview Card in 12.58.2 | Existing Backend Capability | Ready for Future Wiring | Notes |
| --- | --- | --- | --- | --- |
| Could become Collection | Yes (disabled) | No direct collection domain endpoint | Partial | Requires future collection model/UX decisions. |
| Could become Album | Yes (disabled) | Yes (`/api/albums`, album asset membership endpoints) | Yes | Candidate->create/apply flow deferred by milestone boundary. |
| Could become Event | Yes (disabled) | Partial (event update/merge; photo event assign/remove exists) | Partial | Candidate-driven event creation/grouping flow not implemented. |
| Could suggest Person Clue | Yes (disabled) | Yes (people list/aliases, face/cluster assignment endpoints) | Partial | Uses conservative name/alias match only; no assignment action. |
| Could suggest Date Clue | Yes (disabled) | Partial (event assignment exists, metadata write paths separate) | Partial | Display-only interpretation; no metadata/event mutation. |
| Could suggest Place Clue | Yes (disabled) | Partial (place labels endpoints exist) | Partial | No place assignment/write action from Source Review. |
| Could suggest Tag/Title | Yes (disabled) | Limited direct tagging write path from Source Review | Partial | Candidate-only in this milestone. |
| Could mark as Reviewed | Yes (disabled) | Not wired for Source Review candidate rows | No | Explicitly deferred. |
| Could ignore this level | Yes (disabled) | Not wired for Source Review level ignore persistence | No | Explicitly deferred. |
| Could become Semantic Root | Yes (disabled) | Not allowed by milestone policy | No | Concept only; no persistence or path semantics mutation. |

## 7. UX Notes
- Candidate cards are informational and intentionally disabled.
- Main Source Review workspace remains focused on provenance, hierarchy, and match preview.
- Readiness matrix is documented here, not surfaced as normal user-facing UI content.

## 8. Validation Performed
- Frontend TypeScript diagnostics for Source Review component and styles: no errors.
- Frontend production build should be used as final validation for integration changes.

## 9. Follow-up Status (12.58.3)
- `Could become Album` moved from preview-only to active create flow in milestone 12.58.3.
- Other candidate actions documented here remain preview-only/deferred.
