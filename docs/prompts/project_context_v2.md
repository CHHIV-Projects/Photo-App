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

- Cache / Queue: Redis (planned / partial integration)

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

  → Duplicate Detection (pHash / lineage)
  → Duplicate Suggestions (candidate pairs)
  → Duplicate Adjudication (confirm / reject / demote / canonical selection)

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

- **Place** — grouped geographic location (GPS cluster)  

- **User Place Label** — human-defined place name  

- **Visibility Status** — visible / demoted asset state  

- **Canonical Metadata** — selected metadata from multiple observations

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

### Duplicate Adjudication System

- duplicate suggestions (12.12)  
- canonical selection (12.13)  
- demotion (visibility control)  
- rejection persistence

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

### Location System

- canonical GPS selection (12.8)  
- place grouping (12.9)  
- reverse geocoding (12.11)  
- user-defined place labels (12.17)

### Photo Review System

- primary browsing workspace (12.14)  
- unified filtering and search (12.15)  
- person-aware filtering (12.16)  
- visibility-aware asset filtering

### Presentation Layer

- slideshow / presentation viewer (11.15)

- next/previous navigation

- keyboard controls

- fullscreen support

### Admin System

- system summary metrics (12.18)  
- operational visibility layer  
- foundation for future system controls

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

- Photo Review (primary surface)  

- Duplicate Groups  

- Duplicate Suggestions  

- Admin

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

- ingestion performance constrained by duplicate lineage processing (pending decoupling)  

- no cloud ingestion (iCloud / others)  

- HEIC viewing not fully supported  

- Live Photo (HEIC + MOV) handling undefined  

- location intelligence limited to geocoding (no landmark detection or inference)  

- face clustering suggestions limited in effectiveness  

- UI still workbench-oriented (Photo Review not fully unified workspace)  

- video handling not yet implemented

---

## 13. Near-Term Direction (Post 12.18)

- ingestion stabilization (batch staging, cloud ingestion)  

- duplicate processing decoupling (background processing)  

- HEIC native support and Live Photo handling  

- undated asset discovery and metadata completeness workflows  

- duplicate system refinement (threshold tuning, UX improvements)  

- location filtering and place system expansion  

- demotion workflows for non-duplicate unwanted assets

---

## 14. System Philosophy

- correctness over automation

- human control over identity

- non-destructive data handling

- scalable for large archives

- optimize later, structure first

## 15. System Layers

- **Storage Layer** — Vault (immutable file storage)  

- **Data Layer** — Database (assets, metadata, relationships)  

- **Processing Layer** — ingestion, clustering, canonicalization  

- **Intelligence Layer** — faces, duplicates, tagging (partially implemented)  

- **Interaction Layer** — UI (Photo Review, Workbench, Admin)

## 16. Processing Model

- ingestion pipeline is deterministic and repeatable  

- certain systems will transition to asynchronous/background processing:  
  
  - duplicate lineage  
  
  - suggestions  
  
  - future intelligence tasks  

- system is evolving toward hybrid:  
  
  - ingestion-time processing  
  
  - background enrichment

## 17. Storage and Deployment Direction

The system is designed to operate locally, with planned migration toward dedicated NAS-based storage for scalability and reliability.  

### Planned Architecture

- Primary storage will migrate to a Synology NAS (DS225+)  
- Vault directory will reside on NAS-backed storage  
- PostgreSQL and Redis expected to run via Docker on NAS  
- Local machine will act as:  
- development environment  
- UI/frontend host  
- optional processing node  

### Design Implications

- Vault must remain:  
- immutable  
- file-system independent  
- ingestion and processing must support:  
- network-mounted storage  
- larger datasets  
- long-running processes (duplicate lineage, enrichment) will transition to background execution aligned with NAS capabilities  

### Status

- migration not yet complete  
- system currently optimized for local-first development
