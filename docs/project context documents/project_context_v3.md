# PROJECT_CONTEXT.md

## 1. Overview

Local-first photo organization system focused on safe ingestion, deduplication, metadata canonicalization, and human-in-the-loop curation across faces, events, places, and collections.

The platform now includes Admin-controlled operational workflows and cloud acquisition support through icloudpd, while keeping Source Intake as the ingestion authority.

---

## 2. Tech Stack

- Backend: Python 3.11, FastAPI
- Frontend: Next.js (React)
- Database: PostgreSQL
- Cache / Queue: Redis (planned and partial use for background-job-oriented workflows)
- Container environment: Docker Compose (PostgreSQL + Redis)

### Media and Processing Tooling

- ExifTool / pyexiftool for metadata extraction
- imagehash / pHash for near-duplicate analysis
- OpenCV YuNet for face detection
- DeepFace (FaceNet) for face embeddings
- icloudpd as an external acquisition adapter (download to staging only)

### Operating Environment

- Windows-first development currently
- NAS-oriented deployment path is planned

---

## 3. Core Architecture

```text
backend/
  app/
    models/        # assets, provenance, sources, faces, people, events, albums
    services/      # ingestion, metadata, duplicates, vision, admin workflows
    api/           # REST endpoints
    core/          # configuration
    db/            # database session/connection
  scripts/         # operational and batch runners

storage/
  vault/                 # immutable canonical storage
  drop_zone/             # internal ingestion staging
  exports/icloud/        # cloud acquisition staging (per source_label)
  quarantine/            # rejected/failed staging material
  logs/                  # operational reports and run artifacts
  review/                # face crops and review assets
  previews/              # generated display previews
  thumbnails/            # reserved / future use

frontend/
  src/                   # Next.js application

docker/
  docker-compose.yml     # postgres + redis services
```

`storage/exports/icloud/<source_label>/` is a temporary local cloud staging area and is not the Vault.

---

## 4. Data Flow / Pipeline

### Local Source Path

```text
Local source
  -> Source Registry
  -> Source Intake
  -> Drop Zone
  -> Vault + DB + Provenance
  -> metadata / previews / duplicates / faces / places / review workflows
```

### iCloud Source Path

```text
iCloud source
  -> icloudpd acquisition
  -> storage/exports/icloud/<source_label>/
  -> Source Intake
  -> Drop Zone
  -> Vault + DB + Provenance
  -> post-intake background/admin jobs
  -> optional verified iCloud staging cleanup
```

Architecture rule: icloudpd never writes directly to Drop Zone, Vault, DB, or provenance.

Successful files are removed from Drop Zone after ingestion; failed/rejected files are retained or routed through failure handling rather than silently discarded.

---

## 5. Core Concepts

- Asset: Canonical media record keyed by SHA-256.
- Provenance: Source lineage (source identity plus source-relative path).
- Ingestion Source: Registered source identity used by Source Intake.
- Source Registry: Admin-managed source catalog (`source_label`, `source_type`, `source_root_path`, optional account linkage fields).
- Source Intake: Authoritative ingestion workflow from registered sources into the canonical pipeline.
- Cloud Source: Registered source identity representing a cloud staging root.
- iCloud Acquisition: Download-only acquisition step using icloudpd into local exports staging.
- Account Username: Non-secret iCloud account identifier associated with a source (not password, token, or session secret).
- Vault: Immutable canonical file storage.
- Drop Zone: Controlled internal staging area used by ingestion.
- Exports iCloud Staging Folder: Local temporary acquisition area under `storage/exports/icloud/<source_label>/`.
- Display Preview: Generated display-friendly media representation (e.g., HEIC/TIFF compatibility).
- Live Photo Pair: Still-photo asset paired with its motion companion.
- Live Photo Motion Companion: Motion-side asset associated with a Live Photo still.
- Video Metadata Trust: Capture-time trust model for video-native metadata.
- Place: Canonicalized location grouping for assets.
- Duplicate Lineage: Near-duplicate grouping and adjudication model.
- Canonical Metadata: Consolidated metadata selected across multiple observations/provenance inputs.
- iCloud Staging Cleanup: Operator-triggered local staging deletion after positive provenance + asset + vault verification.

---

## 6. Active Systems

### Source Registry and Source Intake

- Registered source identity with normalized path handling.
- Supports source label/type/root registration and management.
- Supports `account_username` for cloud/iCloud source records as a non-secret operator safety field.
- Explicit run/status controls with admin visibility and run reporting.
- Source Intake remains the ingestion authority for both local and cloud-staged inputs.

### iCloud Acquisition System

- icloudpd is the preferred acquisition adapter.
- Raw PyiCloud scripts remain experimental/diagnostic; icloudpd is the preferred acquisition path.
- Admin supports run/status/stop controls.
- Download target is `storage/exports/icloud/<source_label>/`.
- Recent-window acquisition behavior (default recent count 25, max 500).
- Completeness guarantees across full history are not yet implemented.
- `account_username` prefill/override safeguards are included.
- Application does not store Apple ID password, 2FA code, token, or session cookies.

### iCloud Staging Cleanup

- Preview-first (dry-run) workflow before delete mode.
- Deletes only local iCloud staging files after verification.
- Requires provenance + asset + vault-file evidence.
- Writes structured cleanup reports to logs.
- Does not delete iCloud cloud-library data, Vault files, DB records, provenance history, or source registry records.

### Display Preview System

- Admin-triggerable preview generation.
- HEIC/HEIF preview support is active.
- TIFF and content-type mismatch preview handling is supported.

### Live Photo System

- Pairing workflow implemented.
- Supports standard basename pairing and icloudpd `_HEVC.MOV` pairing patterns.
- UI indicators for Live Photo and motion companion states are present.
- Playback and advanced motion-companion hide/filter UX remain deferred.

