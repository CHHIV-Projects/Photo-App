# Parking Lot Summary v3

Compact 1-2 sentence summaries of each parking lot entry.

## 1) Near-Term Promotion Candidates

- **ICL-001**: Implements an until-found/checkpoint strategy for iCloud acquisition so runs can detect true completeness instead of looping over a fixed recent window. It solves re-download churn and unknown coverage after staging cleanup.
- **SRC-001**: Adds archive/inactive lifecycle states for sources instead of hard deletion. It solves provenance risk and source-list clutter from legacy test sources.
- **SRC-002**: Cleans up iCloud test source labels/folders and stale staging artifacts. It solves operational clutter while preserving explainability for already-ingested data.
- **SRC-003**: Replaces multi-step source handling with a unified Source Profile + Run Intake workflow. It solves daily usability friction while preserving safe ingestion boundaries.
- **OPS-001**: Creates a unified history view linking acquisition, intake, cleanup, and post-intake jobs. It solves operator trust and troubleshooting gaps across split workflows.
- **PX-016**: Adds explicit discovery for undated/low-trust assets via filters and timeline handling. It solves the inability to quickly find metadata-date gaps.
- **PX-018**: Adds manual date-trust override for physical-media photos where EXIF date reflects digitization, not original capture. It solves timeline correctness issues without rewriting source metadata.

## 2) iCloud / Cloud Acquisition Track

- **ICL-002**: Defines long-term credential/session boundaries for iCloud acquisition. It solves uncertainty around auth ownership, especially for NAS and scheduled operation.
- **ICL-003**: Adds preflight iCloud authentication status in Admin before acquisition runs. It solves avoidable run failures caused by expired/missing sessions.
- **ICL-004**: Defines safe multi-account iCloud operation and source/account isolation. It solves wrong-account/wrong-source mixing risk.
- **ICL-005**: Extends provenance with cloud-native iCloud identity fields where available. It solves limited traceability when local staged filenames are insufficient.
- **ICL-006**: Exposes safe advanced icloudpd options with guardrails. It solves the need for control without risking destructive or provenance-breaking flags.
- **ICL-007**: Imports iCloud organizational metadata (albums/favorites/people) if feasible. It solves loss of higher-level cloud organization during local intake.

## 3) Source Registry / Ingestion / Operations

- **IN-001**: Defines deterministic Drop Zone reprocessing behavior after interrupted/partial runs. It solves retry safety, duplicate staging risk, and unclear residual-file handling.
- **IN-002**: Clarifies durable provenance vs transient ingestion-run history as separate concepts. It solves model confusion that can affect cleanup/reprocessing logic.
- **IN-003**: Improves progress/completeness reporting for large sources. It solves low visibility during long imports and helps operators estimate remaining work.
- **OPS-002**: Adds an Admin report browser for operational logs across major jobs. It solves manual JSON hunting and improves operational observability.
- **OPS-003**: Adds optional post-intake enrichment chaining after Source Intake. It solves repetitive manual job triggering and enables guided automation.

## 4) Photo Review / General UX

- **UX-001**: Builds a photo-centric correction workspace that unifies key correction tasks from one detail surface. It solves fragmented workflows across multiple screens.
- **UX-002**: Formalizes UI surface separation (Viewer, Workbench, Admin). It solves mode confusion and clarifies intent by workflow type.
- **UX-003**: Adds auto-advance after repetitive actions (duplicate/face/date/demotion tasks). It solves high-click friction in review-heavy workflows.
- **UX-004**: Expands smart filtering for trust/location/face/demotion/media states. It solves limited targeting when triaging large archives.
- **UX-005**: Improves person-centric navigation into review/correction flows. It solves weak continuity between people records and actionable face work.

## 5) Face / Identity System

- **ID-001**: Lets users create a new cluster/person from a single unassigned face. It solves dead-ends when no suitable cluster exists.
- **ID-002**: Improves cluster selection/move UX. It solves friction and error-prone reassignment during identity cleanup.
- **ID-003**: Enables representative face selection for clusters/people. It solves poor identity visibility caused by weak default thumbnails.
- **ID-004**: Shows cluster confidence/quality indicators. It solves low trust and weak prioritization for identity decisions.
- **FW-001**: Adds bulk face actions. It solves slow one-by-one processing for large correction queues.
- **FW-002**: Improves cluster suggestion quality and assignment flow. It solves inefficiency and misses in current suggestion workflows.
- **FW-003**: Adds side-by-side face/cluster comparison tools. It solves difficult visual decision-making during ambiguous matches.
- **FW-004**: Adds dismissal of incorrect suggestions. It solves repeated resurfacing of known-bad suggestions.

