**Milestone 11.12.1 — Content Tag Vocabulary Expansion and Coverage Refinement**

**Goal**

Improve the practical usefulness of the 11.12 content-tagging system by expanding and refining the controlled vocabulary and label-mapping layer based on the actual prediction patterns seen in this archive.

This milestone is a **targeted refinement** of the existing object/scene understanding pipeline, not a redesign.

**Context**

Milestone 11.12 successfully implemented:

-   local content tagging using a pretrained classifier
-   controlled vocabulary with normalized persisted tags
-   confidence thresholding
-   asset-level tag persistence
-   photo detail UI display of tags

Current limitation:

-   coverage is low because many model predictions:
    -   fall outside the current whitelist
    -   or do not map cleanly into the existing controlled vocabulary

Observed result:

-   pipeline works technically
-   but many photos receive no persisted tag because the current vocabulary is too narrow for real archive content

This milestone should improve **coverage and usefulness** while preserving the original safety principles:

-   controlled vocabulary
-   human-readable tags
-   confidence-aware filtering
-   no raw noisy labels

**Scope**

**In Scope**

-   review actual model predictions across the archive
-   expand the controlled vocabulary
-   expand/refine raw-label → normalized-tag mappings
-   improve coverage while maintaining quality
-   rerun tagging with updated vocabulary
-   provide before/after coverage summary
-   keep existing storage/API/UI shape stable unless a small label display improvement is clearly helpful

**Out of Scope**

-   changing the underlying model
-   adding freeform/raw label persistence
-   semantic search redesign
-   manual tag editing
-   tag filtering/search UI
-   OCR/captioning
-   taxonomy engine or ontology system

**Core Principles**

1.  **Expand vocabulary, not noise**
2.  **Use real archive evidence**
3.  **Keep tags human-readable**
4.  **Preserve controlled persisted output**
5.  **Improve coverage without sacrificing trust**

**Required Approach**

**1. Archive-Driven Vocabulary Review**

Inspect the real prediction output from the current tagging model and identify:

-   common raw labels that currently fail mapping
-   common useful concepts present in this archive
-   labels that should be promoted into the persisted vocabulary

Focus on practical archive categories such as:

-   travel/outdoor scenes
-   household/family contexts
-   animals/pets
-   vehicles
-   nature/water/sky/weather
-   buildings/architecture
-   celebrations/common life scenes

Do not expand arbitrarily; use observed archive predictions as the basis.

**2. Controlled Vocabulary Expansion**

Expand the whitelist from the current small set to a broader but still controlled vocabulary.

Target:

-   approximately **80–120 persisted tags**

This is a guideline, not an exact requirement.

Requirements:

-   tags must remain:
    -   stable
    -   human-readable
    -   broadly useful
-   avoid obscure or overly specific labels unless clearly valuable

Examples of acceptable expansions:

-   tree
-   flower
-   snow
-   boat
-   airplane
-   bridge
-   city
-   street
-   food
-   baby
-   group
-   park
-   kitchen
-   party

Only include tags that are meaningfully supported by observed predictions and useful for browsing later.

**3. Mapping Refinement**

Expand and improve the mapping dictionary.

Examples:

-   seashore, lakeside, shore → beach or water as appropriate
-   sports car, convertible → car
-   tabby, Persian cat → cat
-   golden retriever, Labrador retriever → dog
-   alp, volcano → mountain
-   palace, castle, monastery → building
-   dining table, plate rack, restaurant → indoor or food only if mapping is clearly justified

Keep mappings explicit and reviewable.

Do not create hidden or fuzzy mapping logic.

**4. Preserve Tag Quality**

Do NOT:

-   persist raw ImageNet labels directly
-   expand into a noisy uncontrolled label set
-   lower the confidence threshold just to inflate coverage without evidence

Threshold changes are allowed only if coder believes a small adjustment is clearly justified by results, and if documented.

Default assumption:

-   keep current confidence threshold unless archive-driven review shows a strong reason to tune it slightly

**5. tag_type Rules**

Continue assigning tag_type by vocabulary rule:

-   object
-   scene

If new tags are added, they must be classified consistently.

Do not introduce additional tag types in this milestone.

**6. Rebuild / Reprocess**

After vocabulary and mapping refinement:

-   rerun tagging in rebuild mode for canonical assets
-   preserve existing schema/model/API shape
-   update persisted tags based on the improved mapping rules

This milestone is expected to improve stored results through a controlled rebuild.

**7. Coverage Reporting**

Provide a before/after summary including:

-   assets evaluated
-   assets tagged
-   total tag rows written
-   percentage coverage before refinement
-   percentage coverage after refinement

Also provide a concise summary of:

-   top newly useful tags added
-   common raw labels that were newly mapped
-   examples of labels deliberately rejected as too noisy

**8. UI Scope**

Keep UI changes minimal.

Existing photo detail tag display is sufficient unless a very small readability improvement is clearly beneficial.

Do not add:

-   tag filters
-   tag editing
-   new tag surfaces in Timeline/Albums/Events

**Backend Requirements**

**Vocabulary / Mapping**

Refine and expand the controlled vocabulary and label mapping files.

**Tagging Workflow**

Support controlled rebuild with updated vocabulary.

**Stability**

Do not break:

-   existing content tag schema
-   photo detail API
-   current Photos UI tag display

**Validation Checklist**

**Coverage / Quality**

-   archive coverage improves materially over 11.12 baseline
-   persisted tags remain controlled and human-readable
-   raw noisy labels are still filtered out
-   mapping improvements are explicit and reviewable

**Rebuild Behavior**

-   rebuild updates content tags cleanly
-   rerun remains deterministic
-   duplicate tag rows are still prevented

**Regression**

-   no impact on provenance/duplicate lineage
-   no impact on faces/people
-   no impact on events/timeline/albums
-   photo detail UI remains stable

**Deliverables**

-   expanded whitelist / controlled vocabulary
-   expanded raw-label mapping rules
-   rebuild run against canonical assets
-   before/after coverage summary
-   concise code summary describing:
    -   vocabulary growth
    -   mapping strategy
    -   any threshold changes (if made)
    -   observed archive-specific improvements

**Definition of Done**

-   content tagging coverage improves materially
-   persisted tags remain clean, controlled, and useful
-   mapping is better aligned with real archive content
-   no unrelated systems are affected

11.12.1 decisions:

- Run the archive audit internally and proceed directly to implementation.
- No need to pause for approval of the audit results first.
- Use the audit to drive vocabulary/mapping refinement, then report back with:
  - common unmapped raw labels
  - new normalized tags added
  - mapping examples
  - before/after coverage

- Expansion should be primarily driven by actual model predictions across the archive.
- When choosing among useful additions, prioritize categories that help with:
  - travel/outdoor
  - water/beach/lake/mountain/snow/park
  - pets/animals
  - buildings/city/street/bridge
  - vehicles/boat/airplane
  - celebrations/party/group
  - indoor/kitchen/food