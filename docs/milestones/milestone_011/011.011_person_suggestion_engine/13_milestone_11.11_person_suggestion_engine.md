**Milestone 11.11 — Person Suggestion Engine**

**Goal**

Introduce a **suggestion-only identity assistance layer** that recommends likely person assignments for new or unassigned face clusters using prior labeled identity work, while keeping all final identity decisions human-controlled.

**Context**

The current system already supports:

-   face detection, embeddings, clustering
-   manual review and correction
-   person creation and assignment
-   reviewed cluster protection
-   incremental face processing (11.8)

Current limitation:

-   new/unassigned clusters require full manual identification
-   no reuse of prior labeled identity knowledge

This milestone adds **assistive suggestions only**, not automation.

**Core Principles**

1.  **Suggest, do not assign**
2.  **Safety over aggressiveness**
3.  **Use reviewed identity as ground truth**
4.  **Explainability required**
5.  **Deterministic behavior (no black-box ML yet)**

**Scope**

**In Scope**

-   suggestion generation for eligible clusters
-   similarity-based ranking using embeddings
-   confidence scoring and thresholds
-   explainable outputs
-   API + minimal UI integration

**Out of Scope**

-   automatic assignment
-   cluster merging/splitting
-   ML training pipelines
-   identity graph redesign

**Functional Requirements**

**1. Eligible Target Clusters**

Generate suggestions ONLY for:

-   clusters where person_id IS NULL
-   clusters not marked is_ignored
-   clusters not marked is_reviewed (i.e., unresolved)

Do NOT generate suggestions for:

-   assigned clusters
-   ignored clusters
-   reviewed/resolved clusters

**2. Trusted Source Clusters (Training Set)**

Use ONLY clusters that satisfy:

-   person_id IS NOT NULL
-   AND (is_reviewed = true OR implicitly stable assigned clusters)

Do NOT use:

-   unassigned clusters
-   machine-only clusters without human confirmation

**3. Suggestion Method (Locked)**

Use **centroid-based similarity**:

-   each cluster has centroid embedding (centroid_json)
-   for each person:
    -   compute person centroid as average of their cluster centroids
-   compare target cluster centroid to each person centroid
-   compute similarity score (cosine similarity or equivalent)

This is:

-   deterministic
-   explainable
-   sufficient for this milestone

**4. Candidate Selection (Locked)**

Return:

-   **Top 3 candidate persons maximum**

Sorted by similarity score descending.

**5. Confidence Model (Locked)**

Define thresholds (config-driven but with defaults):

-   **High confidence:** ≥ 0.75
-   **Tentative:** 0.60 – 0.74
-   **No suggestion:** \< 0.60

Ambiguity rule:

-   If top two candidates differ by \< 0.05 → mark as **ambiguous**
-   Ambiguous → downgrade to tentative or no suggestion

**6. Suggestion Output Shape**

Return:

-   cluster_id
-   suggestion_state: high_confidence \| tentative \| none \| ambiguous
-   suggested_people[]:
    -   person_id
    -   person_name
    -   confidence_score
    -   rank

**7. Explainability (Locked)**

Include simple explanation string:

Examples:

-   “Closest match to previously labeled clusters for [Person Name]”
-   “Multiple similar matches — low confidence”

Do NOT expose raw embedding data.

**8. Generation Strategy (Locked)**

Use **on-demand generation**:

-   compute suggestions when requested via API
-   no background jobs
-   no precomputation layer

Reason:

-   simpler
-   always up-to-date
-   acceptable performance at current scale

**9. UI Integration (Locked Scope)**

Add suggestions ONLY in:

-   cluster review / assignment panel
-   unassigned cluster view

UI behavior:

-   show top suggestion prominently
-   show up to 2 alternates (if above threshold)
-   display confidence label:
    -   Strong suggestion
    -   Tentative suggestion
    -   No strong suggestion

User can:

-   accept suggestion via existing assignment action
-   ignore it

No auto-assign.

**10. Assignment Flow**

No new assignment mechanism.

Use existing:

-   assign cluster → person action

Suggestion only assists selection.

**11. Non-Destructive Guarantee**

Suggestions must NOT:

-   change cluster membership
-   change person assignments
-   merge/split clusters
-   modify embeddings

**Backend Requirements**

**Data Usage**

-   use existing embeddings + centroids
-   compute person centroids dynamically

**Config**

Add configurable values:

-   similarity threshold
-   ambiguity margin
-   max candidates (default 3)

**API**

Add endpoint:

-   GET /clusters/{cluster_id}/suggestions

**Frontend Requirements**

-   display suggestions in review panel
-   show confidence labels
-   allow manual override always
-   no UI redesign beyond minimal integration

**Validation Checklist**

**Suggestion Quality**

-   correct suggestions for known clusters
-   ambiguous cases handled conservatively
-   weak matches suppressed

**Safety**

-   no automatic assignments
-   no mutation of existing data

**API/UI**

-   returns correct ranked candidates
-   UI displays clearly

**Regression**

-   review workflow unchanged
-   people/clusters unaffected

**Deliverables**

-   suggestion service
-   config thresholds
-   API endpoint
-   UI integration
-   code summary
-   validation report

**Definition of Done**

-   system suggests likely person matches for unassigned clusters
-   suggestions are confidence-aware and explainable
-   ambiguous/weak cases handled safely
-   no automatic identity changes occur
-   existing workflows remain stable

11.11 decisions:

- Source clusters must be strictly:
  - person_id IS NOT NULL
  - is_reviewed = true
- Endpoint path = /api/clusters/{cluster_id}/suggestions
- If target centroid_json is null:
  - suggestion_state = none
  - explanation = "Cluster has insufficient embedding data for suggestion."
- Use one explanation string at response level only
- Add dedicated config settings:
  - PERSON_SUGGESTION_HIGH_THRESHOLD
  - PERSON_SUGGESTION_TENTATIVE_THRESHOLD
  - PERSON_SUGGESTION_AMBIGUITY_MARGIN
  - PERSON_SUGGESTION_MAX_CANDIDATES
- Show suggestions only in Cluster Review panel
- Do not add suggestion UI to Unassigned Faces
- Show alternates only when top suggestion is not strong
- Tie-break equal similarity scores by lower person_id