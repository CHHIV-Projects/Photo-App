# Provenance Mining Design 12.58
Date: 2026-05-22
Status: Reconnaissance and UX design complete

## 1. Overview
This milestone is a read-only reconnaissance and UX design pass for provenance mining / source review.
The goal is to use provenance paths and source metadata as human-guided organizational clues without implementing the full workspace yet.

## 2. Current Provenance Model
The current provenance model is a single table: `provenance`.

Observed fields:
- `id`
- `asset_sha256`
- `source_path`
- `ingestion_source_id`
- `ingestion_run_id`
- `source_label`
- `source_type`
- `source_root_path`
- `source_relative_path`
- `ingested_at`
- `source_hash`
- `notes`

Model facts:
- `asset_sha256` is a foreign key to `assets.sha256`.
- The table has a uniqueness constraint on `(asset_sha256, source_path, ingestion_run_id)`.
- That means one asset can have multiple provenance rows when they come from different runs or paths.
- The code preserves the provenance row as an observation record, not as a replacement for canonical asset state.

Normalization facts:
- `source_path` is preserved as recorded.
- Root-path normalization happens in ingestion context handling, where source roots are resolved and lowercased for matching.
- The provenance model itself does not perform hierarchical parsing.

## 3. Current Source Model
The source registry is `ingestion_sources` via `IngestionSource`.

Observed fields:
- `id`
- `source_label`
- `source_label_normalized`
- `source_type`
- `source_root_path`
- `source_root_path_normalized`
- `account_username`
- `created_at`

Source-type values currently accepted by the ingestion context helper and CLI:
- `local_folder`
- `external_drive`
- `cloud_export`
- `scan_batch`
- `other`

Findings:
- Source labels are user-facing and stable enough to surface in UI.
- `source_type` is a useful coarse bucket, but it is not fine-grained enough to infer folder meaning by itself.
- Source identity is determined by label + type + normalized root path.

## 4. Asset Multi-Provenance Behavior
The system already supports multiple provenance rows per asset.

Evidence:
- The provenance uniqueness key allows multiple rows per asset when `source_path` or `ingestion_run_id` differs.
- Validation data shows real multi-provenance examples with `provenance_count: 3` for multiple assets.
- The asset detail payload returns a provenance list, not a single provenance field.

Interpretation:
- Provenance mining should operate on provenance observations.
- It should not assume one asset equals one source copy.
- Duplicate/canonical logic remains orthogonal to provenance history.

## 5. Path Hierarchy Parsing Plan
Recommended deterministic parsing approach:
1. Prefer `source_relative_path` when present.
2. Otherwise derive a relative path by stripping the known `source_root_path` prefix from `source_path` when possible.
3. Normalize separators to `/` for parsing and comparison.
4. Preserve original segment text for display.
5. Compare prefixes using a normalized form, but never rewrite stored provenance history.

Specific handling recommendations:
- Windows drive letters should be treated as root metadata, not as hierarchy levels.
- Unix and NAS paths should be split on `/` after normalization.
- Cloud export paths should keep the technical export root separate from the human path candidate levels.
- If the root is repeated in the path, strip only the configured source root prefix, not arbitrary repeated substrings.
- If relative path is missing, fall back to the stored source path and show that the path is technical rather than semantic.

## 6. Path Prefix Query Feasibility
Prefix queries are feasible today, but only in a broad text-search sense.

Current behavior:
- The search service already filters provenance text fields using case-insensitive `LIKE` matching on source label, type, root path, relative path, and source path.
- Provenance rows are indexed by asset SHA-256, not by relative path.

Implications:
- A proper provenance workspace can query by prefix, but it should use a normalized path prefix rather than a generic substring match.
- `source_relative_path` should be the primary field for prefix queries where available.
- `source_path` can remain a fallback for rows that lack relative-path data.
- A dedicated prefix index would be useful later if the workspace needs large-scale traversal.

## 7. Source-Type Usefulness Classification
Recommended source interpretation layers:

- `source_type` stays as a coarse acquisition class.
- Path segments get a separate semantic classification layer.

Recommended segment classes:
- semantic
- technical
- mixed
- ignore

Recommended heuristics:
- `local_folder` and `external_drive` are more likely to contain human-organized folder clues.
- `cloud_export` often contains a technical export wrapper plus some meaningful inner folders.
- `scan_batch` often contains acquisition-oriented structure that may still carry archive clues.
- `other` should default to conservative/manual review.

Recommendation:
- Do not auto-promote `source_type` into a semantic decision.
- Allow user overrides for any segment that the heuristic classifies incorrectly.

## 8. Folder-Level Candidate Clue Model
Recommended candidate clue types:
- person
- date
- date_range
- place
- landmark
- object
- thing
- event
- album_title
- collection_title
- source_archive_label
- technical_noise
- ignore

Recommendation:
- Candidate clues should be reviewable, not auto-applied.
- A path segment can yield multiple candidate clues.
- Confidence should be explicit and visible.
- Review state should support at least: pending, accepted, rejected, ignored.

