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

The system is no longer a prototype — it is a **functionally complete archival platform**.

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

### Phase 4 — Intelligence & Refinement (Next Phase)

Focus:

- metadata canonicalization (critical next step)

- provenance model refinement

- event refinement (remove/reassign assets)

- near-duplicate review workflows

- improved content tagging and semantic understanding

- video asset strategy

---

### Phase 5 — Platform Expansion (Future)

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

---

## 5. Parking Lot Integration Strategy

Features move from parking lot to roadmap when they:

- solve real workflow friction

- improve data correctness

- unlock multiple downstream capabilities

---

### Immediate Promotion Candidates

- metadata canonicalization

- provenance visibility

- near-duplicate review

---

### Mid-Term Candidates

- event refinement

- album-event integration

- tagging improvements

---

### Long-Term Candidates

- semantic search

- collaborative users

- mobile expansion

- cloud-assisted ML

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