## 6) Location / Places

- **PL-001**: Expands location intelligence beyond reverse geocoding into hierarchy/landmark/inference tracks. It solves shallow location context for richer browsing.
- **PL-002**: Adds richer location filters (country/state/city/place/user label/missing). It solves coarse location query limitations.
- **PL-003**: Normalizes duplicate/inconsistent place names. It solves fragmented place browsing caused by naming drift.
- **PL-004**: Defines handling for missing GPS/location assets. It solves inconsistent behavior for location-incomplete media.
- **PL-005**: Reconciles conflicts between provenance-implied and GPS/geocoded location. It solves contradictory location truth sources.

## 7) Collections / Albums / Events

- **CO-001**: Enables event-to-album integration while preserving independent models. It solves manual bridging between event workflows and curated collections.
- **CO-002**: Evaluates unifying albums/collections/smart collections/saved filters. It solves conceptual fragmentation in organization features.
- **EV-001**: Ensures event date range recalculation consistency across merges/assignments/removals/corrections. It solves drift and inconsistency in event timelines.

## 8) Media / Video / Live Photo

- **MV-001**: Adds Live Photo playback UX for paired still+motion assets. It solves the current gap where pairing exists but playback is unavailable.
- **MV-002**: Adds optional hiding/filtering for Live Photo motion companion MOV files. It solves gallery clutter while preserving access when needed.
- **MV-003**: Brings video parity to canonical metadata recompute paths. It solves image-only recompute assumptions that can leave video metadata stale.
- **MV-004**: Defines full video strategy (playback, thumbnails, metadata, duplicates, filtering). It solves incomplete end-to-end video product behavior.
- **MV-005**: Evaluates legacy camcorder format support when samples are available. It solves deferred compatibility risk for older personal archives.

## 9) Duplicate System

- **DUP-001**: Tunes pHash Hamming thresholds and related candidate logic for near duplicates. It solves missed matches and balancing false positives.
- **DUP-002**: Improves duplicate group review UX (preview/presentation/comparison/flow speed). It solves decision friction in adjudication.
- **DUP-003**: Improves duplicate detection across cross-format derivatives. It solves misses when pHash/metadata diverge by format.
- **DUP-004**: Explores safe auto-grouping for likely cross-format duplicates. It solves manual grouping overhead while guarding against unsafe merges.
- **DUP-005**: Adds multi-signal duplicate scoring beyond pHash alone. It solves weak confidence from single-signal matching.
- **DUP-006**: Adds canonical asset locking for user-selected canonicals. It solves trust issues where recomputation silently changes canonical choices.

## 10) Demotion / Visibility

- **DS-001**: Supports reversible demotion for non-duplicate unwanted assets. It solves separation of clutter management from duplicate workflows.
- **DS-002**: Adds management UI for viewing/restoring demoted assets. It solves recoverability and oversight gaps for hidden content.

## 11) NAS / Deployment / Scheduling

- **NAS-001**: Plans NAS/Synology deployment readiness for storage, services, jobs, and backups. It solves migration risk from workstation-centric operation to always-on infrastructure.
- **NAS-002**: Adds scheduled iCloud acquisition on NAS/always-on hosts. It solves manual run dependency and supports routine incremental intake.

## 12) Intelligence / AI Long-Term

- **AI-001**: Expands semantic/natural-language search using broader metadata and future embeddings. It solves limited search expressiveness for large archives.
- **AI-002**: Adds landmark/scene intelligence beyond geocoding. It solves shallow place understanding in visually meaningful contexts.
- **AI-003**: Suggests likely physical-media photos from visual cues without auto-changing trust. It solves manual triage burden while keeping user authority.
- **AI-004**: Explores assisted EXIF/metadata inference with explicit user approval. It solves missing metadata recovery while preserving explainability and control.