Example interpretation:
- `6. Pic of Mary` can surface a person candidate for Mary.
- `Pictures of Mary 1962 to 1990's` can surface a person candidate plus date-range candidate.
- `3. 6-75 to 12-76` can surface a date-range candidate.
- `Disneyland` can surface a place or landmark candidate.

## 9. Collections / Albums / Events Implications
Current model shape:
- `Collection` is the user-curated manual grouping entity.
- It is implemented as the album-like container in the codebase.
- `CollectionAsset` is a many-to-many membership table.
- `Event` is a separate time-bucket model stored directly on `Asset.event_id`.

Implications for provenance mining:
- A long folder structure should not be forced directly into Collection, Album, or Event during the first provenance pass.
- The better intermediate object is a provenance group candidate.
- Provenance group candidates can later spawn a Collection, an Album-like grouping, an Event, or a tag clue after human review.

Design recommendation:
- Collection = broad durable grouping.
- Album = current user-facing label for collection UI.
- Event = time-bounded occurrence.
- Provenance group candidate = source-derived grouping before type commitment.

## 10. Proposed Provenance Review / Source Review UX
Recommended first version layout:

- Left panel: source roots, source labels, and the selected asset’s provenance rows.
- Middle panel: the selected provenance path split into hierarchy levels.
- Right panel: assets matching the selected path prefix, plus sample thumbnails if practical.
- Action panel: create collection, create album, create event, apply date/person/place/tag clue, mark reviewed, ignore level.

Entry points:
- Open Provenance Review from a selected photo or asset detail screen.
- Show all provenance rows for the selected asset immediately.

Must-show content:
- selected asset preview
- source label/type/root
- split hierarchy levels
- asset count per level if feasible
- candidate clues per level
- explicit review actions

## 11. Candidate Actions
Recommended action set:
- View assets under this level
- Create Collection from this level
- Create Album from this level
- Create Event from this level
- Apply Person clue
- Apply Date Range
- Apply Place clue
- Apply Tag / Thing / Object clue
- Mark reviewed
- Ignore this level

Current API support assessment:
- Collection and album creation/membership APIs already exist.
- Event listing/detail/update/merge APIs exist, but there is no obvious create-event-from-selection endpoint in the current surfaces reviewed.
- Bulk provenance-derived creation will need a dedicated UI workflow even where backend primitives already exist.

## 12. Cloud Source Metadata Findings
Current iCloud-related capabilities found:
- Experimental staging code can enumerate iCloud albums and report album names and counts.
- The scan/staging code can sample filenames, sizes, created dates, item types, version keys, and identifier candidates.
- The acquisition flow records source label, source type, source root path, and run status information.

Current gaps:
- No stable DB model was found for shared-album membership.
- No stable DB model was found for favorites or other cloud-specific flags.
- No explicit cloud asset ID field was found in the core source/provenance model.
- Cloud metadata appears to be mostly operational/report-level today, not yet a first-class provenance browsing layer.

Recommendation:
- Treat cloud exports as one source type, not as a special UI path.
- Design the workspace so cloud metadata can be added later without changing the basic navigation model.

## 13. Future Source Copy Cleanup Considerations
The provenance design should preserve source-copy history for eventual cleanup workflows.

Must preserve:
- exact source path
- source root path
- source relative path when available
- source label and type
- ingestion source and ingestion run IDs
- source hash where available
- ingestion timestamp

Do not do now:
- source-file deletion
- vault-file deletion
- destructive copy cleanup
- automatic canonical asset changes

Reason:
- Future cleanup will need trustworthy source lineage and copy relationships.

## 14. Risks and Open Questions
Risks:
- Prefix matching can accidentally become substring matching if normalized carelessly.
- Technical export wrappers may be mistaken for semantic folder structure.
- Mixed cloud/local paths may need source-specific heuristics.
- Large provenance tables may require indexing before a browse-heavy workspace is practical.

Open questions:
- Should `source_relative_path` become mandatory for all future sources?
- Should the workspace allow user-defined “semantic root” overrides per source?
- Do we want a separate persistent table for provenance candidate groups, or should the first iteration remain read-only?
- Should albums and collections eventually diverge in the data model, or stay intentionally unified for now?

## 15. Recommended 12.58.1 Implementation Plan
Recommended first implementation slice:
1. Add a read-only Provenance Review / Source Review workspace shell.
2. Reuse existing photo detail provenance data as the asset entry point.
3. Split one selected provenance path into hierarchy levels deterministically.
4. Add prefix-based asset matching for the selected level.
5. Show counts and a small sample of matching assets.
6. Add candidate action placeholders with no destructive writes.
7. Add review state UI only after the browse model is stable.

Validation target for 12.58.1:
- user can open a provenance workspace from an asset
- user can inspect multiple provenance rows
- user can click a hierarchy level and see matching assets by prefix
- no source or media mutation is performed
