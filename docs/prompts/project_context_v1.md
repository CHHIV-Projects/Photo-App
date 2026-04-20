# PROJECT_CONTEXT.md

## 1. Overview

AI-powered local photo organization system that ingests, deduplicates, analyzes, and organizes large photo archives while enabling human-guided correction and curation.

The system combines:

- automated structure (faces, events, albums, metadata)

- human correction workflows

- scalable architecture for long-term intelligence (search, tagging, canonicalization)

---

## 2. Tech Stack

- Backend: Python 3.11, FastAPI

- Frontend: Next.js (React)

- Database: PostgreSQL

- Cache / Queue: Redis (planned / partial)

### Computer Vision

- Face Detection: OpenCV YuNet

- Face Embeddings: DeepFace (FaceNet)

### Environment

- Windows 11

- Docker (Postgres + Redis)

---

## 3. Core Architecture

```
backend/
  app/
    models/        # Asset, Face, Cluster, Person, Event, Album, Provenance
    services/      # ingestion, metadata, vision, clustering, identity
    api/           # REST endpoints
    core/          # config
    db/            # session/connection

  scripts/         # ingestion + processing pipelines

storage/
  vault/           # canonical storage (hash-based)
  drop_zone/       # ingestion staging
  quarantine/      # rejected/unknown files
  review/          # face crops
  previews/        # reserved
  thumbnails/      # reserved
  exports/         # reserved

frontend/
  Next.js UI

docker/
  postgres + redis
```

---

## 4. Data Flow / Pipeline

```
Source → Drop Zone
  → Scan / Filter
  → Hash (SHA256)
  → Exact Deduplication
  → Vault (canonical storage)

  → Ingestion Context (source + relative path)
  → EXIF Extraction
  → Metadata Normalization

  → Capture Classification (type + time trust)
  → Event Clustering

  → Duplicate Lineage (near-duplicate grouping)

  → Face Detection
  → Face Cropping
  → Face Embedding
  → Face Clustering

  → Content Tagging (object / scene)

  → UI Review / Correction / Assignment
```

---

## 5. Core Concepts

- **Asset** — canonical image (one per SHA256)

- **Provenance** — source + file hierarchy

- **Ingestion Source / Run** — origin context of ingestion

- **Duplicate Lineage** — near-duplicate grouping (pHash-based)

- **Canonical Asset** — highest-quality representative

- **Face** — detected face with bbox

- **FaceCluster** — candidate identity group

- **Person** — user-defined identity

- **Event** — time/provenance-based grouping

- **Album** — user-curated grouping

- **Capture Type** — digital | scan | unknown

- **Capture Time Trust** — high | low | unknown

- **Display State** — non-destructive adjustments (rotation)

- **Vault** — single source of truth for files

---

## 6. Active Systems

### Ingestion & Provenance

- ingestion pipeline with batching

- exact deduplication (SHA256)

- ingestion source tracking (11.1.2)

- provenance with relative paths

### Metadata System

- EXIF extraction

- normalization

- capture classification

- time trust model

### Duplicate System

- exact duplicates collapsed at ingest

- near-duplicate lineage grouping (11.7)

### Face & Identity System

- detection (YuNet)

- embeddings (FaceNet)

- clustering (cosine similarity)

- full correction workflow

- person assignment

### Event System

- time-based clustering (trusted timestamps)

- provenance-based clustering (scans)

- event label editing

- event merge

### Album System

- user-created collections

- add/remove assets

- album ordering

### Content Tagging System

- object/scene classification (11.12)

- controlled vocabulary (early stage)

### Presentation Layer

- slideshow / presentation viewer (11.15)

- next/previous navigation

- keyboard controls

- fullscreen support

### Display Adjustment System

- rotation (non-destructive, DB-backed)

### UI System

- Review (faces/clusters)

- Photos (inspection + overlays)

- People

- Events

- Albums

- Places

- Unassigned Faces

---

## 7. Data Interaction Model

Two primary modes:

### Automated

- ingestion

- clustering

- tagging

- grouping

### Human-Guided

- face correction

- person assignment

- event editing

- album curation

System is designed to be **human-in-the-loop**, not fully automated.

---

## 8. API Layer

Core domains:

- `/api/photos`

- `/api/faces`

- `/api/clusters`

- `/api/people`

- `/api/events`

- `/api/albums`

Includes:

- cluster operations (merge, assign, ignore)

- face operations (move, unassign)

- event editing + merge

- album management

- rotation updates

---

## 9. Key Constraints

- Vault = immutable source of truth

- DB = authoritative state

- No destructive overwrite of originals

- Exact duplicates never stored twice

- Identity is human-controlled

- Local-first architecture

- Processing must be safe and repeatable

---

## 10. Architecture Rules

- strict separation of concerns

- service-layer business logic

- UI consumes APIs only

- deterministic pipelines preferred

- non-destructive design

---

## 11. Current Capabilities

- full ingestion + dedup pipeline

- provenance tracking (multi-source)

- metadata extraction + normalization

- event clustering + editing

- duplicate lineage grouping

- face detection + clustering + correction

- person identity management

- album system

- slideshow/presentation layer

- content tagging (early stage)

---

## 12. Known Limitations

- metadata inconsistency across sources (EXIF gaps)

- no canonical metadata selection yet

- near-duplicate review workflow missing

- no asset-level event reassignment

- content tagging accuracy limited

- no video playback or video intelligence

- limited provenance UI visibility

- UI consistency not yet optimized

---

## 13. Near-Term Direction (Milestone 12+)

- metadata canonicalization (EXIF reconciliation)

- provenance model refinement

- event refinement (remove/reassign assets)

- album-event integration

- near-duplicate review system

- improved tagging / semantic search

- video asset strategy

- UX/UI refinement layer

---

## 14. System Philosophy

- correctness over automation

- human control over identity

- non-destructive data handling

- scalable for large archives

- optimize later, structure first
