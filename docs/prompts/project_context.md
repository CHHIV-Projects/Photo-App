\# PROJECT_CONTEXT.md

\#\# 1. Overview

AI-powered local photo organizer that ingests images, extracts metadata, detects and groups faces, and enables human-guided identity labeling with a growing UI for review, context inspection, and navigation.

The system combines:

\- automated organization (faces, events, places)

\- human correction and curation

\- evolving intelligence for large-scale photo archives

\---

\#\# 2. Tech Stack

\- Backend: Python 3.11, FastAPI

\- Frontend: Next.js (React)

\- Database: PostgreSQL

\- Cache (reserved): Redis

\#\#\# Computer Vision

\- Face Detection: OpenCV YuNet

\- Face Embeddings: DeepFace (FaceNet)

Environment:

\- Windows 11

\- Docker (Postgres/Redis)

\---

\#\# 3. Core Architecture

backend/

app/

models/ \# Asset, Face, FaceCluster, Person, Event

services/ \# ingestion, vision, clustering, identity, metadata logic

core/ \# config

db/ \# session/connection

scripts/ \# ingestion, normalization, clustering, classification workflows

storage/

vault/ \# canonical hash-based storage

drop_zone/ \# ingestion staging

quarantine/ \# rejected files

review/ \# face crop storage (UI + debug)

previews/ \# reserved

thumbnails/ \# reserved

exports/ \# reserved

frontend/

Next.js app (active UI layer)

docker/

postgres + redis

\---

\#\# 4. Data Flow / Pipeline

Drop Zone

→ Scan / Filter

→ Hash (SHA256) + Dedup

→ Vault

→ EXIF Extraction

→ Metadata Normalization

→ Capture-Type Classification (11.6)

→ Event Clustering

→ Face Detection (resized input)

→ Face (original-resolution bbox)

→ Face Crop (vault image)

→ Embedding (FaceNet)

→ Face Clustering (cosine similarity)

→ FaceCluster

→ Cluster Review (UI + crops)

→ Cluster Correction (UI actions)

→ Person Assignment (cluster → person)

\---

\#\# 5. Core Concepts

\- Asset: Canonical image (deduplicated, vault-stored)

\- Face: Detected face with bbox + confidence

\- FaceCluster: Group of similar faces (same-person candidate)

\- Person: Human-labeled identity

\- Event: Grouping of assets (time-based or provenance-based)

\- Provenance: Original source path / ingestion origin

\- Capture Type: digital \| scan \| unknown (11.6)

\- Capture Time Trust: high \| low \| unknown (11.6)

\- Vault: Source of truth for files

\---

\#\# 6. Active Systems

\#\#\# Ingestion & Metadata

\- ingestion + deduplication pipeline

\- EXIF extraction + normalization

\- capture-type classification (11.6)

\- reclassification script support

\#\#\# Face & Identity System

\- face detection (YuNet, scaled → original coords)

\- embeddings (FaceNet)

\- clustering (cosine similarity)

\- cluster review and correction

\- person identity assignment

\- cluster merge / move / ignore

\#\#\# Event System

\- time-based clustering (trusted timestamps only)

\- provenance-based clustering (for scans / low-trust assets)

\- scan-aware grouping (11.3)

\- event labeling from provenance

\#\#\# UI System (Active)

\- Review view (clusters + face operations)

\- People view (create + assign identities)

\- Photos view (image + metadata + faces)

\- Events view (event grouping display)

\- Places view (GPS grouping)

\- Unassigned Faces view (correction workflow)

\#\#\# Search & Filtering

\- people filtering

\- cluster filtering

\- photo filtering

\- events / places filtering

\---

\#\# 7. People Management System

\- FaceClusters represent candidate identities

\- Person entities are user-defined

\- Clusters can be assigned to a Person

\- Identity is human-controlled (no auto-labeling yet)

\- System supports:

\- assign cluster → person

\- reassign clusters

\- merge clusters

\- remove/move faces

Future-ready for:

\- person suggestion system

\- confidence-based assignment

\---

\#\# 8. Photo Review System

Two complementary workflows:

\#\#\# Review View (Primary Editing Surface)

\- cluster-based face review

\- move face

\- remove face

\- merge clusters

\- assign person

\- ignore clusters

\#\#\# Photos View (Inspection Surface)

\- full image display

\- face overlays

\- face list

\- metadata panel:

\- filename

\- asset ID

\- capture type (11.6)

\- capture time trust (11.6)

\- event

\- location (GPS)

\- provenance (source path)

Photos view is \*\*read-focused\*\*, not full editing UI.

\---

\#\# 9. Events / Timeline System

\#\#\# Current Behavior

\- Digital photos:

\- grouped by time (when capture_time_trust = high)

\- Scans / low-trust:

\- grouped by provenance (folder-based)

\#\#\# Event Characteristics

\- events are automatically generated

\- not manually created or edited yet

\- label may come from provenance (scan folders)

\- UI displays event groupings

\#\#\# Key Rule (11.6)

\- only high-trust timestamps participate in time-gap clustering

\- unknown/low trust excluded from time-based grouping

\---

\#\# 10. API Layer (for UI)

\#\#\# Clusters

\- GET /clusters

\- GET /clusters/{id}

\- POST /clusters/{id}/ignore

\- POST /clusters/{id}/unignore

\- POST /clusters/merge

\#\#\# Faces

\- POST /faces/{id}/unassign

\- POST /faces/{id}/move

\- POST /faces/{id}/create-cluster

\#\#\# People

\- GET /people

\- POST /people

\- POST /people/{id}/assign-clusters

\#\#\# Photos

\- GET /photos/{asset_sha256}

\- returns:

\- metadata

\- faces

\- event

\- location

\- provenance

\- capture_type

\- capture_time_trust

\- POST /photos/{asset_sha256}/capture-classification

\- manual override (11.6)

\---

\#\# 11. Key Constraints

\- Vault = single source of truth

\- DB = authoritative state

\- Bounding boxes in original coordinates

\- No destructive asset operations

\- Identity is human-controlled

\- Local-only processing

\- Scripts and APIs must be safe and explicit

\---

\#\# 12. Architecture Rules

\- Strong separation:

\- ingestion / metadata / vision / clustering / identity

\- API uses service layer only

\- UI never reimplements business logic

\- Review outputs are temporary

\- Prefer deterministic, rerunnable workflows

\---

\#\# 13. Current System Capabilities

\- End-to-end ingestion and deduplication

\- Metadata extraction and normalization

\- Capture-type classification and date trust model

\- Event grouping (time + provenance)

\- Face detection + embeddings + clustering

\- Full cluster correction workflow via UI

\- Person identity assignment

\- Multi-view UI (Review, Photos, Events, Places, People)

\- Search and filtering across entities

\---

\#\# 14. Known Limitations

\- No person auto-labeling yet

\- No incremental face processing (rebuild tradeoff exists)

\- No multi-provenance tracking (single source path only)

\- No timeline UI yet

\- No event editing (merge/split)

\- No object/scene recognition

\- No semantic search

\- Photos view lacks direct editing actions

\---

\#\# 15. Direction (Near-Term)

\- provenance visibility expansion

\- incremental face processing

\- person suggestion system

\- timeline / time-layer UI

\- collections / albums layer

\- object/scene understanding

\- semantic search

\---
