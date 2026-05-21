```
# Milestone 12.56 — Person Alias Support## GoalAdd first-class alias support for people/person records so face assignment, people search, and future Photo Review person filtering can find a person by either their canonical display name or familiar alternate names.Example desired behavior:```textPerson display name:  Charles HendersonAliases:  Charlie  Grandfather  Grandpa
```

Searching or assigning by:

```
CharlieGrandfatherGrandpaCharles
```

should all find the same person:

```
Charles Henderson
```

This milestone should implement alias support carefully and narrowly without changing face recognition, clustering, or merge behavior.

---

## Context

Recent milestones completed:

```
12.53 — Photo Review Face Assignment Workflow12.54 — Presentation Mode Face Assignment12.55 — Face Review Search, Cluster Merge, and Person Alias Planning
```

12.55 produced the recommended alias design:

```
Add person_aliases tableStore normalized alias valuesEnforce global alias uniqueness for v1 clarityExtend people search/pickers to match display name OR aliasKeep alias management UI scoped to add/remove flows
```

12.56 should now implement this design.

---

## Product Direction

People should have one canonical display name, but may have multiple aliases.

The canonical display name is the main person name shown in UI.

Aliases are search/assignment aids.

Examples:

```
Charles Hendersonaliases:- Charlie- Grandfather- Grandpa
```

```
Mary Hendersonaliases:- Mom- Grandma
```

A person alias is not a separate person.

An alias should resolve to exactly one person for v1.0.

---

## Core Principles

### 1. Canonical name remains primary

The person’s `display_name` remains the authoritative visible name.

Aliases help find that person.

UI should usually display:

```
Charles Henderson
```

not:

```
Grandfather
```

unless specifically showing alias metadata.

### 2. Alias search must be deterministic

If the user searches:

```
Grandfather
```

the system should find one person.

For v1.0, avoid ambiguous aliases.

### 3. Aliases should be globally unique

For v1.0, one alias should belong to one person only.

Do not allow:

```
Grandpa -> Charles HendersonGrandpa -> Robert Smith
```

unless future design explicitly supports scoped aliases.

### 4. Aliases should not alter face cluster identity

Aliases do not change:

- face detection
- face clustering
- cluster assignment
- person ID
- canonical display name

They only improve lookup/search/assignment.

---

## Scope

### In Scope

This milestone should implement:

- `PersonAlias` model/table
- normalized alias value for lookup/uniqueness
- alias create/list/delete APIs
- alias-aware people search
- alias-aware person picker behavior where currently used
- UI for viewing aliases on a person
- UI for adding/removing aliases
- update Face Review person search to match aliases
- update Photo Review face assignment person picker to match aliases
- update Presentation mode face assignment person picker to match aliases
- update Photo Review structured People filter if practical
- documentation
- validation

### Conditional Scope

If updating every person picker/search surface is too broad, prioritize:

```
1. Face Review person search2. Photo Review face assignment picker3. Presentation face assignment picker4. Photo Review structured People filter5. People view / person management UI
```

But the preferred outcome is that all current person search/picker surfaces share the same alias-aware backend/search helper.

### Out of Scope

Do not implement:

- relationship-specific aliases
- per-user aliases
- scoped aliases
- alias confidence/scoring
- automatic alias inference
- nickname generation
- fuzzy alias matching beyond case-insensitive/normalized exact or contains matching
- person merge workflow unless already existing and unaffected
- face recognition changes
- face clustering changes
- cluster merge changes
- Photo Review search redesign
- Presentation mode redesign
- Collections model

---

## Required Codebase Reconnaissance

Before implementation, inspect and document current person-related code.

### 1. Person model

Inspect:

- `Person` model/table
- `display_name`
- `notes`
- timestamps
- uniqueness rules
- current normalization rules
- current person creation logic
- current duplicate-name handling

Document current constraints.

---

### 2. Person service

Inspect person service logic.

Document:

- how people are created
- how duplicate names are blocked
- whether normalization is case-insensitive
- whether there is existing search
- where alias-aware lookup should live

Expected current behavior:

```
Person display_name uniqueness is enforced.
```

Do not weaken that.

---

### 3. Person APIs

Inspect:

- people list endpoint
- create person endpoint
- any person detail endpoint
- any person update endpoint
- any people-with-clusters endpoint
- any assignment endpoints that consume person IDs

Document what must be extended.

---

### 4. Person picker/search surfaces

Inspect frontend areas where a user searches/selects people:

```
Photo Review face assignment panelPresentation mode face assignment popoverFace Review cluster pane person searchFace Review assign/reassign controlsPhoto Review structured People filterPeople viewUnassigned Faces workflows
```

Document which currently use person list, local filtering, server filtering, or direct person IDs.

---

### 5. Existing migration/schema pattern

Inspect how schema changes are handled.

Document:

- whether project uses Alembic or ensure-table logic
- existing migration scripts
- idempotent migration pattern
- how recent schema additions were handled

12.56 will need a safe, idempotent alias table creation path.

---

## Required Implementation Areas

## 1. PersonAlias Data Model

Add a new model/table.

Suggested table:

```
person_aliases
```

Suggested fields:

```
idperson_idaliasalias_normalizedcreated_at_utcupdated_at_utc, if project convention uses it
```

Required relationships:

```
Person 1 -> many PersonAlias
```

Required constraints:

```
person_id references people.idalias_normalized unique globallyalias not empty
```

Recommended indexes:

```
person_idalias_normalized
```

### Normalization

Implement a normalization helper.

Suggested behavior:

```
trim whitespacecollapse internal repeated spaces if project convention allowslowercase
```

Examples:

```
" Grandpa " -> "grandpa""CHARLIE" -> "charlie"
```

Do not overbuild fuzzy matching.

---

## 2. Schema Migration / Ensure Logic

Add safe schema creation/migration.

Required:

- idempotent table creation
- safe for existing dev DB
- safe for fresh DB
- no data deletion
- no person data modification
- no automatic alias backfill unless explicitly trivial and safe

If using migration script, include it in repo and document how/when it was run.

If using app startup ensure logic, document it.

---

## 3. Alias Service

Create or extend service logic for aliases.

Required operations:

```
list aliases for personadd alias to personremove aliassearch people by display name or alias
```

Validation:

- alias cannot be empty
- alias cannot duplicate another alias
- alias cannot duplicate another person’s display name if this would create ambiguity
- alias should probably not equal the same person’s display name
- duplicate alias with different case should be blocked

Recommended error messages:

```
Alias already exists for another person.Alias matches an existing person's display name.Alias is already the display name for this person.
```

### Display-name conflict rule

For v1.0, do not allow alias values that conflict with any existing `Person.display_name` normalized value.

Reason:

```
Searching "Mary Henderson" should not have to choose between one person's display name and another person's alias.
```

---

## 4. Alias APIs

Add narrow APIs.

Possible endpoints:

```
GET /api/people/{person_id}/aliasesPOST /api/people/{person_id}/aliasesDELETE /api/people/{person_id}/aliases/{alias_id}
```

or project-consistent equivalents.

Also update people list/search response to include aliases if practical.

Suggested response shape:

```
{  "id": 1,  "display_name": "Charles Henderson",  "aliases": ["Charlie", "Grandfather", "Grandpa"]}
```

Do not expose normalized alias unless useful for debugging.

---

## 5. Alias-Aware People Search

Update person search/list logic so searching by alias returns the canonical person.

Example:

```
query = "Grandfather"returns:  Charles Henderson  aliases: Grandfather, Grandpa, Charlie
```

Search should match:

```
Person.display_namePersonAlias.alias
```

Preferred behavior:

- case-insensitive
- fragment match if existing people search uses fragment match
- exact normalized matching for uniqueness checks

If multiple people match through different names/aliases, return all matching people, but alias values themselves should still be globally unique.

---

## 6. Update Person Pickers / Assignment Surfaces

Update person search/pickers to use alias-aware people results.

Priority surfaces:

### A. Photo Review face assignment

When assigning a face:

```
search "Grandfather"select Charles Hendersonassign cluster to Charles Henderson
```

### B. Presentation mode face assignment

Same behavior as Photo Review.

### C. Face Review cluster assignment/reassignment

Search by alias should find canonical person.

### D. Face Review person filter

Filtering by alias should show clusters for the canonical person.

### E. Photo Review structured People filter

If practical, selecting people by alias should work there too.

---

## 7. Alias Management UI

Add a minimal UI to view/add/remove aliases.

Preferred location:

```
People view / Person detail area
```

or wherever person details are currently managed.

Minimum behavior:

```
select/open personview aliasesadd aliasremove alias
```

Do not create a full person management redesign.

Validation and messages:

```
Alias added.Alias removed.Alias already exists for another person.Alias conflicts with an existing person name.
```

If there is no obvious person detail UI, add a small alias management section to the most appropriate existing People/Face Review person area.

---

## 8. Documentation

Update/create:

```
docs/operations/person_alias_support_12_56.md
```

Document:

1. purpose of aliases
2. canonical display name vs aliases
3. data model
4. normalization rules
5. uniqueness rules
6. API behavior
7. UI behavior
8. search/picker behavior
9. validation performed
10. limitations/future work

---

## Validation Requirements

### Backend validation

Validate:

```
create aliaslist aliasesdelete aliasduplicate alias blockedcase-insensitive duplicate blockedalias conflicting with another person display name blockedalias matching same person's display name blockedsearch by alias returns canonical personsearch by display name still works
```

### UI validation

Validate:

```
add alias to personremove alias from personPhoto Review assignment picker finds person by aliasPresentation assignment picker finds person by aliasFace Review assignment picker finds person by aliasFace Review person filter finds person by aliasPhoto Review structured People filter finds person by alias, if updated
```

### Regression validation

Validate:

```
existing person creation still worksexisting duplicate-name blocking still worksPhoto Review face assignment still works by display namePresentation face assignment still works by display nameFace Review cluster assignment/reassignment still worksFace Review cluster merge still worksPhoto Review structured search still worksfrontend build passesbackend tests pass if changed
```

---

## Safety Requirements

Do not:

- delete people
- delete clusters
- delete faces
- alter face recognition
- alter face clustering
- alter cluster merge semantics
- alter ingestion
- alter Source Intake
- alter iCloud acquisition
- alter display URL contract
- modify media files
- modify Vault files

Alias add/remove should affect only alias records.

---

## Performance Notes

Alias search should be efficient enough for v1.0.

If table is small, simple joins/LIKE are acceptable.

Document future indexing needs if necessary.

Recommended indexes:

```
person_aliases.person_idperson_aliases.alias_normalized
```

---

## Deliverables

Required deliverables:

1. PersonAlias model/table
2. idempotent migration/ensure logic
3. alias service functions
4. alias APIs
5. alias-aware people search
6. updated assignment/person picker surfaces
7. alias management UI
8. validation/tests
9. operations documentation
10. coder closeout response

Expected closeout file:

```
docs/prompts/Coder response 12.56.md
```

---

## Definition of Done

12.56 is complete when:

- a person can have aliases
- aliases are globally unique
- aliases are normalized for case-insensitive lookup
- aliases can be added/listed/removed
- aliases cannot conflict with existing person names
- person search can find people by alias
- face assignment pickers can find people by alias
- Face Review person search/filter can find people by alias
- alias UI exists in a reasonable person management location
- existing display-name-based workflows still work
- no face cluster logic is changed
- documentation explains alias behavior and limitations

---

## Required Coder Closeout Response

Create:

```
docs/prompts/Coder response 12.56.md
```

The closeout response should include:

1. Milestone title and date
2. Scope completed
3. Files inspected
4. Files modified or added
5. Data model summary
6. Migration/ensure summary
7. Alias normalization/uniqueness rules
8. API changes
9. Service/search changes
10. UI changes
11. Assignment picker updates
12. Validation performed
13. Regression checks
14. Safety confirmation
15. Deviations from prompt
16. Known limitations
17. Recommended next milestone

---

## Recommended Next Milestone

After 12.56, proceed to:

```
12.57 — Face Review Cluster Thumbnail and Scale Improvements
```

or, if face workflow is stable enough:

```
12.57 — Collections / Album / Event Design
```

# Answers to Coder Questions — Milestone 12.56

## 1. Conflict rule strictness

Confirmed.

Block alias creation if the normalized alias matches **any existing person display_name**, including the same person.

Rules:

```text
alias cannot equal another person's display_name
alias cannot equal the same person's display_name
alias cannot equal another existing alias
alias cannot equal the same person's existing alias

