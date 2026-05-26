# Google Vision Enrichment Workflow Realignment 12.60.2

## 1. Purpose
Milestone 12.60.2 is a documentation and product-direction realignment checkpoint.

This milestone defines how Google Vision should be used next without changing behavior in the current system.

## 2. Current Implementation Summary
Current implementation combines two delivered parts:

- 12.60 harness flow:
  - selected-asset Google Vision test harness
  - dry-run default, explicit live mode
  - landmark persistence to place observations
  - label/object report-only
- 12.60.1 review flow:
  - Places view section for Google Vision landmark observations
  - accept/reject/ignore actions
  - optional link to existing place
  - optional create new place from observation when coordinates exist

Current writes are explicit and user-triggered; no automatic assignment behavior was introduced.

## 3. Revised Product Direction
Google Vision should be treated primarily as photo enrichment, not as default Place assignment.

Two tracks should be handled separately:

- Track 1: assets with geolocation metadata
- Track 2: assets without geolocation metadata

## 4. Track 1 - Geolocated Assets
For assets with GPS/lat-lon:

- Place remains the geographic and user-facing location record
- reverse geocode plus user edits drive canonical place display
- Google Vision landmark is additional visual context

Recommended behavior:

- do not automatically replace Place with Vision landmark output
- do not automatically set asset.place_id from Vision landmark output
- do not automatically create a Place from Vision landmark output
- treat Vision landmark as context suggestion for review

## 5. Track 2 - No-Location Assets
For assets without GPS/lat-lon:

- Google Vision may provide landmark/context and possible location clues
- these clues may include candidate place/city/state/country and optional coordinates
- this is a higher-risk inference path and should be reviewed separately

Recommended behavior:

- separate workflow from geolocated enrichment
- require explicit user review before any place/location write
- do not merge no-GPS inference into standard geolocated Place editing flow

## 6. Place Definition
For v1, Place means the asset's geographic/user-facing location record:

- lat/lon
- reverse-geocoded location/address result
- user-corrected canonical fields
- city/county/state/postal/country
- retained provider evidence as observations

## 7. Landmark/Context Definition
For v1, Landmark should generally be treated as visual/context enrichment:

- image-derived context label
- tag-like descriptor
- may represent a visible landmark or scene context

Landmark should not automatically imply camera capture location truth.

## 8. Observation Definition
Observation means retained provider/system evidence for audit and review.

Examples include:

- reverse geocode outputs
- Google Vision landmark outputs
- future label/object candidate evidence
- manual/provenance clues

Observation is evidence, not automatic truth.

## 9. Candidate Selection Strategy
Future Vision candidate pools should support:

- manual selected assets
- selected collection subset
- selected album subset
- selected place group subset
- geolocated assets with weak/broad place information
- no-location assets
- canonical assets from duplicate groups
- source review provenance groups

Cost/control default recommendation:

- canonical assets first where possible
- avoid duplicate calls and duplicate review load

## 10. Duplicate/Canonical Asset Strategy
Recommended default run unit:

- duplicate-group canonical assets

Recommended review flow:

1. run Vision on canonical representative
2. review suggestion outcome
3. if accepted, optionally apply scope expansion

Do not auto-propagate by same lat/lon or same Place.

## 11. Propagation Strategy
Accepted landmark/context labels should default to conservative scope:

- default: this asset only

Optional user-expanded scopes:

- exact duplicates
- near-duplicate group
- selected assets
- selected album/collection subset

Propagation should always be explicit user intent, not implicit broad rule.

## 12. UI/Workspace Recommendation
Places tab should remain focused on canonical Place management:

- view and edit canonical Place/address
- review provider evidence as needed

Primary Google Vision operating workspace should move to a future tab:

- recommended name: Visual Enrichment

Visual Enrichment should eventually include:

- candidate selection controls
- Vision run controls
- landmark/context suggestion review
- accept/reject/ignore/edit actions
- later label/object review
- later no-GPS location candidate review
- run history and reports

## 13. Assessment Of 12.60.1 Implementation
12.60.1 remains technically useful and should not be removed.

Classification under revised direction:

- useful as secondary workflow
- useful for edge cases, including no-location and true place-creation needs
- not the primary enrichment workflow for geolocated assets

## 14. Recommended Next Implementation Milestone
Recommended next milestone:

- 12.60.3 - Visual Enrichment Workspace Foundation

Suggested initial scope:

- add Visual Enrichment workspace shell
- support candidate pool selection UX
- display existing landmark observations in enrichment context
- begin asset-centric landmark/context review workflow
- keep Place assignment out of scope

Alternative if storage model must be clarified first:

- 12.60.3 - Landmark/Context Tag Model Foundation

## 15. Open Questions / Risks
Open questions:

1. Should accepted landmark/context remain in place_observations for near-term iteration, or move to dedicated enrichment/tag persistence?
2. What confidence/provenance thresholds should gate no-GPS location candidate actions?
3. What exact propagation options should ship first after this-asset-only default?
4. Should exact-duplicate propagation be one-click or always explicit per action?
5. What minimal data model is needed before label/object transitions from report-only to reviewable candidates?

Risks if unresolved before implementation:

- data model rework between enrichment and place evidence
- inconsistent operator behavior for no-GPS inferred location decisions
- premature propagation beyond intended conservative scope
