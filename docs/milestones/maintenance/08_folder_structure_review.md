Apply a small project-organization cleanup pass to align the current workspace structure with our intended architecture.

Goal:

Keep the existing architecture intact, but clean up a few organizational details so the project stays maintainable as we move into later milestones.

Important constraints:

\- do not change working ingestion/database/event logic

\- do not refactor code behavior unless required for organization only

\- do not move or rename major code modules unless clearly necessary

\- keep changes small, safe, and beginner-friendly

Required cleanup tasks:

1\. Remove or relocate debug artifact files from backend root

\- backend/ should remain code-focused

\- if backend/event_check.json is only a debug/sample output artifact, either:

\- move it to docs/debug_samples/

\- or remove it if it is no longer needed

\- do not leave ad hoc JSON output files in backend root

2\. Standardize prompt/document naming going forward

\- use underscores instead of spaces in prompt filenames

\- specifically rename any prompt files with spaces to underscore versions if practical

\- example:

\- rename \`07_milestone_6_event clustering.md\`

\- to \`07_milestone_6_event_clustering.md\`

\- keep numbering and milestone meaning intact

\- update references only if needed

3\. Preserve storage folder structure

Keep these folders in place:

\- storage/drop_zone/

\- storage/quarantine/

\- storage/vault/

\- storage/previews/

\- storage/thumbnails/

\- storage/exports/

These are correct and should remain part of the project structure.

4\. Add a note or comment for Drop Zone intent

Somewhere appropriate (README or docs), clarify that:

\- Drop Zone is temporary staging

\- Vault is canonical hash-based storage

\- Drop Zone should not be treated as long-term storage

Do not implement cleanup automation yet, just document the intent.

5\. Verify generated folders stay ignored where appropriate

Confirm that generated/runtime folders remain ignored in git as appropriate, including:

\- storage/

\- frontend/.next/

\- frontend/node_modules/

\- .venv/

Adjust .gitignore only if needed.

What to explain after changes:

1\. what files were moved, renamed, or removed

2\. whether any prompt filenames were standardized

3\. where the debug/sample JSON files now live

4\. whether README or docs were updated to describe Drop Zone as temporary staging

5\. whether .gitignore needed any changes
