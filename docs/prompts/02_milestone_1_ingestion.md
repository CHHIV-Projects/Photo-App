Build Milestone 1: Core Ingestion Engine for the photo organizer project.

Goal:

Implement a safe, modular ingestion pipeline for local media folders.

Requirements:

1\. Recursively scan a selected local folder for media files.

2\. Support a configurable allowlist of approved file extensions.

3\. Reject unsupported files and very small likely-junk files.

4\. Move unreadable or invalid files into a quarantine folder.

5\. Compute SHA-256 for exact identity.

6\. Compute pHash for image files for visual duplicate detection.

7\. Store source volume name and original source path.

8\. Copy approved files into a local vault folder.

9\. Verify copied file integrity after transfer.

10\. Write asset records into PostgreSQL.

11\. Generate a structured ingestion summary report.

Important constraints:

\- source files must be treated as read-only

\- originals in the vault must never be modified

\- keep logic split into small modules

\- every major step should be independently testable

\- no AI or face recognition yet

\- no frontend UI required yet unless explicitly useful for testing

Please:

\- propose the module/file structure first

\- then implement one module at a time

\- include test instructions for each part
