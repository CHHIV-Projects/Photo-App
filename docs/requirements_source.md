**Photo Organizer Project Plan (Revised Architecture, Multi User)**

**Requirements**

**Section 1: Drop Zone (Ingestion Pipeline) Requirements**

**1.1 Source Selection & Volume Identification**

-   **Execution UI:** The system will provide an interface to trigger specific fetching routines for various origins: Local Drives, iCloud, OneDrive, and Google Photos (via Google Takeout).
-   **Volume Naming:** Prior to executing any fetch routine, the system will prompt the user to input a "Volume Name" (e.g., Chucks_Old_Dell or Seagate_2TB).
-   **Historical Dropdown:** The input prompt will feature a dropdown menu populated with previously used Volume Names to ensure consistent naming conventions.
-   **Metadata Tagging:** The designated Volume Name will be prepended to all original directory paths recorded in the Workspace Database.

**1.2 The Pre-Flight Check (Local Sources Only)**

-   **Action:** For local hardware scans, the system will evaluate files at the source before initiating transfer to save time and drive wear.
-   **Execution:** Calculates the Perceptual Hashing (phash) hash at the source and cross-references the Database.
    -   *Known Hash + Known Path:* Skipped entirely.
    -   *Known Hash + New Path:* Skipped transfer. New path appended to existing database record.
    -   *Unknown Hash:* Approved for Drop Zone transfer.

**1.3 Archive Extraction Protocol**

-   **Action:** Handles compressed archives (Google Takeout).
-   **Execution:** Auto-unpacks .zip, .rar, or .tgz files placed in the Drop Zone. Extracted contents route to the Bouncer. Archive is deleted upon success.

**1.4 The Bouncer (Pre-Drop Zone Filter)**

-   **Action:** A strict validation gate preventing digital lint and unsupported formats.
-   **Dynamic Allowlist:** Queries the Database for the active Master Allowlist (Images: .jpg, .heic, .cr2, etc. Video: .mp4, .mov. Sidecars: .xmp).
-   **Thumbnail Killer:** Files under 50KB are rejected unless explicitly approved (like sidecars).

**1.5 Drop Zone Processing & Hashing**

-   **Action:** Files passing the Bouncer land in the Drop Zone for cryptographic fingerprinting via Perceptual Hashing (phash) hashing.

**1.6 Vault Promotion & Deduplication Logic**

-   **Scenario A (New File):** Approved to move to Vault. New database record created.
-   **Scenario B (True Duplicate):** Deleted from Drop Zone (FIFO). No database update.
-   **Scenario C (Contextual Duplicate):** Deleted from Drop Zone. New path added to existing hash record in the database.

**1.7 Vault Handoff & Hash Verification**

-   **Action:** Prevents bit-rot during transfer. The system calculates the hash of the newly written Vault file and compares it to the Drop Zone hash. Matches are finalized; mismatches are deleted and retried.

**1.8 The Quarantine Protocol**

-   **Action:** Unreadable or locked files are moved to a Drop_Zone/Quarantine directory. An error log is generated for manual review.

**1.9 Zero-State Enforcement**

-   **Action:** Validates pipeline hygiene. The Drop Zone must be 0 bytes after a routine. Lingering files trigger an alert.

**1.10 Post-Routine Summary Report**

-   **Action:** Generates an audit trail (Total Scanned, Skipped, True Duplicates, Promoted to Vault, Quarantine items, etc.).

**1.11 Continuous Mobile Feeder (Daily Ingestion)**

-   **Action:** Supports background mobile app ingestion (e.g., Synology Photos client). Pushes new network captures directly to the Drop_Zone.

**1.12 Autonomous Cloud API Fetchers**

-   **Action:** Decouples cloud ingestion from local PC. NAS scripts (Fetchers) connect to Google Drive/iCloud via OAuth2 using locally stored tokens.json.
-   **Routing:** Runs on NAS cron jobs, dropping files into the Drop Zone blind to the Vault logic. Prompts users via push notification if tokens expire.

**1.13 Dynamic Configuration Management**

-   **Action:** System rules must not be hardcoded into the Python execution scripts.
-   **Execution:** Processing variables—including the active File Extension Allowlist, the Bouncer's minimum file size (e.g., 50KB), AI confidence thresholds, and the Deduplicator's Hamming Distance tolerance, as well as variable in config.py—must be stored in a centralized Database configuration table. These variables will be adjustable via the Administrator UI to allow real-time tuning without editing code.

