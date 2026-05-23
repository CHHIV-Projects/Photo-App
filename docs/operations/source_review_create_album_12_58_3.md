# Source Review Create Album 12.58.3

## 1. Purpose
Enable the first real write action in Source Review: create an Album from a selected provenance hierarchy level and add all matching assets under that prefix.

## 2. User Flow
1. Open Source Review from Photo Detail.
2. Select provenance row, hierarchy mode, and hierarchy level.
3. Review matching assets and candidate actions.
4. Use active Album action.
5. In confirmation panel:
   - edit album name
   - review selected context and match count
   - review sample assets
   - confirm filename-level warning checkbox when applicable
6. Confirm create action.
7. Backend recomputes full matching asset set server-side and performs write.
8. UI shows result counts and offers Open Albums.

## 3. Album/Collection Model Assumption
Current behavior remains collection-backed album model:

- Album UI maps to `collections` records.
- Membership maps to `collection_assets` records.

No model split or hierarchy redesign was introduced.

## 4. Backend Endpoint/API Used
New provenance-aware action endpoint:

- `POST /api/provenance-review/create-album`

Payload:

- `provenance_id`
- `level_index`
- `hierarchy_mode` (`relative` or `full_source_path`)
- `album_name`
- `conflict_mode` (`ask` or `use_existing`)

Implementation reuses existing album membership services for idempotent add behavior.

## 5. Matching Asset Selection Rules
Server-side selection reuses Source Review prefix logic:

- same context scoping rules
- same hierarchy parsing mode
- same prefix rule: exact prefix or `prefix/` boundary

The create action does not trust the frontend sample list.

## 6. All-Matching vs Sample Behavior
Source Review UI still displays sample items (first N), but create action uses full matching set.

- `matching_asset_count` reflects full matched set
- add/create uses full matched SHA list

## 7. Duplicate Album Name Behavior
Duplicate detection for create uses case-insensitive, trim-normalized, collapsed-whitespace comparison.

When a conflict is found:

- `conflict_mode=ask` returns `outcome=name_conflict` with existing album identity.
- UI offers:
  - Use Existing Album and Add Assets
  - Enter Different Name
  - Cancel

No silent duplicate album creation.

## 8. Duplicate Membership Behavior
Membership writes are idempotent.

Result includes explicit counts:

- `added_count`
- `already_present_count`
- `failed_count`

## 9. Safety Guarantees
This milestone only writes album/grouping records and membership.

No changes to:

- source or media files
- provenance rows
- canonical/duplicate logic
- people/events/places/date/tag assignment
- ingestion/source semantics

## 10. Validation Performed
- Backend editor diagnostics for changed provenance-review files: no errors.
- Frontend editor diagnostics for changed files: no errors.
- Frontend production build: passed.
- Manual runtime scenario validation is pending dedicated dataset walkthrough.

## 11. Known Limitations
- Album tab opens from success action; direct preselection of created album is not wired.
- Match-set > sample-size runtime verification may depend on local dataset availability.
- Use-existing flow is offered after conflict response in confirmation panel.

## 12. Recommended Next Milestone
- 12.58.3a: Album creation validation polish (album preselection and UX refinements), or
- 12.58.4: Event/date candidate actions after album flow validation.
