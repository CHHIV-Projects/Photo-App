# Place Address Correction UI and Observation Review 12.59.2

## 1. Purpose
Milestone 12.59.2 adds a practical user workflow for correcting canonical Place address fields while reviewing provider observations as separate evidence.

Implemented outcomes:
- Canonical Place fields are editable in the Places detail panel.
- Verification and lock flags are user-controlled during canonical edits and apply flows.
- Place observations are visible with status and evidence details.
- Observation statuses can be set to accepted, rejected, or ignored.
- Address observations can be accepted without apply, or accepted and applied to canonical fields.
- Alias behavior from 12.59.1 remains available.

## 2. UX and Behavior
### Canonical Place edit form
The Places detail panel now exposes:
- user label
- place type
- formatted address
- street
- city
- county
- state
- postal code
- country
- notes
- address source
- user verified
- address locked

Save behavior:
- Uses PATCH /api/places/{place_id}
- Updates detail panel state immediately
- Updates the selected list-row summary state so the list does not remain stale

### Observation list presentation
Observation rows show:
- source type
- observation type
- status
- raw label and/or formatted address
- confidence (if present)
- created date

Raw details are hidden by default and available through a per-row details toggle.
Expanded details include raw JSON and technical fields when present.

### Observation actions
Supported actions:
- Accept
- Reject
- Ignore

Status semantics for 12.59.2:
- Reject: status update only
- Ignore: status update only
- Accept (non-address observations): status update only
- Accept (address observations):
  - Accept only (status update)
  - Accept and apply to canonical address fields

No auto-supersede behavior is applied to other pending observations.

### Accept and apply confirmation
Address observation apply flow uses a lightweight confirmation panel with:
- current canonical address summary
- observation address summary
- observation source type
- status intent (accepted + apply)
- optional toggles:
  - mark place user verified
  - lock address against provider overwrite

Default toggle behavior:
- Defaults unchecked unless the Place already has the corresponding flag set true.
- Existing true flags remain true.

## 3. API and Service Changes
### Places API
Added observation patch endpoint:
- PATCH /api/places/{place_id}/observations/{observation_id}

Request supports:
- status
- apply_to_canonical
- set_user_verified
- set_address_locked

Existing place patch endpoint is reused for canonical form updates:
- PATCH /api/places/{place_id}

### Observation update policy
Observation update flow now supports:
- status-only updates
- optional canonical address apply for address observations only

Apply-to-canonical updates only these fields:
- formatted_address
- street
- city
- county
- state
- postal_code
- country
- address_source

Not applied in 12.59.2:
- latitude/longitude
- Place representative coordinates
- asset GPS
- asset-place linking behavior

## 4. Data Model and Schema Updates
`place_observations` now includes structured address columns:
- street
- city
- county
- state
- postal_code
- country

Schema ensure flow remains idempotent and adds missing columns when absent.

## 5. Safety and Scope
Confirmed in this milestone:
- No Google Vision call integration.
- No external provider invocation from the new review UI actions.
- No map/editor redesign.
- No supersede automation.
- Source Review remains preview/read-only for place clues.

## 6. Validation Summary
Validation performed:
- Backend diagnostics: clean on modified files.
- Frontend diagnostics/types: clean on modified files.
- Frontend production build: passed.
- Transaction-wrapped backend smoke checks passed for:
  - canonical place patch
  - observation listing
  - observation reject
  - observation ignore
  - observation accept only
  - observation accept and apply address fields
  - canonical address update after apply
  - alias create/delete
  - alias-backed photo search regression
- Manual regression smoke passed for:
  - Photo Review list endpoint loading
  - Source Review asset and matches read-only endpoints

## 7. Limitations
- Confirmation is an inline panel rather than a dedicated modal dialog.
- Observation comparison tools (conflict ranking/supersede policies) are deferred.
- No observation history or audit timeline UI was added.

## 8. Recommended Next Milestone
Recommended next step:
- 12.59.3 - Reverse Geocode Observation Policy Update

Alternative if policy is stable and place workflows are sufficient:
- 12.60 - Google Vision Landmark Candidate Planning and Test Harness