### Video Metadata System

- Video-native metadata extraction for MOV/MP4/M4V.
- QuickTime/container timestamp handling included.
- Capture-time trust model (`high`, `low`, `unknown`) applied to video assets.
- Missing image EXIF in MOV is no longer treated as an automatic low-trust case.
- Video playback and thumbnail-specific UX remain deferred.

### Admin System

Admin controls and operational visibility include:

- Source Registry
- Source Intake
- iCloud Acquisition
- iCloud Staging Cleanup
- Display Preview Generation
- Live Photo Pairing
- Duplicate Processing
- Face Processing
- Place Geocoding
- Stale-run recovery for selected background jobs

### Operational Reports and Audit Artifacts

- Operational reports are written under `storage/logs/` for Source Intake, ingestion manifests, iCloud acquisition, iCloud staging cleanup, duplicate processing, display preview generation, Live Photo pairing, face processing, and place geocoding.
- Reports are used for validation, troubleshooting, and operator auditability.
- Reports are not the system of record; DB state and provenance remain authoritative.

### Intelligence and Curation Systems

- Exact SHA-256 deduplication in ingestion path
- Near-duplicate lineage/suggestions/adjudication
- Face detection, embedding, clustering, correction, and assignment
- Event clustering/edit/merge workflows
- Place canonicalization and reverse-geocoding enrichment
- Photo Review filtering across person/place/time/visibility metadata
- Duplicate processing can run as an Admin-controlled background job rather than being tightly coupled to every ingestion run.

---

## 7. API Layer

Core domains include photo, face/cluster, people, events, albums, places, and admin operational APIs.

Admin API group includes operational domains such as:

- `/api/admin/source-intake/...`
- `/api/admin/icloud-acquisition/...`
- `/api/admin/icloud-staging-cleanup/...`
- `/api/admin/duplicate-processing/...`
- `/api/admin/face-processing/...`
- `/api/admin/place-geocoding/...`
- `/api/admin/live-photo-pairing/...`
- display-preview admin control endpoints

---

## 8. Key Constraints and Architecture Rules

- Source Intake is the only ingestion authority.
- Cloud acquisition may write only to exports staging.
- icloudpd must not write directly to Drop Zone, Vault, DB, or provenance.
- Vault is immutable canonical storage.
- DB plus provenance provide authoritative origin/lineage state.
- iCloud staging cleanup is allowed only after positive provenance + vault verification.
- The app does not store Apple ID passwords, 2FA codes, session cookies, or auth tokens.
- One stable iCloud source per iCloud account/library is the production operational rule.
- Processing is non-destructive, deterministic where possible, and repeatable.
- Identity and curation remain human-controlled.
- Local-first architecture remains the baseline.

---

## 9. Current Capabilities

- Local folder ingestion with Source Registry and Source Intake controls
- iCloud acquisition through icloudpd via Admin UI
- Verified iCloud staging cleanup workflow (dry run + execute)
- Exact dedupe plus near-duplicate lineage/adjudication workflows
- Metadata observations and canonicalization
- HEIC/HEIF and TIFF-friendly display preview generation
- Live Photo pairing (including icloudpd naming support)
- MOV/MP4/M4V metadata trust handling
- Face processing and identity correction workflows
- Place geocoding and location grouping
- Duplicate/face/place background job controls via Admin
- Photo Review search/filter across timeline/location/person facets

---

## 10. Known Limitations

- iCloud acquisition currently uses fixed recent windows; full checkpoint/until-found completeness is not implemented.
- Fixed-window acquisition can re-download files if local staging was cleaned and upstream checkpointing is absent.
- After iCloud staging cleanup, fixed-window acquisition may re-download recently cleaned files until checkpoint/until-found logic is implemented.
- Multiple test iCloud sources may exist in registry; archive/inactive-source lifecycle is not fully implemented.
- Source Registry can still contain confusing or duplicate test labels until archive/inactive-source support is added.
- Cloud-native iCloud asset IDs are not yet captured as first-class provenance keys.
- The application does not manage iCloud credentials/sessions directly.
- Live Photo playback is not yet implemented.
- Live Photo motion-companion hide/filter UX is not yet implemented.
- Video playback and video thumbnail UX are deferred.
- Unified Source Profile and one-click intake workflow are not yet implemented.
- NAS production deployment is planned but not yet complete.

---

## 11. Near-Term Direction

- 12.45 documentation and architecture-context consolidation
- Source Registry cleanup and inactive-source lifecycle model
- iCloud acquisition completeness strategy (checkpoint/until-found)
- Unified Source Profile and Intake workflow design
- Unified run history across acquisition and intake workflows
- Production-scale iCloud intake validation
- NAS deployment planning and environment hardening
- Continued Photo Review and curation UX refinement

---

## 12. Storage and Deployment Direction

Current operation is local-first with planned migration toward NAS-backed deployment.

- Vault migration to NAS-backed storage remains planned.
- PostgreSQL and Redis are expected to run in Docker on target deployment hosts.
- icloudpd helper/runtime requirements must be accounted for in NAS/server deployment design.
- iCloud authentication/session handling remains external/manual operationally.
- Scheduled unattended iCloud acquisition is deferred.

---

## 13. Deferred Themes (High-Level)

- iCloud checkpoint/until-found completeness strategy
- Cloud-native provenance identifiers for iCloud assets
- Multi-account iCloud session handling model
- Credential/session manager architecture (if ever introduced)
- Source archive/inactive lifecycle workflows
- Unified Source Profile and one-click operator workflow
- Live Photo playback and richer motion-companion UX
- Video playback and thumbnail workflows
- NAS-scheduled acquisition and long-running operational orchestration
