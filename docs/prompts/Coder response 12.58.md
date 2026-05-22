# Coder Response 12.58
Date: 2026-05-22
Milestone: 12.58 - Provenance Mining Reconnaissance and UX Design

## 1. Scope Completed
Completed the reconnaissance and UX design pass for provenance mining / source review.
This was an information-gathering milestone only. No full Provenance Review workspace was implemented.

## 2. Files Inspected
Primary files reviewed:
- `backend/app/models/provenance.py`
- `backend/app/models/ingestion_source.py`
- `backend/app/models/asset.py`
- `backend/app/models/collection.py`
- `backend/app/models/collection_asset.py`
- `backend/app/models/event.py`
- `backend/app/models/source_intake_run.py`
- `backend/app/services/ingestion/ingestion_context_service.py`
- `backend/app/services/admin/source_intake_service.py`
- `backend/app/services/admin/summary.py`
- `backend/app/services/admin/source_intake_schema.py`
- `backend/app/services/albums/album_service.py`
- `backend/app/services/metadata/metadata_normalizer.py`
- `backend/app/services/photos/photos_service.py`
- `backend/app/services/icloud_acquisition/execution_service.py`
- `backend/app/api/albums.py`
- `backend/app/api/events.py`
- `backend/app/api/admin.py`
- `backend/app/schemas/admin.py`
- `backend/app/schemas/albums.py`
- `backend/app/schemas/events.py`
- `backend/app/schemas/ui_api.py`
- `backend/scripts/run_pipeline.py`
- `backend/scripts/migrate_duplicate_lineage.py`
- `backend/scripts/experimental/icloud_staging_adapter.py`
- `backend/scripts/experimental/icloud_scan.py`
- `backend/_validation_final_data.json`

## 3. Provenance Model Findings
The provenance model is a single table keyed around `asset_sha256` plus source-copy identity.

Key findings:
- provenance rows store exact source-path history
- one asset can have multiple provenance rows
- uniqueness is enforced on `(asset_sha256, source_path, ingestion_run_id)`
- provenance includes source label, type, root path, relative path, source hash, and ingestion run/source IDs
- provenance is treated as observation history rather than a replacement for canonical asset state

## 4. Source / Source-Profile Findings
The source registry is `ingestion_sources`.

Key findings:
- source identity is label + type + normalized root path
- source labels are user-facing and suitable for UI display
- `source_type` is a coarse acquisition bucket, not a semantic classification system
- current accepted source types include `local_folder`, `external_drive`, `cloud_export`, `scan_batch`, and `other`
- source root normalization is already handled in ingestion context helpers

## 5. Multi-Provenance Findings
Multi-provenance is already real in this dataset.

Evidence:
- the validation snapshot includes assets with `provenance_count: 3`
- the photo detail payload already returns a provenance array
- canonical/duplicate logic does not erase provenance rows

Conclusion:
- the workspace should operate on provenance observations, not just current vault paths

## 6. Path Hierarchy Parsing Findings
Path splitting is feasible, but the codebase does not yet have a dedicated provenance hierarchy parser.

Recommended parsing rules:
- prefer `source_relative_path` when present
- otherwise derive relative path from `source_root_path` and `source_path`
- normalize separators to `/`
- preserve original segment text for display
- compare with normalized prefixes for matching

Key nuance:
- Windows drive letters and technical export wrappers should not be treated as semantic hierarchy levels

## 7. Path Prefix Query Feasibility
Prefix queries are feasible, but the current implementation is broad-text search, not a dedicated path-prefix engine.

Findings:
- provenance search already filters across source label, type, root path, relative path, and source path using case-insensitive `LIKE`
- provenance rows are indexed by asset SHA-256, not by path prefix
- `source_relative_path` should be the preferred field for a future provenance browse workspace

Recommendation:
- use normalized prefix matching instead of generic substring search for the review workspace

## 8. Source-Type Classification Recommendation
Recommendation:
- keep `source_type` as the coarse acquisition class
- add a separate semantic classification layer for folder segments later