**1.14 Source Preservation (Read-Only Fetching)**

-   **Action:** To prevent accidental data loss during large-scale ingestion, the system must treat all original source locations (OneDrive, Google Drive, Local Laptops, External HDDs) as strictly Read-Only.
-   **Execution:** All Fetcher scripts must use "Copy" commands to duplicate files into the Drop Zone. The system is strictly prohibited from issuing "Move" or "Delete" commands to the origin source drives.

**Section 2: The Vault (Physical Storage & Preservation) Requirements**

**2.1 Storage Architecture & File Routing (Hex-Prefixing)**

-   **Execution:** Files are permanently renamed to their Perceptual Hashing (phash) hash and routed into 256 subfolders (00 through ff) based on the first two characters of the hash.

**2.2 The Immutability Mandate (WORM Principle)**

-   **Action:** Write-Once, Read-Many. Once verified in the Vault, files are physically locked. All tagging/edits happen in the Database.

**2.3 Bit-Rot Protection & Scrubbing**

-   **Execution:** Synology NAS formatted in Btrfs. Automated monthly data scrubs repair degraded files using RAID parity.

**2.4 Disaster Recovery & Backup Protocol**

-   **Execution:** Automated, immutable Btrfs snapshots. Incremental, block-level sync to an offsite cloud bucket (3-2-1 backup).

**2.5 The Break-Glass Protocol**

-   **Action:** The Administrator retains full Read/Write/Delete authority directly at the NAS OS level for disaster extraction.

**Section 3: Source Reclamation (Storage Maintenance) Requirements**

**3.1 Manual Execution Mandate**

-   **Action:** Reclamation routines cannot be automated. Must be manually launched and confirmed via the UI against a specific target volume.

**3.2 The Cloud-Sync Firewall**

-   **Execution:** System permanently blocks execution against active cloud-sync folders (OneDrive, iCloud Desktop). Generates a "Redundancy Report" instead.

**3.3 The "Dumb Storage" Vacuum Protocol**

-   **Execution:** Scans target offline drives. A file is only flagged for deletion if its exact hash exists and is verified in the WORM Vault.

**3.4 The Soft-Delete Safety Net**

-   **Execution:** Files are not Shift+Deleted. They are moved to a \_Vault_Reclaimed_Space folder on the root of the source drive, with an automated 30-day expiration purge.

**3.5 The Database Auditor (Ghost Record Reconciliation)**

-   **Action:** Prevents database desynchronization caused by users manually deleting or moving files directly within the NAS operating system.
-   **Execution:** A scheduled maintenance routine that queries the database for all recorded file paths, verifies their physical existence in the WORM Vault, and automatically purges all orphaned metadata (tags, faces, records) for any files that have been manually removed.

**3.6 The Vault Sweeper (Retroactive Deduplication)**

-   **Action:** An on-demand tool to scan the established WORM Vault for internal visual duplicates (e.g., heavily compressed clones that bypassed initial ingestion due to changing Hamming distance tolerances).
-   **Execution:** The Sweeper presents matched clusters in a "Resolution UI." The user can choose to **Archive** (move the lower-quality file to the \_Vault_Reclaimed_Space for a 30-day cooling-off period).

**Section 4: The Workspace (Processing & Metadata) Requirements**

**4.1 Distributed Master-Worker Architecture (New)**

-   **Action:** Ensures 24/7 NAS uptime while leveraging desktop PC power for heavy AI tasks when available.
-   **Execution:** The core PostgreSQL database lives on the NAS. A Redis Task Queue manages asynchronous jobs.
    -   *Primary Worker (PC):* A Celery worker on the Desktop PC consumes AI tasks at high speed when awake.
    -   *Fallback Worker (NAS):* A lightweight NAS worker slowly processes the queue if the PC is offline.

**4.2 Baseline Metadata Extraction**

