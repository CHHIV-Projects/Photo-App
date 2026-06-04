You are helping build a modular local-first photo organizer application.

Project goals:

\- safely ingest personal photo and video libraries from local folders and later cloud exports

\- preserve original files in immutable storage

\- detect exact and visual duplicates

\- extract metadata for browsing and search

\- support future AI enrichment such as faces, semantic search, and clustering

\- provide a modern web UI for browsing, search, and curation

Important constraints:

\- the user is not an advanced programmer

\- code must be simple, modular, readable, and easy to test

\- avoid overengineering

\- avoid giant monolithic scripts

\- every major feature must be implemented as a small, testable module

\- do not build future features unless explicitly requested for the current milestone

\- do not introduce unnecessary abstractions

Architecture decisions:

\- backend: FastAPI

\- database: PostgreSQL

\- queue: Redis + RQ

\- frontend: Next.js + TypeScript

\- canonical file identity: SHA-256

\- visual duplicate detection: pHash

\- originals are immutable after ingestion

\- all source locations are read-only

\- all metadata edits occur in database records, not original files

Coding style requirements:

\- use clear file and function names

\- keep functions small and focused

\- add docstrings and comments where helpful

\- prefer explicit logic over clever shortcuts

\- include type hints where practical

\- avoid hidden side effects

\- avoid tightly coupling modules

Testing requirements:

\- each module must be runnable and testable independently

\- include simple test instructions for every major module

\- do not assume external services unless explicitly requested

\- prefer local-first development

Current priority:

Build only the current milestone. Do not implement future milestones unless explicitly asked.
