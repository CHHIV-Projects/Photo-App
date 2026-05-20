# Face Review Cluster Cleanup 12.55

Date: 2026-05-20
Scope: Face Review person/status filtering, safe merge confirmation hardening, and alias design planning.

## 1) Current-State Findings

- Face Review already had cluster list/detail, cluster assign/reassign, ignore, face move, and merge actions.
- People view already had person-name search, but Face Review cluster pane did not.
- Cluster API already supported `include_ignored`, but frontend did not request ignored clusters.
- Merge behavior already existed, and backend already blocked conflicting person-assignment merges.

## 2) Person Search Behavior

- Added person-name filter directly in Face Review cluster pane.
- Filtering matches `ClusterSummary.person_name` (case-insensitive contains).
- For unassigned clusters, the query matches only via "unassigned" text fallback.

## 3) Cluster Status Filters

Added Face Review status filters:

- `All`: assigned + unassigned, excluding ignored.
- `Assigned`: `person_id != null` and not ignored.
- `Unassigned`: `person_id == null` and not ignored.
- `Ignored`: ignored only.

Ignored clusters remain hidden unless explicitly selected via `Ignored`.

## 4) Cluster Assignment/Reassignment Behavior

- Existing assign/reassign flows remain unchanged.
- Assignment is still cluster-level (`FaceCluster.person_id`).
- Person selection remains name-based in UI.

## 5) Cluster Merge Behavior

12.55 keeps merge implementation and hardens UX:

- Added custom merge confirmation dialog.
- Dialog shows:
  - source cluster
  - target cluster
  - source assigned person
  - target assigned person
  - source face count
  - target face count
  - source cluster removal flag
  - irreversible warning

Pre-merge safety checks in UI:

- target cluster required
- target must be loaded in current cluster list
- source/target cannot be same cluster
- cannot merge into ignored target
- strict block if source and target have different non-null assigned people

Backend safety remains in place and authoritative.

## 6) Merge Safety Rules

- No silent assignment conflict resolution.
- No automatic merge behavior.
- Source cluster removal is explicitly disclosed as irreversible in confirmation text.

## 7) Person Alias Design

12.55 is design-only for aliases (no schema/API implementation).

Recommended model for 12.56:

- New table: `person_aliases`
  - `id`
  - `person_id` (FK to `people.id`)
  - `alias_text`
  - `normalized_alias` (lower/trimmed for search)
  - `created_at_utc`
- Index `normalized_alias` for search.

Rules recommendation:

- Alias uniqueness: globally unique for v1 alias search clarity.
- Duplicate alias values: disallowed globally.
- Search behavior: people search matches `display_name` OR alias.
- Picker behavior: show canonical display name with alias context in results.

Migration/backfill:

- No backfill required for v1.
- Existing `people.notes` remains freeform, not parsed as aliases.

## 8) Validation Performed

- Frontend production build passed: `npm run build`.
- Type/lint checks included in Next.js build pipeline passed.

## 9) Known Limitations

- Cluster list currently follows API list defaults (current practical limit behavior remains in effect).
- Filters apply to currently loaded cluster set.
- If target cluster is not loaded, merge is blocked and user is prompted to adjust scope.
- Cluster list preview thumbnails remain unavailable from current backend payload (`preview_thumbnail_urls` empty).
- Person rename remains out of 12.55 implementation scope.

## 10) Recommended Follow-up Milestone

- `12.56 - Person Alias Support`

Optional follow-up increments:

- Face Review thumbnail polish (`preview_thumbnail_urls` population path).
- Cluster list pagination/load-more UX improvements for large datasets.
- Person rename API/UI if approved for a focused milestone.
