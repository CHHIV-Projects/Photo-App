1\. Drop Zone file naming collisions

Use A: auto-suffix like (1), (2) in the Drop Zone only.

Reason:

\- Drop Zone is temporary staging, not canonical storage

\- we must not lose unique files that happen to share the same filename

\- canonical identity still happens later by SHA-256 in the Vault

\- original filename should be preserved as much as possible, but safe staging comes first

2\. Quarantine behavior

Use report-only quarantine for this milestone.

Reason:

\- keep Milestone 4 simple

\- track rejected files and reasons

\- include the quarantine path that would be used later

\- do not physically copy/move rejected files to quarantine yet

3\. Config source

Use existing config.py + environment variables for this milestone.

Reason:

\- minimal change

\- consistent with current setup

\- simple to understand

\- database-backed config can come later
