Update the Milestone 1 storage_manager to use hash-based vault storage instead of original filenames.

Goal:

Prevent filename collisions when different unique files have the same original name but come from different source folders.

Required behavior:

1\. Do not store files in the vault using the original filename.

2\. Use the file's SHA-256 hash as the canonical vault filename.

3\. Preserve the original file extension in lowercase.

4\. Store files in a 2-character hex prefix subfolder based on the first two characters of the SHA-256 hash.

5\. Example:

\- sha256: 3266ff1d665fa274fe36bf8244abe670e75c1e07ef86d425ae4f860cc7e43347

\- original extension: .JPG

\- destination path:

vault/32/3266ff1d665fa274fe36bf8244abe670e75c1e07ef86d425ae4f860cc7e43347.jpg

Implementation requirements:

\- remove or stop using the old filename collision logic that adds (1), (2), etc.

\- build destination path from sha256 + lowercase extension

\- create the prefix subfolder automatically if missing

\- if the exact destination file already exists, do not copy again

\- still verify copied file size after copy

\- keep source files read-only

\- keep code simple and modular

\- do not add database logic yet

Important design note:

Original filename and original source path should NOT be used as vault identity. They will be preserved later in metadata/database records, not in physical vault naming.

Please update:

\- backend/app/services/ingestion/storage_manager.py

\- backend/scripts/run_storage_manager.py only if needed

Then explain:

1\. what changed

2\. what old logic was removed

3\. what the new vault path format is