-   **Execution:** Extracts Date/Time, GPS, Make/Model, Lens. Supports proprietary RAW (.CR2, .NEF) and Video Atoms via FFmpeg.
-   **Scan Drop Zone:** A dedicated folder for physical scans that bypasses EXIF date extraction, relying on AI Era Estimation instead.
-   **The Triage Gatekeeper (EXIF Edge Cases):**
-   **Scanner Hardware Check:** Identifies known physical scanner models (e.g., Epson, HP, CanoScan) in the Make/Model EXIF tags to automatically flag the file as a physical scan and bypass the digital timestamp.
-   **Scanning Software Check (The Photomyne Rule):** Inspects the Software tag for known digitization apps (e.g., Photomyne, PhotoScan). If found, overrides the modern smartphone capture date and routes the historical file to the AI Era Estimator.
-   **Dead Battery Reset Check:** Detects factory-default timestamps (e.g., 2000-01-01 00:00:00) caused by dead internal camera batteries, flagging the photo for AI Era Estimation instead of incorrectly filing it in the year 2000.

**4.2.1 Cloud API Fallback Protocol (Hybrid Edge-to-Cloud)**

**Objective:** To establish a secondary, highly accurate semantic tagging tier for media assets that the local AI model cannot confidently classify, ensuring maximum searchability while managing cloud computing costs.

**Workflow & Logic:**

-   **The Confidence Tripwire:** During the standard clip_classifier pipeline, if an image's calculated mathematical match for all predefined SEMANTIC_TAGS falls below the designated TAG_CONFIDENCE_THRESHOLD (e.g., \< 0.40), the local engine will abort tagging.
-   **The Pending Queue:** Instead of being routed to the database with zero semantic metadata, the asset is temporarily moved to an isolated API_Pending_Queue directory.
-   **Cloud API Batching:** On a scheduled basis (or via manual user trigger), the system will securely package the queued images and transmit them to a commercial Vision API endpoint (Supported targets: Microsoft Azure AI Vision, OpenAI Vision API, Google Cloud Vision, or Amazon Rekognition).
-   **Advanced Contextual Tagging:** The designated Cloud API will perform a deep contextual analysis of the image. The API will be constrained by prompt or configuration to map its findings to the Vault's established master taxonomy.
-   **Database Ingestion & Archival:** The rich metadata returned from the Cloud API is mapped to the asset's unique ID, written to the SQLite database, and the physical file is finally cleared from the pending queue and moved into the immutable NAS Vault.
-   

**4.3 The AI Recognition Pipelines**

-   Facial Recognition (Local processing via **DeepFace**: Age-Invariant, Relationship mapping)
-   ~~Facial Recognition (Age-Invariant, Relationship mapping)~~.
-   Contextual Classification (Scenes, Objects).
-   Place & Landmark Recognition (Visual + GPS translation).
-   Era & Content Recognition (For analog scans).
-   Visual Duplication (Perceptual Hashing).

**4.4 The Active Learning UI (Human-in-the-Loop)**

-   Execution: Dashboard for Editors/Admins to correct unconfident or missing AI tags. User corrections instantly update the relational SQLite database records to ensure search accuracy, without initiating computationally heavy fine-tuning of the underlying local AI models.
-   **~~Execution:~~** ~~Dashboard for Editors/Admins to correct unconfident AI tags, feeding data back to refine local models.~~
-   **Bounding Box Spatial Storage:** The database must store the exact X and Y pixel coordinates of detected faces, allowing the frontend UI to draw interactive boxes for manual user verification and deletion.
-   **Automated Reference Generation:** When a user manually tags a new person in the UI, a background worker must automatically crop the face, generate a new Known_Faces directory for that person, and clear the DeepFace .pkl cache to force the model to learn the new face.

**4.5 Event Clustering & Curation**

-   **Execution:** Spatial-temporal clustering (DBSCAN) groups photos into "Events" for rapid triage (Promote vs. Archive).

**4.6 The Semantic Query Engine**

-   **Execution:** Vector embeddings (CLIP) power natural-language searches (e.g., "Audrey and Patricia in a garden").

**4.7 Global Curation (Favorites & Ratings)**

-   **Execution:** Boolean "Favorite" toggle and 1-5 star rating system for instant priority indexing.

**4.8 Relational Taxonomy (Logical Hierarchy)**

-   **Execution:** Nested categorization (e.g., Utah \> Moab) relationship groupings (e.g., mapping individual profiles for Chuck, Patricia, Audrey, and Tori into a searchable 'My Family' group). Tagging a child automatically associates the parent.

**4.9 Database Preservation & Redundancy**

-   **Execution:** The core PostgreSQL Database undergoes automated daily backups, compressed and synced to offsite cloud storage.

