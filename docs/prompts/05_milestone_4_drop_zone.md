Build Milestone 4: Drop Zone and configuration-driven ingestion.

Goal:

Introduce a real Drop Zone stage in front of vault storage so ingestion becomes safer, more controllable, and closer to the intended production architecture.

Scope:

\- add a Drop Zone workflow

\- add a simple configuration system for ingestion rules

\- keep the existing scanner/filter/hasher/deduplicator/storage_manager modules where practical

\- do not build cloud fetchers yet

\- do not build mobile ingestion yet

\- do not build archive extraction yet

\- do not build quarantine UI yet

\- do not build source reclamation yet

\- do not build face or AI features in this milestone

\- keep this milestone focused, modular, and beginner-friendly

Target architecture for this milestone:

Source Folder

\-\> Drop Zone

\-\> scan/filter/hash/deduplicate

\-\> Vault

\-\> database persistence

Required behavior:

1\. Configuration system

Create a simple config-driven ingestion settings layer.

It should support at least:

\- approved file extensions

\- minimum file size in bytes

\- drop zone path

\- vault path

\- quarantine path

Implementation guidance:

\- use config.py and/or a simple config file approach already compatible with the current project

\- remove hardcoded extension/min-size values from the filter module if practical

\- keep configuration simple and easy to understand

\- do not build database-backed config yet

2\. Drop Zone staging

Create a service/module that copies candidate files from a chosen source folder into the Drop Zone first.

Rules:

\- source files remain read-only

\- files are copied, never moved or deleted

\- keep filenames as-is in the Drop Zone for this milestone

\- collect copy failures with reasons

\- return structured results

3\. Drop Zone ingestion pipeline

After files are staged in the Drop Zone:

\- run scanner on the Drop Zone

\- run filter

\- run hasher

\- run deduplicator

\- run storage_manager

\- run database persistence

4\. Quarantine handling

For this milestone, rejected files and copy/read failures should be recorded and optionally copied/moved into a quarantine folder only if simple to implement.

Do not overcomplicate this.

If quarantine movement is too much for this milestone, at minimum:

\- track rejected files

\- track reasons

\- store/report the quarantine target path that would be used later

5\. End-of-run reporting

The runner should print a summary including:

\- source files scanned

\- files copied to Drop Zone

\- Drop Zone scan count

\- accepted

\- rejected

\- unique

\- duplicates

\- copied to vault

\- inserted into DB

\- skipped existing

\- failures by stage

Project structure guidance:

Use files in locations like these unless a better fit already exists:

\- backend/app/services/ingestion/dropzone_manager.py

\- backend/app/services/ingestion/config_loader.py (only if needed)

\- backend/scripts/run_dropzone_ingestion.py

Implementation notes:

\- keep modules small

\- keep path handling explicit

\- preserve current ingestion modules unless small refactors improve reuse

\- keep database persistence step at the end

\- do not delete Drop Zone contents automatically yet unless very simple and safe

\- do not add scheduler logic yet

What to explain after coding:

1\. what files were added or changed

2\. how configuration is now handled

3\. how the Drop Zone flow works

4\. how to run the new Drop Zone ingestion script

5\. what is still deferred to later milestones
