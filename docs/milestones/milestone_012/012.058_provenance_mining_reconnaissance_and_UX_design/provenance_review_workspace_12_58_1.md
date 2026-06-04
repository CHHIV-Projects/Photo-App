# Provenance Review Workspace 12.58.1

## 1. Workspace Purpose
Source Review is a read-only workspace for inspecting one asset's provenance rows, browsing hierarchy levels from a selected provenance path, and previewing assets under a selected path-prefix.

## 2. Entry Points
Implemented initial entry point from Photo Detail:

- Photo Detail -> Provenance section -> Open Source Review

Additional global tab:

- Header view switch includes Source Review
- If opened directly, it uses last selected Photo Detail asset when available

## 3. Provenance Row Display
For the selected asset, Source Review loads all provenance rows and shows:

- source label/type
- source relative path (or unavailable indicator)
- source path

Selection behavior:

- left panel always visible
- single-row assets auto-select row 0
- multi-row assets allow row switching

## 4. Path Hierarchy Parsing Rules
Implemented deterministic parsing in backend service.

Rule order:

1. Use source_relative_path when present and non-empty.
2. Else derive relative path by stripping normalized source_root_path prefix from normalized source_path when possible.
3. Else fallback to source_path.

Normalization and hierarchy behavior:

- path separators normalized to '/'
- repeated separators collapsed
- leading/trailing separators trimmed
- Windows drive segment (e.g., C:) stripped from semantic hierarchy levels
- filename remains final hierarchy level
- original stored provenance fields are not mutated

## 5. Prefix Matching Rules
Matching is backend-owned and read-only.

Selected context:

- selected provenance row + selected hierarchy level
- selected normalized prefix (joined segment path)

Source scope:

- if selected row has ingestion_source_id: match rows with same ingestion_source_id
- else: match rows with same source_label + source_type + source_root_path (null-safe equality)

Path match logic:

- compute candidate normalized path using same parser fallback policy
- match exact prefix OR prefix followed by '/'
- no broad substring matching

## 6. Matching Asset Display
For selected level, API returns:

- total_count of unique matching assets
- sample items limited to first 50
- thumbnail/display-safe URL metadata
- filename
- captured_at
- matched path fragment

Frontend display message:

- Showing first 50 of N matching assets
- or Showing N matching assets (when N <= 50)

## 7. source_relative_path Preference and Fallback Behavior
Implemented and surfaced in UI:

- source_relative_path preferred
- derived-relative fallback from source_root_path + source_path
- final fallback to source_path

If fallback occurred, selected provenance panel shows reason message:

- source_relative_path missing; derived from source_root_path + source_path
- relative path unavailable; using source_path fallback

## 8. Placeholder Actions
Implemented disabled placeholders only:

- Create Collection
- Create Album
- Create Event
- Apply Person Clue
- Apply Date Range
- Apply Place Clue
- Apply Tag
- Mark Reviewed
- Ignore Level

UI label states this is read-only in 12.58.1.

## 9. Read-Only Safety Guarantees
This implementation introduces only GET endpoints:

- GET /api/provenance-review/assets/{asset_sha256}
- GET /api/provenance-review/matches

No writes, no schema changes, no persisted candidates, no review-state mutations.

## 10. Limitations
- Matching currently computes candidates in service memory for correctness-first behavior.
- Technical path de-emphasis is hint-based (simple segment dictionary), not semantic classification.
- Match samples are capped at 50.
- No pagination UI for match results yet.

## 11. Recommended Next Milestone
- Add reviewed/ignored candidate persistence model and mutation endpoints.
- Add explicit technical-vs-semantic level controls.
- Add match-result pagination and optional source context tuning.
- Add Photo Review context entry point once behavior is validated.

## Follow-up: Shallow Hierarchy Investigation

Issue observed:

- Some rows showed only 2 levels in hierarchy while source_path appeared much deeper.

Root cause:

- Relative hierarchy mode intentionally prefers source_relative_path.
- If stored source_relative_path is already short (for example because source_root_path is deep), relative hierarchy will also be short.

Follow-up fix implemented:

- Added hierarchy mode switch in Source Review:
	- Relative hierarchy
	- Full path hierarchy
- Added parse diagnostics in debug panel and API payload:
	- source_path
	- source_root_path
	- source_relative_path
	- parse_mode_used
	- derived_relative_path
	- normalized_segments_relative
	- normalized_segments_full

Outcome:

- Users can now see full source folder depth when needed and understand exactly why relative hierarchy may appear shallow for specific rows.
