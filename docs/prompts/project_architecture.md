\# ARCHITECTURE_ROADMAP.md

\#\# 1. Current State Summary

The system is a local-first photo organizer with a working backend pipeline and active browser-based UI.

Today it can:

\- ingest and deduplicate photos into canonical storage

\- extract and normalize metadata

\- classify capture type and capture-time trust

\- detect, cluster, and review faces

\- assign people to clusters

\- group photos into events and places

\- browse Photos, Events, Places, People, Review, and Unassigned Faces views

\- support manual correction workflows

\- run safe pipeline orchestration for new batches

\- support first-pass search and filtering

The system is now beyond prototype stage and has a usable operational foundation.

\---

\#\# 2. Development Phases

\#\#\# Phase 1 — Metadata, Provenance, and Context Integrity

Strengthen the accuracy of source data and context layers so future intelligence is built on trustworthy foundations.

Focus:

\- provenance visibility

\- multi-provenance support

\- photo detail improvements

\- event/place refinement

\- timeline foundation

\---

\#\#\# Phase 2 — Identity and Ingestion Scalability

Make the system safe and practical for growing archives by preserving reviewed identity work while allowing ongoing ingestion and processing.

Focus:

\- incremental face processing

\- non-destructive clustering updates

\- better duplicate / near-duplicate handling

\- canonical asset promotion/demotion rules

\- pipeline automation and scheduling

\---

\#\#\# Phase 3 — Retrieval and Curation

Make the archive easy to navigate, organize, and curate using metadata, provenance, and human-defined groupings.

Focus:

\- stronger search and filtering

\- collections and albums

\- timeline navigation

\- provenance-aware browsing

\- admin tooling

\---

\#\#\# Phase 4 — Content Understanding and Assisted Intelligence

Add richer automatic understanding of image contents and begin using user corrections as system guidance.

Focus:

\- person suggestion system

\- object/scene understanding

\- event/place refinement with multiple signals

\- confidence-aware automation

\- feedback-aware reprocessing

\---

\#\#\# Phase 5 — Distribution, Sharing, and Platform Expansion

Prepare the system for broader usage beyond a single local operator.

Focus:

\- external sharing

\- view-only external users

\- profile-based access

\- browser-to-app evolution

\- lightweight mobile companion

\---

\#\# 3. Milestone Roadmap

\#\#\# 11.5 — Photo Detail Improvements and Provenance Foundation

\*\*Goal:\*\* Strengthen photo detail view with metadata, context, and visible provenance so each photo can be inspected as a meaningful archival object.

\*\*Components:\*\* backend photo detail API, Photos UI, metadata services

\*\*Dependencies:\*\* existing Photos view, event/place APIs

\#\#\# 11.6 — Capture-Type Classification and Date Trustworthiness

\*\*Goal:\*\* Replace simplistic scan/digital assumptions with a better model for capture type and timestamp trust, including override support and reclassification.

\*\*Components:\*\* asset model, metadata normalization, event clustering, Photos UI

\*\*Dependencies:\*\* metadata normalization, scan-aware event grouping

\#\#\# 11.7 — Multi-Provenance and Duplicate Lineage

\*\*Goal:\*\* Support one canonical asset with multiple provenance sources, while preserving duplicate and near-duplicate lineage for archival trust and later decision-making.

\*\*Components:\*\* asset/provenance model, ingestion, dedupe services, photo detail UI

\*\*Dependencies:\*\* stable canonical asset model, provenance foundation

\#\#\# 11.8 — Incremental Face Processing

\*\*Goal:\*\* Process newly ingested assets without destroying existing reviewed face, cluster, and person work.

\*\*Components:\*\* face detection pipeline, face clustering services, orchestration script

\*\*Dependencies:\*\* pipeline orchestration, stable identity workflows

\#\#\# 11.9 — Timeline and Time Layer

\*\*Goal:\*\* Elevate time into a first-class navigation layer for browsing by year, month, decade, and date trust.

\*\*Components:\*\* backend time services, Photos/Events UI, filtering/navigation

\*\*Dependencies:\*\* capture-time trust model, event system

\#\#\# 11.10 — Collections and Albums Foundation

\*\*Goal:\*\* Introduce user-defined manual groupings built from curated search results and archival judgment.

\*\*Components:\*\* UI, metadata/search integration, collection/album data model

\*\*Dependencies:\*\* stable search/filtering, provenance and context visibility

\#\#\# 11.11 — Person Suggestion Engine

\*\*Goal:\*\* Suggest likely person assignments for new clusters using prior labeled identity work, with confidence and human confirmation.

\*\*Components:\*\* identity services, clustering logic, Review UI

\*\*Dependencies:\*\* incremental face processing, preserved person history

\#\#\# 11.12 — Object and Scene Understanding