Reason:

Canonical display names should remain primary.
Aliases should only add alternate lookup names, not duplicate canonical names.

Example:

Person: Charles Henderson
Alias: Charles Henderson

should be blocked as unnecessary/confusing.

2. Normalization policy

Confirmed.

Use:

trim
collapse repeated internal whitespace
lowercase

Examples:

" Grandpa " -> "grandpa"
"Grandpa   C." -> "grandpa c."
"CHARLIE" -> "charlie"

Keep this normalization helper centralized so display-name conflict checks and alias uniqueness checks use the same behavior.

3. Alias character policy

Allow normal punctuation/symbols for v1.0, within reason.

Approved examples:

Grandpa C.
Aunt Mary
Mary-Helen
O'Connor
Dad #1

Do not restrict to letters only.

But enforce:

not empty after trim
reasonable max length, preferably same or lower than display_name limit
no control characters

If the existing app has a standard text validation pattern, follow it.

Do not overbuild character validation in 12.56.

4. Deletion behavior

Confirmed.

Use hard delete for alias removal in 12.56.

No soft delete or audit table needed.

Reason:

Aliases are user-managed search helpers, not primary identity records.

Deleting an alias should not affect:

Person
FaceCluster
Face
Asset
assignments
5. API response shape

Yes.

Include aliases in:

/api/people
/api/people-with-clusters

as:

"aliases": ["Charlie", "Grandfather"]

Default should be:

"aliases": []

This is the cleanest way to make existing frontend-local pickers alias-aware without adding separate search calls everywhere.

Do not expose alias_normalized in normal UI responses unless needed for debugging.

6. People view UX

Yes.

Use the minimal People view UX:

inline alias chips
add alias input/control per person card
remove alias button on each alias chip

Keep it small.

Do not redesign the People view.

Expected behavior:

Person card:
  Charles Henderson
  Aliases: Charlie [x], Grandfather [x]
  Add alias: [________] [Add]

Show clear validation messages:

Alias already exists for another person.
Alias matches an existing person name.
Alias added.
Alias removed.
7. Photo Review structured People filter

Confirmed.

For 12.56, “practical” means alias-aware matching of the already-loaded candidate list is enough.

No new backend search API is required for this unless coder finds it already exists and is trivial.

Expected behavior:

People picker/search box:
  user types Grandfather
  candidate Charles Henderson appears because Grandfather is an alias

Backend filtering can still use person_ids after the UI resolves the selected person.

8. Backfill

Confirmed.

No backfill from people.notes.

Aliases start empty unless the user adds them manually.

Reason:

Notes may contain arbitrary text.
Automatically turning notes into aliases would be unsafe and confusing.

If future import/backfill is desired, handle that as a separate explicit task.

Summary for Coder

Proceed with:

- Dedicated person_aliases table.
- alias_normalized globally unique.
- normalization = trim + collapse spaces + lowercase.
- allow normal punctuation/symbols.
- block aliases that conflict with any person display_name, including same person.
- hard delete aliases.
- include aliases in /api/people and /api/people-with-clusters.
- minimal People view alias chips/add/remove UI.
- make existing frontend person pickers/searches alias-aware using returned aliases.
- no notes backfill.
- no alias-aware backend Photo Review search endpoint unless already trivial.