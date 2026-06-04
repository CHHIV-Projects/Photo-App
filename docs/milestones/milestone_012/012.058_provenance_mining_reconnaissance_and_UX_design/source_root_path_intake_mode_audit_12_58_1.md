# Source Root Path Intake Mode Audit (Pre-12.58.2)

Date: 2026-05-22

## Scope

Audit of how source_root_path is assigned and used across these intake modes:

- local_folder
- external_drive
- cloud_export
- scan_batch
- from-path/direct import variants

## Core Mechanics (Shared)

- Ingestion source identity is keyed by:
  - source_label_normalized
  - source_type
  - source_root_path_normalized
- This is enforced via unique constraint on ingestion_sources.
- For from-path runs, source_root_path is set to the resolved from_path.
- Provenance source_relative_path is computed as source_path relative to source_root_path when possible.
- Source intake skip-known compares current source-relative paths against stored provenance.source_relative_path for the same ingestion_source_id.

## Mode-by-Mode Findings

### 1) local_folder

Who/what chooses source_root_path:

- CLI from-path flow: operator chooses --from-path, which becomes source_root_path.
- Interactive run_pipeline fallback defaults source_type to local_folder when a source folder is entered.
- Admin source-intake flow: source_root_path comes from pre-registered ingestion source record.

What root represents:

- Selected folder root (registration root for that source entry).

How source_relative_path is computed:

- Provenance upsert computes relative path from source_path to source_root_path.

Does source_root_path affect skip-known/source matching:

- Yes.
- Source registration matching includes normalized root.
- Skip-known relies on source_relative_path + ingestion_source_id generated under that root.

Break risk if semantics change:

- High for source-intake skip-known continuity (already-known files may be re-selected).
- Medium for provenance grouping/history continuity (new ingestion source identity if root changes).
- Low for SHA-based dedup correctness.

### 2) external_drive

Who/what chooses source_root_path:

- Same mechanism as local_folder.
- Operator/admin chooses the root; source_type tag is external_drive.

What root represents:

- Selected mount/folder root as registered for that source.

How source_relative_path is computed:

- Same relative-to-root computation in provenance upsert.

Does source_root_path affect skip-known/source matching:

- Yes, same as local_folder.

Break risk if semantics change:

- High for skip-known continuity across runs.
- Medium for source identity continuity.
- Low for hash dedup correctness.

### 3) cloud_export

Who/what chooses source_root_path:

- CLI from-path mode: operator-provided from-path becomes root.
- iCloud acquisition flow: root is resolved staging directory for source label.
- Acquisition requires existing source registration match by label/type/root.

What root represents:

- Export staging root (registration root for this export source).

How source_relative_path is computed:

- Same provenance relative-to-root computation.

Does source_root_path affect skip-known/source matching:

- Yes.
- Cloud-export intake additionally runs readiness filtering before selection.
- Skip-known still depends on ingestion_source_id + source_relative_path derived from root.

Break risk if semantics change:

- High for cloud-export source registration lookup and skip-known/caught-up behavior.
- Medium for live-photo pairing quality where source_relative_path participates in pairing key.
- Low for hash dedup correctness.

### 4) scan_batch

Who/what chooses source_root_path:

- No special scan_batch-specific root logic.
- If run with from-path, selected from-path becomes root.
- If not from-path but context requested via label/type, root is None.

What root represents:

- Either selected folder root (from-path) or empty root identity (no from-path context).

How source_relative_path is computed:

- With root: relative-to-root.
- Without root: None (or fallback behavior in readers).

Does source_root_path affect skip-known/source matching:

- Yes when from-path is used.
- No skip-known source pass is applied for existing-drop-zone mode.

Break risk if semantics change:

- Medium when scan_batch uses from-path and expects source continuity.
- Low when run entirely via existing drop-zone without source root.

### 5) from-path/direct import variants

A) from-path import (CLI/Admin intake):

- source_root_path = resolved from_path
- source_relative_path computed from that root
- skip-known uses relative paths for same ingestion_source_id
- root semantics changes are high risk for skip-known continuity

B) existing drop-zone direct import (no from-path):

- resolve_ingestion_context returns None if no source_label is provided
- if source_label/source_type provided without from-path, root is None
- source_relative_path cannot be computed from root and may be null/fallback
- skip-known source pass is not used (it is a from-path source scan feature)

Break risk:

- Low for ingestion correctness
- Medium for provenance consistency/readability if labels/types are used with null root

## Impact on Existing Subsystems

### Ingestion / dedup core

- Primary dedup is SHA-based and remains correct if root semantics change.
- Risk is operational continuity, not hash correctness.

### Provenance matching and review surfaces

- source_relative_path is root-dependent; changing root semantics alters hierarchy depth and prefix groupings.
- Source Review and related prefix logic can shift materially when root definition changes.

### Source intake skip-known

- Most sensitive area.
- Skip-known compares current relative paths to stored provenance relative paths under same ingestion_source_id.
- Root changes can cause known files to appear unknown.

### Live photo pairing

- Pairing key uses ingestion_source_id plus source-relative directory/basename.
- Root/relative changes can affect pairing grouping quality.

## Recommendation Before 12.58.2

- Keep current root semantics stable per registered source.
- If introducing new root semantics, treat as versioned behavior with explicit migration/backfill plan for:
  - ingestion_sources identity matching
  - provenance.source_relative_path consistency
  - skip-known historical continuity
  - live-photo pairing keys

## Evidence References

- ingestion source identity and root normalization:
  - backend/app/models/ingestion_source.py
  - backend/app/services/ingestion/ingestion_context_service.py
- run_pipeline source type/from-path behavior:
  - backend/scripts/run_pipeline.py
- skip-known implementation:
  - backend/app/services/ingestion/pipeline_orchestrator.py
- provenance relative computation:
  - backend/app/services/duplicates/lineage.py
- admin source intake uses registered source root:
  - backend/app/services/admin/source_intake_execution_service.py
- cloud_export/iCloud acquisition root and registration matching:
  - backend/app/services/icloud_acquisition/execution_service.py
- live photo pairing key path behavior:
  - backend/app/services/live_photo/pairing_service.py
