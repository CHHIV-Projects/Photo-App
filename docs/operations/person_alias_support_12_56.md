# Person Alias Support 12.56

Date: 2026-05-20
Scope: Canonical person aliases for deterministic lookup in search and assignment pickers.

## 1) Purpose

Aliases allow users to find the same canonical person by alternate names while keeping `display_name` as the primary visible identity.

Example:

- Display name: Charles Henderson
- Aliases: Charlie, Grandfather, Grandpa

Search/picker entry by any alias resolves to Charles Henderson.

## 2) Canonical Name vs Alias

- `Person.display_name` remains authoritative and primary in UI.
- Aliases are lookup aids only.
- Aliases do not change person IDs, cluster ownership, or clustering behavior.

## 3) Data Model

New table:

- `person_aliases`
  - `id` (PK)
  - `person_id` (FK -> `people.id`)
  - `alias`
  - `alias_normalized`
  - `created_at_utc`

Constraints and indexes:

- Global uniqueness on `alias_normalized`.
- Indexes on `person_id` and `alias_normalized`.

## 4) Normalization Rules

Centralized normalization helper:

- trim leading/trailing whitespace
- collapse repeated internal whitespace
- lowercase

Examples:

- `" Grandpa "` -> `"grandpa"`
- `"Grandpa   C."` -> `"grandpa c."`
- `"CHARLIE"` -> `"charlie"`

## 5) Uniqueness and Validation Rules

Alias create is blocked when normalized alias:

- is empty after normalization
- contains control characters
- exceeds max length (255)
- equals same person's display name
- equals any existing person's display name
- equals any existing alias (case-insensitive/normalized), including same person

v1 behavior is deterministic and globally unique.

## 6) API Behavior

Added APIs:

- `GET /api/people/{person_id}/aliases`
- `POST /api/people/{person_id}/aliases`
- `DELETE /api/people/{person_id}/aliases/{alias_id}`

Updated APIs now include aliases in person payloads:

- `GET /api/people`
- `GET /api/people-with-clusters`

Response shape includes:

- `aliases: string[]` (default `[]`)

`alias_normalized` is not exposed in normal UI responses.

## 7) UI Behavior

People view:

- shows alias chips per person
- supports add alias
- supports remove alias (hard delete)
- keeps current person-card structure (no redesign)

Search/pickers updated for alias-aware matching:

- Face Review cluster pane person filter
- Face Review assignment form person search
- Photo Review structured People filter candidate matching
- Presentation assignment picker search
- Unassigned Faces destination matching by person alias

## 8) Migration / Ensure

Added idempotent migration script:

- `backend/scripts/migrate_person_aliases.py`

Also updated fresh DB init to include `PersonAlias` model:

- `backend/scripts/init_db.py`

No backfill from `people.notes` was performed.

## 9) Validation Performed

- Frontend build passed: `npm run build`.
- Type/lint checks in Next.js build pipeline passed.

## 10) Limitations / Future Work

- Alias matching is case-insensitive contains for UI filtering, not fuzzy search.
- No per-user/scoped/relationship aliases in v1.
- No alias audit history/soft-delete.
- No automatic notes backfill.
- Optional future enhancement: dedicated people search endpoint if local filtering scale becomes a concern.
