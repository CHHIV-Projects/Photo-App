# ARCHITECTURE_ROADMAP.md

## 1. Current State Summary

The system is a **local-first photo intelligence platform** with a complete operational foundation.

It currently supports:

- ingestion with exact deduplication into canonical vault storage

- provenance tracking with source context

- metadata extraction and normalization

- capture classification (type + time trust)

- event grouping (time-based and provenance-based)

- face detection, embedding, clustering, and correction workflows

- person identity assignment

- duplicate lineage (near-duplicate grouping)

- album/collection system

- presentation layer (slideshow, navigation, fullscreen)

- content tagging (early-stage object/scene classification)

- multi-view UI (Photos, Review, People, Events, Albums, Places, Unassigned)

- duplicate adjudication system (suggestions, canonical selection, demotion)  

- location system (place grouping, geocoding, user-defined labels)  

- Photo Review workspace (primary browsing surface)  

- admin system (system visibility and operational layer)

The system is no longer a prototype — it is a **functionally complete archival platform**.

## System Evolution Note

The system has evolved from a primarily pipeline-centric architecture  
to a layered architecture where user workflow surfaces (review, correction, curation)  
are now the primary interaction model, while system pipelines continue to provide  
the underlying structure and automation.

This shift is centered around the Photo Review workspace and duplicate adjudication system.

---

## 2. Development Phases

### Phase 1 — Data Integrity (Complete)

Establish trustworthy ingestion, metadata, and identity systems.

Delivered:

- ingestion + deduplication

- metadata extraction + normalization

- face system

- event system foundation

---

### Phase 2 — Identity & Pipeline Stability (Complete)

Preserve user work while enabling ongoing ingestion and processing.

Delivered:

- incremental face processing

- duplicate lineage model

- ingestion context / provenance tracking

- safe pipeline orchestration

---

### Phase 3 — Organization & Presentation (Largely Complete)

Enable meaningful browsing, grouping, and consumption of the archive.

Delivered:

- albums / collections

- timeline navigation

- event browsing and editing

- presentation/slideshow layer

- multi-view UI

Remaining minor gaps:

- event reassignment

- album-event integration

- UI consistency refinement

---



### Phase 4 — Data Quality & User Workflows (Complete)

Focus:  

- metadata canonicalization  
- duplicate adjudication and control  
- event stabilization (non-destructive model)  
- location system foundation (GPS, places, geocoding)  
- unified search and Photo Review workspace  
- user-driven workflows for correction and curation  

Delivered:  

- canonical metadata system (12.1)  
- duplicate review, suggestions, adjudication (12.3–12.13)  
- event stabilization (12.7)  
- place system + geocoding (12.8–12.11)  
- Photo Review + unified search (12.14–12.15)  
- person integration (12.16)  
- place aliasing (12.17)  
- admin system (12.18)

---

###### Phase 5 — System Stabilization & Real-World Scale (Current)

Focus:  

- ingestion stabilization (batch staging)  
- cloud ingestion (iCloud priority)  
- duplicate processing decoupling (background processing)  
- format handling (HEIC, Live Photos)  
- performance and scalability improvements  
- UX refinement toward unified workflows  

This phase marks transition from:  
prototype completeness → real-world operational robustness

### Phase 6 — Platform Expansion (Future)

Focus:

- external sharing

- access control

- mobile/lightweight clients

- optional cloud-assisted processing

---

## 3. Milestone Reality (11.x Summary)

Milestone 11 delivered the **complete functional backbone**:

- ingestion and provenance (11.1.x)

- duplicate lineage (11.7)

- incremental processing (11.8)

- timeline (11.9)

- albums (11.10)

- person suggestion (11.11)

- content tagging (11.12)

- display adjustments (11.13)

- event administration (11.14)

- presentation layer (11.15)

Milestone 11 is considered **functionally complete**.

---

## 4. Architectural Priorities

### A. Provenance as a First-Class System

Must support:

- multiple source origins

- relative file hierarchy

- auditability of ingestion

Future refinement:

- separation of provenance vs ingestion observation

---

### B. Identity Preservation

Manual identity work must remain safe.

System must:

- avoid destructive clustering

- support incremental updates

- maintain human authority over identity

---

### C. Canonical Asset Model

System must maintain:

- one canonical asset

- exact duplicate elimination

- near-duplicate grouping

- potential future canonical promotion/demotion

---

### D. Time as a Navigation Layer

Time is:

- metadata

- clustering signal

- user-facing navigation system

Must incorporate:

- trust levels

- missing/low-confidence handling

---

### E. Local-First Scalability

Design assumes:

- 15K–20K+ assets

- desktop + NAS architecture

- optional background processing

- cloud only when justified

---

### F. Separation of User vs System Layers

System must distinguish:

- user workflows (albums, viewing, correction)

- system workflows (ingestion, clustering, tagging)

### G. Processing Decoupling

The system must evolve from ingestion-time heavy processing to:  

- background processing for expensive tasks  
- non-blocking ingestion pipeline  
- controllable execution via admin layer  

Key candidates:  

- duplicate lineage  
- suggestion generation  
- future intelligence tasks

### H. Format-Aware Asset Handling

The system must support multiple media formats:  

- HEIC (primary modern photo format)  
- Live Photos (HEIC + MOV linkage)  
- video assets  

Design must:  

- preserve original formats  
- avoid lossy conversion  
- support unified viewing experience

---

## 5. Parking Lot Integration Strategy

Features move from parking lot to roadmap when they:

- solve real workflow friction

- improve data correctness

- unlock multiple downstream capabilities

---

###### Immediate Promotion Candidates

- ingestion stabilization (batch staging)  
- background duplicate processing  
- cloud ingestion (iCloud)  
- HEIC support (minimum viable)  

### Mid-Term Candidates

- Live Photo handling (design + implementation)  
- undated asset discovery  
- duplicate UX improvements  
- location filtering  

### Long-Term Candidates

- multi-signal duplicate scoring  
- location intelligence (landmarks, inference)  
- semantic search and tagging  
- collections / album-event integration

---

## 6. Constraints for Future Work

- maintain local-first architecture

- avoid cloud dependency by default

- preserve non-destructive workflows

- keep backend logic centralized

- prioritize explainable systems over opaque ML

- avoid silent automation

- maintain canonical asset model

- support both manual and automated workflows

---

## 7. Long-Term Vision

The system evolves into a **local-first photo intelligence platform** capable of:

- organizing archives by:
  
  - who (people)
  
  - what (content)
  
  - when (timeline)
  
  - where (location)
  
  - origin (provenance)

- preserving archival truth while enabling high-quality canonical assets

- combining:
  
  - automated grouping
  
  - human correction
  
  - explainable intelligence

- supporting:
  
  - rich browsing
  
  - search and filtering
  
  - albums and collections
  
  - timeline navigation

- scaling to large personal archives while maintaining trust and control

- remaining private-first, with optional expansion to sharing and external access

This is not just a photo viewer — it is a **curated, intelligent archival system**.

### 8. NAS/Synology

- planned migration to NAS-backed storage (Synology) for:  
- vault storage  
- database and cache hosting  
- background processing workloads