\*\*Goal:\*\* Add structured recognition of “things” and visual themes such as dogs, cars, weddings, landscapes, etc.

\*\*Components:\*\* vision/content services, metadata model, photo indexing

\*\*Dependencies:\*\* stable photo detail, scalable processing strategy

\#\#\#11.12.5 — Non-Destructive Photo Editing and Derivative Assets

**\*\*Goal:** Add basic photo editing while preserving originals, supporting rotation as metadata-only and edits as new derived assets with lineage tracking.  
**\*\*Components:** asset model (parent/derived relationships), metadata services (rotation + edit parameters), storage layer (derived assets), Photos UI (edit/rotate actions)  
**\*\*Dependencies:** canonical asset model, provenance system (multi-source support), photo detail UI (11.5+), storage architecture for derived assets

\#\#\# 11.13 — Administrative Workflow Layer

\*\*Goal:\*\* Add admin-oriented controls for jobs, notifications, pipeline launch, monitoring, and corrective maintenance.

\*\*Components:\*\* admin UI, orchestration integration, status/error surfaces

\*\*Dependencies:\*\* pipeline orchestration, stable browser UI structure

\#\#\# 11.14 — Sharing and External Access Foundation

\*\*Goal:\*\* Add initial support for controlled sharing, beginning with private links and view/download-only external access.

\*\*Components:\*\* auth/access layer, sharing model, collection/album integration

\*\*Dependencies:\*\* collections/albums, provenance and metadata stability

\---

\#\# 4. Architectural Priorities

\#\#\# A. Provenance must become first-class

The system should move from storing a single source path to representing provenance as a meaningful archival layer. This is especially important for:

\- scans

\- duplicate lineage

\- canonical asset trust

\- future event and collection logic

\#\#\# B. Identity work must remain safe

Manual identity corrections are high-value user work and must not be lost during normal ingestion or processing. Incremental face processing is a priority.

\#\#\# C. Canonical asset logic must mature

The system should support:

\- one canonical asset

\- multiple provenance records

\- exact duplicate elimination

\- near-duplicate tracking

\- canonical promotion/demotion when better-quality versions arrive

\#\#\# D. Time should become a navigation layer

Time is not only metadata or event input. It should become a user-facing organizational layer with explicit trust handling.

\#\#\# E. Local-first performance needs planning

Target scale is roughly 15K–20K non-duplicate assets. Processing design should assume:

\- laptop + NAS as primary environment

\- optional mini server later

\- cloud reserved for heavy ML only when truly justified

\#\#\# F. UI should separate user and admin concerns

Long-term architecture should distinguish:

\- archive/user workflows

\- admin/operator workflows

without breaking the browser-first model.

\---

\#\# 5. Parking Lot Integration Strategy

Deferred features should be reconsidered in three ways:

\#\#\# Immediate promotion criteria

Promote a parking-lot feature into active roadmap when it:

\- solves repeated real-world workflow friction

\- improves data integrity

\- unlocks multiple future features

Examples:

\- multi-provenance

\- incremental face processing

\- provenance visibility

\#\#\# Mid-term reconsideration criteria

Reconsider when prerequisite systems become stable.

Examples:

\- collections/albums after stronger search and provenance

\- person suggestion after incremental identity-safe processing

\- object understanding after photo/context layers stabilize

\#\#\# Long-term reconsideration criteria

Reserve for later phases where platform and access models are more mature.

Examples:

\- semantic search

\- collaborative users

\- mobile feature expansion

\- cloud-assisted heavy ML

Parking-lot review should happen after each major phase and after any milestone that exposes a real archival workflow gap.

\---

\#\# 6. Constraints for Future Work

Future milestones must follow these rules:

\- Preserve current local-first architecture unless there is a strong reason not to

\- Do not introduce cloud dependency as a default requirement

\- Do not make destructive processing the default for reviewed identity data

\- Keep UI browser-based for now; app packaging is later

\- Keep backend logic centralized in services, not duplicated in UI

\- Prefer explainable heuristics before heavy ML

\- Prefer confidence-aware suggestions over silent automation

\- Use one canonical asset model, even when many provenance sources exist

\- Support both manual workflows and scheduled automation

\- Avoid architectural drift by building on existing Photos / Events / Places / People / Review patterns

\---

\#\# 7. Long-Term Vision

The system should become a rich, local-first photo intelligence platform that can:

\- organize archives by who, what, when, where, and source history

\- preserve archival provenance while still supporting high-quality canonical assets

\- automatically group and suggest labels with human correction and curation

\- support advanced browsing, filtering, timeline navigation, and collections/albums

\- scale to large personal archives without losing trust or control

\- remain private by default, with optional cloud assistance only when justified

\- eventually support sharing, selective external access, and a lighter mobile experience

The end state is not just a photo browser. It is a curated, intelligent archival system with strong provenance, explainable automation, and human-guided truth.
