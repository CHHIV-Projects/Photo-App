Build Milestone 2: database layer for the photo organizer project.

Goal:

Create the first PostgreSQL + SQLAlchemy persistence layer for ingested assets so the pipeline can save file records after storage.

Scope for this milestone:

\- define the initial database model(s)

\- connect SQLAlchemy to PostgreSQL

\- add a simple database initialization path

\- save ingested asset records into the database

\- keep this milestone focused and minimal

Important constraints:

\- do not build EXIF extraction yet

\- do not build face recognition yet

\- do not build semantic search yet

\- do not build user auth yet

\- do not build album logic yet

\- do not build API CRUD screens yet

\- do not overengineer

\- keep code modular, readable, and beginner-friendly

Required design decisions:

1\. PostgreSQL is the database.

2\. SQLAlchemy is the ORM.

3\. SHA-256 is the canonical identity for a stored asset.

4\. The vault file path is the stored physical location.

5\. Original filename and original source path must be stored as metadata.

6\. The current ingestion pipeline remains:

scanner -\> filter -\> hasher -\> deduplicator -\> storage_manager

7\. This milestone adds database persistence after storage_manager succeeds.

Build these pieces:

1\. Database connection/session

\- create or complete SQLAlchemy engine/session setup

\- keep it simple

\- use environment/config settings if already scaffolded

\- include a way to test connectivity

2\. Initial model

Create an initial Asset model/table with fields similar to:

\- sha256 (primary key or unique canonical id)

\- vault_path

\- original_filename

\- original_source_path

\- extension

\- size_bytes

\- modified_timestamp_utc

\- created_at_utc (database/app timestamp for record creation)

3\. Database initialization

\- add a simple way to create tables for local development

\- include a small script or command for initializing the schema

4\. Persistence service

Create a small service module that accepts successfully copied files from storage_manager and writes Asset rows into PostgreSQL.

Behavior:

\- only persist files that were successfully copied

\- if an asset with the same sha256 already exists, do not create a duplicate row

\- handle duplicate insert attempts gracefully

\- return structured results:

\- inserted records

\- skipped existing records

\- failed inserts with reasons

5\. Test runner

Create a test runner script that:

\- runs the current ingestion pipeline on a chosen folder

\- writes successful results to the database

\- prints a summary:

\- scanned

\- accepted

\- rejected

\- unique

\- duplicates

\- copied

\- inserted

\- skipped existing

\- db failures

Project structure guidance:

Use files in locations like these unless a better fit already exists:

\- backend/app/db/session.py

\- backend/app/models/asset.py

\- backend/app/services/persistence/asset_repository.py

\- backend/scripts/init_db.py

\- backend/scripts/run_ingestion_to_db.py

Implementation notes:

\- keep models and services small

\- use type hints

\- add docstrings

\- avoid adding migration tooling yet unless absolutely necessary

\- avoid Alembic for now

\- prefer a simple create_all approach for this milestone

\- keep storage_manager unchanged unless a small integration point is needed

What to explain after coding:

1\. what files were added or changed

2\. how to initialize the database

3\. how to run the new ingestion-to-database test script

4\. how duplicate asset rows are prevented
