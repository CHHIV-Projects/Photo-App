Build a small fix milestone: preserve original source provenance through Drop Zone ingestion.

Goal:

Ensure the database stores the true original source path and original source filename, not the temporary Drop Zone staging path.

Context:

Source provenance is important for two reasons:

1\. it will later be used for grouping and organizing photos

2\. after production ingestion is trusted, it will support a future reclamation tool that can safely identify and delete redundant files from their original locations to free space on computers and cloud storage (excluding iPhone/iCloud)

Required behavior:

1\. When files are copied from the source folder into the Drop Zone, preserve the true original source path and original source filename in structured metadata.

2\. Do not let the Drop Zone path overwrite or replace original provenance.

3\. The database Asset record must store:

\- original_source_path = the real path from the source location

\- original_filename = the real original filename from the source location

4\. The Drop Zone remains temporary staging only.

5\. Vault remains hash-based canonical storage only.

Implementation guidance:

\- update the Drop Zone staging result objects so they carry original provenance forward

\- update scanner/filter/hasher/deduplicator/storage pipeline integration only as needed to preserve provenance cleanly

\- avoid large refactors

\- keep the existing milestone structure intact

\- do not add source volume tables yet unless absolutely necessary

\- do not build reclamation logic yet

\- do not add delete operations yet

Expected design direction:

\- staged files may have a Drop Zone path for processing

\- but each staged file should still retain metadata for:

\- original_source_path

\- original_filename

\- persistence to the Asset table should use the preserved original provenance, not the Drop Zone path

Files likely affected:

\- backend/app/services/ingestion/dropzone_manager.py

\- backend/app/services/ingestion/scanner.py and/or related ingestion record types if needed

\- backend/app/services/persistence/asset_repository.py

\- backend/scripts/run_dropzone_ingestion.py

\- any small supporting model/dataclass files needed

What to explain after coding:

1\. what files changed

2\. how original provenance is now preserved

3\. whether any dataclasses or record models changed

4\. how to verify the fix with check_assets_in_db.py

Use absolute resolved path.

Reason:
- ensures consistency across runs
- avoids ambiguity from relative paths
- supports reliable future matching for reclamation
- aligns with the goal of treating source locations as stable references

Proceed with absolute resolved paths for original_source_path.