Practical classification guidance:
- `local_folder` and `external_drive` are most likely to contain human-organized folder clues
- `cloud_export` often contains a technical wrapper plus meaningful inner structure
- `scan_batch` may contain archive clues but should be treated conservatively
- `other` should default to manual review

## 9. Candidate Clue Model Recommendation
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
- candidate clues should be manually approved
- do not auto-apply folder clues in 12.58
- allow multiple candidate clues per segment when warranted

## 10. Collection / Album / Event Implications
Current model shape:
- `Collection` is the manual grouping container and effectively the album-like model in the codebase
- `CollectionAsset` is the many-to-many membership table
- `Event` is a separate time bucket attached through `Asset.event_id`

Recommendation:
- provenance-derived folder levels should not directly map to Collection/Album/Event during the first pass
- instead, surface a provenance group candidate and let the user choose the target type

## 11. Proposed Provenance Review UX
Recommended UX:
- left panel: source roots and selected asset provenances
- middle panel: hierarchy levels for the selected provenance path
- right panel: matching assets for the selected prefix
- action panel: create collection, create album, create event, apply clues, mark reviewed, ignore level

Behavior recommendation:
- open the workspace from photo detail or another asset-centric surface
- show all provenance rows for the asset immediately
- allow a user to click one hierarchy level and see sibling assets under that path prefix

## 12. Candidate Action Recommendations
Recommended actions:
- view assets under this level
- create collection from this level
- create album from this level
- create event from this level
- apply person clue
- apply date range
- apply place clue
- apply tag / thing / object clue
- mark reviewed
- ignore this level

Existing API support assessment:
- album/collection creation and membership APIs already exist
- event list/detail/update/merge APIs exist
- no dedicated create-event-from-provenance flow was found in the reviewed surfaces

## 13. Cloud Source Metadata Findings
Current cloud metadata findings:
- experimental iCloud staging code can enumerate albums and report album names and counts
- the scan/staging tools can inspect filenames, sizes, dates, item types, and version keys
- the stable acquisition/run surfaces store source identity and run status, but not rich cloud album membership data

Gaps:
- no first-class shared-album membership model was found
- no first-class favorite flag model was found
- no explicit cloud asset ID field was found in the core provenance/source schema

## 14. Future Source Cleanup Considerations
Future cleanup must preserve provenance history.

Important preservation items:
- exact source path
- root path and relative path
- ingestion source and run IDs
- source hash if available
- timestamps and source labels

Hard constraints:
- no source deletion
- no vault deletion
- no destructive cleanup
- no automatic canonical changes

## 15. Recommended 12.58.1 Implementation Plan
Recommended next milestone slice:
1. Create a read-only Provenance Review / Source Review shell.
2. Reuse the existing photo detail provenance payload for the selected asset.
3. Split the selected provenance path into hierarchy levels.
4. Add prefix matching to show sibling assets under the selected level.
5. Show asset counts and small sample thumbnails.
6. Add placeholder action buttons without writing data.

## 16. Risks / Open Questions
Main risks:
- substring matching could be mistaken for real prefix matching if normalized too loosely
- technical export wrappers may be misread as semantic folder structure
- large provenance tables may need indexing before a browse-heavy UI is practical
- cloud-export and local-folder paths may need different heuristics for semantic segment detection

Open questions:
- should `source_relative_path` become mandatory for future sources
- should the workspace allow user-defined semantic-root overrides
- should provenance group candidates be stored persistently in the first implementation, or stay read-only for now
- should albums and collections remain unified in the data model or split later

## 17. Safety Confirmation
Confirmed safe scope for this milestone:
- no source files were deleted
- no vault files were deleted
- no media files were modified
- no automatic album, collection, event, date, person, or place actions were applied
- no ingestion or source-intake behavior was changed
- no destructive source-copy cleanup was performed

## 18. Suggested Closeout
Recommended summary position for the milestone:
- provenance mining is now mapped well enough to start a read-only Source Review workspace in 12.58.1
- the current data model already supports provenance history and multi-copy lineage
- the main remaining work is browse UX, prefix querying, and user-approved candidate actions
