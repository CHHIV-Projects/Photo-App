**Milestone 11.12 — Object and Scene Understanding**

**Goal**

Add a first-pass **object and scene understanding layer** that extracts useful visual tags from photos so the archive can be described by more than people, time, place, and provenance.

This milestone should create a safe, explainable content-understanding foundation for future filtering, search, curation, and timeline/context improvements.

**Context**

The current system already supports:

-   ingestion and deduplication
-   provenance and duplicate lineage
-   metadata extraction and normalization
-   capture-type classification and timeline browsing
-   face detection, clustering, person assignment, and person suggestions
-   albums / manual grouping

Current limitation:

-   the system does not yet understand general image content such as:
    -   dogs
    -   cars
    -   beach
    -   wedding
    -   sunset
    -   indoor / outdoor
    -   landscape / portrait scene types

This milestone introduces a first semantic layer for **objects and scenes**, but keeps scope tightly controlled.

**Core Principles**

1.  **Tag, do not over-interpret**
2.  **Explainable outputs over heavy black-box behavior**
3.  **Confidence-aware, safety-first tagging**
4.  **Useful general categories first**
5.  **Do not redesign search yet**

**Scope**

**In Scope**

-   visual content tagging for photos
-   object and/or scene label extraction
-   confidence-aware filtering of labels
-   persistence of accepted tags
-   photo detail display of tags
-   basic filtering support using tags if simple
-   rerunnable tag generation workflow

**Out of Scope**

-   natural-language semantic search
-   freeform caption generation
-   OCR/document understanding
-   advanced model orchestration
-   training custom models
-   face/person recognition redesign
-   automatic event relabeling
-   UX redesign across all views
-   background job system

**Product Intent**

The user should be able to do things like:

-   see that a photo is tagged as:
    -   dog
    -   beach
    -   car
    -   sunset
    -   indoor
-   inspect content tags in photo detail
-   eventually use these tags as a foundation for richer search and grouping

This milestone is about creating the **content layer**, not the full search experience yet.

**Locked Design Decisions**

**1. Asset scope**

Run object/scene understanding on:

-   **canonical assets only**

Do not process non-canonical near-duplicate assets in 11.12.

Reason:

-   avoids duplicate tag work
-   aligns with current archive truth model
-   keeps scale manageable

**2. Tagging target**

Store tags at the **asset level**.

Do not create region-level/object-box workflows in this milestone.

**3. Model approach**

Use a **pretrained general-purpose image classification / tagging approach** that is practical in the current local environment.

Preferred characteristics:

-   local inference
-   no external/cloud dependency
-   broad object/scene coverage
-   confidence scores available

Coder may choose the exact library/model, but it must be:

-   lightweight enough for local-first use
-   stable
-   explainable at the label level

Do not introduce a heavyweight distributed inference stack.

**4. Controlled vocabulary**

Use a **normalized controlled label set** for persisted tags.

This means:

-   raw model outputs may be mapped/cleaned
-   persisted tags should be reasonably stable and human-readable

Examples:

-   dog
-   cat
-   car
-   beach
-   mountain
-   indoor
-   outdoor
-   sunset
-   water
-   building

Do not persist noisy long-tail labels blindly if they are low-value or overly specific.

**5. Confidence handling**

Persist only tags above a confidence threshold.

Locked default behavior:

-   use config-driven threshold
-   keep **top useful tags only**
-   default maximum persisted tags per asset: **5**
-   default minimum confidence should be conservative

If confidence is weak:

-   do not persist the tag

**6. No user correction workflow yet**

In 11.12:

-   tags are system-generated only
-   no manual add/edit/remove UI yet

This is a read-only semantic layer for now.

**7. UI integration scope**

Show tags in:

-   **Photos detail view only** for this milestone

Do not add tag UI yet to:

-   Timeline
-   Albums
-   Events
-   Places
-   People
-   Review

If simple, basic photo filtering by tag may be added to existing Photos filtering, but it is optional.

**8. Reprocessing behavior**

Support rerunnable tag generation safely.

Preferred behavior:

-   process assets missing content tags
-   optionally support explicit rebuild/recompute mode later
-   normal runs should not repeatedly overwrite unchanged results without reason

**Functional Requirements**

**1. Content Tag Model**

Add a model for storing asset-level content tags.

Minimum fields:

-   id
-   asset_id
-   tag
-   confidence_score
-   tag_type (recommended: object or scene)
-   created_at

Rules:

-   one asset can have multiple tags
-   duplicate (asset_id, tag) rows should be prevented
-   persisted tags should come from normalized vocabulary, not arbitrary raw strings

**2. Tag Generation Workflow**

Add a service or script that:

-   loads canonical asset image
-   runs content understanding model
-   obtains raw predictions
-   maps/filters them into controlled tags
-   stores accepted tags

Requirements:

-   deterministic enough for repeated use
-   failed assets should be retryable
-   does not disturb unrelated systems

**3. Normalization / Mapping Layer**

Introduce a simple mapping layer from raw model labels to persisted tags.

Examples:

-   golden retriever → dog
-   sports car → car
-   seashore → beach
-   living room → indoor

Keep mapping simple and explicit.  
Do not build a taxonomy engine.

**4. Confidence Thresholds**

Add dedicated config values such as:

-   CONTENT_TAG_MIN_CONFIDENCE
-   CONTENT_TAG_MAX_PER_ASSET

Optional if helpful:

-   separate thresholds by tag type:
    -   CONTENT_OBJECT_MIN_CONFIDENCE
    -   CONTENT_SCENE_MIN_CONFIDENCE

Coder may keep one threshold unless separation is clearly helpful.

**5. Photos Detail Integration**

In photo detail, display:

-   content tags
-   confidence if useful, or simple label display if confidence is noisy

Recommended UI:

-   a compact “Content Tags” section
-   grouped or visually separated by:
    -   objects
    -   scenes  
        if simple

Keep it readable.

**6. Basic Filtering (Optional but allowed)**

If simple within current architecture, allow Photos filtering by one or more tags.

This is optional in 11.12.  
Do not enlarge milestone scope to force it.

The primary goal is persistent content understanding, not full search UX.

**7. Processing Scope / Pipeline**

Add a safe way to run content tagging for new canonical assets.

Preferred pattern:

-   process assets missing content tags
-   keep this similar in spirit to incremental face processing

Do not force full global recompute on every normal pipeline run unless coder believes a small first-pass integration needs it.  
Prefer incremental behavior.

**8. Safety / Non-Destructive Requirements**

Content tagging must not:

-   alter asset files
-   affect duplicate lineage
-   affect face/person assignments
-   affect events
-   affect albums
-   affect existing metadata normalization

This is an additive layer only.

**Backend Requirements**

**Models**

Add asset-level content-tag storage model.

**Services**

Add content-tag inference and persistence service.

**Config**

Add dedicated content-tag settings.

**API**

Extend photo detail API to return content tags.

Optional:

-   simple filter support on existing photo list API if easy

**Processing**

Add script or pipeline hook for incremental tagging of missing canonical assets.

**Frontend Requirements**

**Photos View**

Show content tags on photo detail.

**Stability**

Do not break current views or workflows.

**Filtering**

Optional only if simple.

**Validation Checklist**

**Tagging Behavior**

-   canonical assets can receive content tags
-   non-canonical assets are not unnecessarily processed
-   duplicate tags are prevented
-   low-confidence/noisy tags are filtered out
-   normalized tags are persisted instead of raw noisy labels

**UI / API**

-   photo detail returns content tags
-   photo detail displays content tags clearly

**Incremental Behavior**

-   rerun skips already-tagged assets unless explicitly reprocessed
-   failed items are retryable

**Regression**

-   no impact on provenance/duplicate lineage
-   no impact on faces/people
-   no impact on events/timeline/albums
-   existing UI remains stable

**Deliverables**

-   content tag model
-   inference/tagging service
-   normalization/mapping layer
-   config values
-   photo detail API extension
-   photo detail UI integration
-   optional incremental pipeline/script integration
-   code summary describing:
    -   chosen model/library
    -   mapping strategy
    -   thresholds
    -   incremental behavior
-   validation results from coder

**Definition of Done**

-   system can generate useful object/scene tags for canonical assets
-   tags are confidence-aware and normalized
-   tags are visible in photo detail
-   reruns are safe and incremental where practical
-   no existing systems are destabilized

11.12 decisions:

- Model/library: use timm + lightweight EfficientNet-B0 (or equivalent lightweight timm classifier)
- Do not use DeepFace attributes
- Do not use CLIP unless timm/EfficientNet proves clearly unworkable

- Controlled vocabulary: yes
  - hand-curated mapping dict
  - whitelist of ~30–50 persisted labels

- tag_type:
  - assign by vocabulary rule
  - use object or scene
  - do not use auto

- Confidence settings:
  - single threshold only for 11.12
  - CONTENT_TAG_MIN_CONFIDENCE = 0.25
  - CONTENT_TAG_MAX_PER_ASSET = 5

- Trigger:
  - add standalone script backend/scripts/run_content_tagging.py
  - no FastAPI trigger endpoint in 11.12
  - pipeline integration is okay if simple

- Tag filtering:
  - no tag filtering in 11.12

- UI display:
  - show label only
  - do not show confidence scores in Photos view