**4.10 Proxy & Web-Resolution Generation**

-   **Execution:** System generates 1080p JPEGs and 720p H.264 video proxies, stored outside the Vault, for instant web streaming.

**4.11 Asynchronous Task Queue (Celery/Redis)**

-   **Execution:** Heavy tasks (AI analysis, Proxy generation, EXIF parsing) are pushed to a Redis queue so Vault ingestion never bottlenecks. Processed by the Master-Worker setup (Sec 4.1).

**4.12 Standardized Metadata Write-Back**

-   **Execution:** "Export Metadata" routine generates standardized .xmp sidecar files from the database to prevent vendor lock-in.

**4.13 The Audit Ledger & State Rollback**

-   **Execution:** Tracks all metadata changes (User, Timestamp, Target, Before/After state). UI allows Admins to rollback targeted bulk actions. Includes push notifications for hardware/API failures.

**4.14 Robust Network Concurrency**

-   **Execution:** Upgrading from SQLite to PostgreSQL ensures simultaneous, multi-thread read/write operations for up to 10 concurrent users editing and viewing across the network without database lockups.

**4.15 Source Provenance Tracking (Source Volumes Table)**

-   **Action:** The system must permanently remember the origin of every file to assist with event clustering and user search context.
-   **Execution:** The database schema will include a Source_Volumes table. Upon ingestion, the file's original user-defined origin (e.g., "Chuck's Laptop", "External Drive 1") and its exact original folder hierarchy will be logged and relationally tied to the permanent Vault photo record.

**Section 5: The Storefront (Presentation Layer) Requirements**

**5.1 Responsive Web Architecture (Split Stack)**

-   **Execution:** A decoupled web frontend (React/Vue.js) communicating with the FastAPI backend. Ensures pixel-perfect scaling across desktop, tablet, and mobile browsers.

**5.2 Multi-Tenant Library Architecture (New)**

-   **Private Libraries:** Each registered user is provisioned a private, isolated photo library space upon account creation.
-   **Shared Libraries:** Centralized libraries where multiple authorized users can collaborate, view, and organize the same set of media.

**5.3 The Query Engine Interface**

-   **Execution:** Unified search supporting Semantic Search, Boolean filtering, and visual Facial Querying.

**5.4 The Curation Workbench (Triage UI)**

-   **Execution:** Rapid input interface (Mobile swipe, Desktop hotkeys) to filter clustered events.

**5.5 Virtual Albums & "Favorites" View**

-   **Execution:** Logical grouping without file duplication.

**5.6 The "Checkout Counter" (Export Engine)**

-   **Execution:** Retrieves pristine Vault originals, injects Database metadata into EXIF headers, and packages a zip/directory for the user.

**5.7 Source-Origin Browsing**

-   **Execution:** Dedicated "Source Volumes" tab to view assets exactly as they were grouped on their original ingestion drives.

**5.8 Authentication & Role-Based Access Control (RBAC) (Revised)**

-   **Execution:** Mandatory secure login screen. Supports up to \~10 simultaneous family accounts across three tiers:
    -   **Administrator:** Absolute super-user. Can provision accounts, view backend server directories, manage storage quotas, alter database states, and execute rollbacks.
    -   **Editor:** Read/Write access to designated shared libraries on desktop and mobile. Can upload new media, delete media (soft-delete), edit metadata, and explicitly correct AI tagging.
    -   **Viewer:** Read-Only access to specific libraries. Can search, view, and play media on desktop/mobile, but cannot alter files, tags, or folder structures.

**Section 6: Local Development & File Architecture**

Plaintext

C:\\Photo_Project_Workspace\\

├── 01_Ingestion_Scripts\\

│ ├── icloud_fetcher.py \# Handles Apple API

│ ├── gdrive_fetcher.py \# Handles Google API

│ ├── onedrive_fetcher.py \# Handles Microsoft API

│ └── local_scan_ingest.py \# Handles physical scans

├── 02_NAS_Server_Engine\\

│ ├── api_gateway.py \# FastAPI backend (serves the web app)

│ ├── database_models.py \# PostgreSQL schema logic

│ ├── queue_manager.py \# Routes tasks to Redis

│ └── nas_fallback_worker.py \# Slow background AI processing (Celery)

├── 03_PC_Supercharger_Worker\\

│ └── pc_heavy_worker.py \# High-speed AI processor (DeepFace/CLIP) for Desktop

├── 04_Storefront_Web_UI\\

│ ├── package.json \# Frontend dependencies (React/Vue)

│ ├── src\\ \# UI components, dashboards, routing

│ └── public\\ \# Static assets

├── 05_Mock_NAS_Volumes\\

│ ├── Drop_Zone\\

│ ├── Scan_Drop_Zone\\

│ └── WORM_Vault\\

├── docker-compose.yml \# Blueprint to launch Postgres, Redis, and FastAPI on NAS

├── config.json

└── requirements.txt

**Phase A: The Technology Stack**

| **Category** | **Function**            | **Tool / API**          | **Environment** | **Notes**                                                                       |
|--------------|-------------------------|-------------------------|-----------------|---------------------------------------------------------------------------------|
| Backend Core | File Hashing & Moving   | hashlib & shutil        | NAS (Docker)    | Built-in Python libraries. Bulletproof and native.                              |
| Backend Core | Visual Duplication      | ImageHash               | PC Worker / NAS | Generates mathematical fingerprints to catch visual clones.                     |
| Backend Core | EXIF, RAW, & Video      | PyExifTool / FFmpeg     | PC Worker / NAS | Parses heavy camera RAWs and proprietary Apple video atoms.                     |
| Database     | Core Engine             | **PostgreSQL**          | NAS (Docker)    | Replaces SQLite. Safely handles 10 concurrent network users editing/viewing.    |
| Database     | ORM                     | SQLAlchemy              | NAS (Docker)    | Translates database rows into pure Python objects for the taxonomy.             |
| Architecture | Task Queue              | **Celery + Redis**      | PC & NAS        | Distributes heavy tasks. Redis holds the tickets on NAS; Celery processes them. |
| AI Layer     | Facial Recognition      | DeepFace                | PC Worker / NAS | Handles age-invariance via state-of-the-art local models.                       |
| AI Layer     | Semantic Search         | CLIP                    | PC Worker / NAS | Translates images into searchable concepts ("Dogs in the snow").                |
| AI Layer     | Landmark / OCR Fallback | google-cloud-vision     | Cloud API       | Multi-cloud plug-in. Routes tricky analog scans/landmarks to Google.            |
| Storefront   | API Engine              | FastAPI                 | NAS (Docker)    | Bridges the PostgreSQL database to the React Frontend.                          |
| Storefront   | Frontend Interface      | **React** or **Vue.js** | NAS (Docker)    | Modern "Split Stack" frontend. Perfect UI scaling for mobile/desktop.           |
| Infra.       | Container Management    | Portainer (Docker)      | Synology DS225+ | Runs your Web Server, Database, and Redis Queue. (Requires 6GB RAM).            |
| Infra.       | Vault Cloud Backup      | Hyper Backup            | Synology DS225+ | Block-level, encrypted, incremental backup of physical Vault files.             |

**Phase B: The Execution Strategy (Project Milestones)**

-   **Milestone 1: The Logistics Engine (Drop Zone & Vault)**
    -   *Objective:* Establish physical movement, Bouncer, and WORM protection.
    -   *Execution:* Write script monitoring a local Drop Zone, executing Perceptual Hashing (phash) routing.
-   **Milestone 2: The Core Data & Network Layer**
    -   *Objective:* Stand up PostgreSQL and extract objective EXIF hardware data.
    -   *Execution:* Build SQLAlchemy schema. Process Date Original and GPS into the database.
-   **Milestone 3: The Distributed AI Pipeline (Master/Worker)**
    -   *Objective:* Generate semantic tags using PC hardware, communicating with the NAS.
    -   *Execution:* Stand up Redis queue. Create the Celery worker script for the desktop PC to process DeepFace/CLIP tasks asynchronously.
-   **Milestone 4: The Presentation Layer (Split Stack UI)**
    -   *Objective:* Build the multi-user interactive web dashboard.
    -   *Execution:* Write FastAPI endpoints. Build React/Vue frontend featuring RBAC login, Curation Workbench, and Semantic Search.
-   **Milestone 5: Production Deployment (The DS225+)**
    -   *Objective:* Migrate to NAS for 24/7 automated operation.
    -   *Execution:* Package FastAPI, PostgreSQL, and Redis into Docker. Map paths to NAS drives. Configure Synology Photos mobile app feeder. Test PC worker connection.
