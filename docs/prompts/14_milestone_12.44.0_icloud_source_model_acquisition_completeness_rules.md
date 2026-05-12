# Milestone 12.44.0 — iCloud Source Model + Acquisition Completeness Rules

## Goal

Define and implement the near-term production rules for iCloud sources, acquisition identity, and acquisition completeness before adding staging cleanup.

This milestone resolves key operational questions discovered after 12.43/12.44:

1. What exactly is an iCloud source?
2. How many iCloud sources should exist per iCloud account?
3. How is Apple ID / username associated with an iCloud source?
4. What does `recent_count` actually mean?
5. How does the operator know whether acquisition likely caught all new files?
6. How should old test iCloud sources be handled or distinguished?
7. What assumptions must be true before deleting staging files in 12.44.1?

This milestone is primarily source-model / rules / UI clarity, with limited implementation as needed.

---

## Context

The current iCloud workflow is:

```text
icloudpd acquisition
→ storage/exports/icloud/<source_label>/
→ Source Intake
→ Drop Zone
→ Vault / DB / Provenance
```

Implemented so far:

- 12.38 evaluated `icloudpd`
- 12.39 added Live Photo pairing for `icloudpd` `_HEVC.MOV`
- 12.40 added MOV/MP4 metadata trust handling
- 12.41 designed `icloudpd` connector service
- 12.42 implemented backend acquisition service
- 12.43 added Admin UI for iCloud Acquisition
- 12.44 added Admin handoff from iCloud Acquisition to Source Intake

Current unresolved issues:

- iCloud acquisition uses fixed `recent_count`
- `recent_count = 25` only checks/acquires the most recent 25 items
- if those 25 are already present, the system cannot know whether item 26+ contains unacquired files
- source creation is handled in Source Registry, but this is not obvious from the iCloud UI
- Apple ID username is entered at acquisition run time, but not clearly associated with a source
- multiple test iCloud sources/folders exist from development
- cleanup should not happen until the source/folder model is clear

---

## Core Principle

> An iCloud source represents a stable iCloud account/library staging identity. Acquisition downloads into that source; Source Intake ingests from that source.

Normal production model:

```text
1 iCloud account/library = 1 stable iCloud source
```

Example:

```text
Source Label: chuck_icloudpd
Source Type: cloud_export
Root Path: storage/exports/icloud/chuck_icloudpd/
Apple ID Username: chhendersoniv@gmail.com
```

---

## Scope

### In Scope

- define iCloud source model
- define one-source-per-iCloud-account rule
- clarify legitimate reasons for multiple sources for same account
- determine whether Apple ID username should be stored/associated with source
- improve Admin/source UI guidance if low-risk
- define acquisition completeness semantics
- clarify fixed recent-window limitations
- define near-term operator guidance for `recent_count`
- identify whether `icloudpd --until-found` or equivalent should be evaluated later
- identify test source cleanup policy
- prepare rules needed for 12.44.1 staging cleanup

### Out of Scope

- deleting staging files
- deleting or archiving source registry entries
- implementing full `until-found` / checkpoint strategy
- credential/session manager
- password storage
- multi-account session management
- scheduled acquisition
- NAS deployment
- cloud-native iCloud provenance schema
- automatic Source Intake
- automatic post-intake jobs

---

## Required Design Decisions

---

## 1. iCloud Source Definition

Define an iCloud source as:

```text
A registered Source Registry entry representing the local staging folder for one iCloud account/library acquired via icloudpd.
```

Required source fields today:

```text
source_label
source_type = cloud_export
source_root_path = storage/exports/icloud/<source_label>/
```

Recommended production naming:

```text
<person_or_account>_icloudpd
```

Examples:

```text
chuck_icloudpd
family_icloudpd
spouse_icloudpd
```

Avoid milestone/test labels for production use.

---

## 2. One Source Per iCloud Account Rule

Define default rule:

```text
Use one stable iCloud source per iCloud account/library.
```

Reason:

- avoids source label confusion
- preserves skip-known behavior
- keeps provenance consistent
- prevents multiple staging folders for the same cloud library
- simplifies cleanup
- simplifies Admin workflow

Multiple sources for the same iCloud account should be limited to:

```text
testing
controlled experiments
one-time migration/backfill
album-specific diagnostics
debugging
```

They should not be normal production practice.

---

## 3. Apple ID / Username Association

Current state:

```text
Apple ID username is supplied at acquisition run time.
```

Problem:

```text
The source itself does not clearly remember which Apple ID/account it belongs to.
```

Decision needed:

### Option A — Do not store username on source yet

Keep username as run-level only.

Pros:

- no schema change
- simple
- avoids account identity persistence

Cons:

- operator must re-enter username
- easier to run wrong username against wrong source

### Option B — Store associated username on source or source metadata

Pros:

- safer UI
- easier multi-account support later
- source identity becomes clearer
- Admin can pre-fill username

Cons:

- may require schema/model change
- should be clearly non-secret
- needs migration/schema sync

### Preferred direction

For 12.44.0, coder should evaluate whether storing a non-secret associated username is low-risk.

If low-risk, implement or design:

```text
icloud_username / account_username
```

attached to the source or source metadata.

If not low-risk, defer schema change and add clear UI guidance.

Important:

```text
Apple ID username is not a password.
Do not store password.
Do not store 2FA.
Do not store session cookies.
```

---

## 4. Source Creation Workflow

Current source creation is done in Source Registry.

12.44.0 should make this clear in the Admin UI / docs.

Expected guidance:

```text
To use iCloud Acquisition, first register an iCloud source in Source Registry:
Source Type: cloud_export
Source Label: <stable_iCloud_source_label>
Source Root Path: storage/exports/icloud/<source_label>/
```

If no valid iCloud source exists, iCloud Acquisition should show:

```text
No iCloud source registered. Create one in Source Registry first.
```

If low-risk, add a helper note or button/link:

```text
Go to Source Registry
```

Do not auto-create source silently.

---

## 5. Acquisition Completeness Semantics

Clarify what current acquisition does.

Current behavior:

```text
recent_count = N
```

means:

```text
Ask icloudpd to acquire/check the most recent N iCloud items.
```

It does **not** mean:

```text
All unacquired iCloud items have been found.
```

It does **not** mean:

```text
The system has scanned the full iCloud library.
```

It does **not** mean:

```text
The library is fully caught up.
```

Admin UI/reporting should use wording such as:

```text
Recent window checked: N
```

not:

```text
All new files acquired
```

---

## 6. Acquisition Completeness Reporting

Add or clarify report/UI fields if low-risk:

```text
recent_window_requested
files_staged_after_run
new_files_downloaded_to_staging
existing_files_skipped_by_icloudpd
completeness_status
completeness_note
```

Suggested `completeness_status` values:

```text
unknown
recent_window_checked
possibly_caught_up
not_determined
```

For 12.44.0, it is acceptable to avoid a new enum and simply add a clear note:

```text
This run checked the most recent N iCloud items. It does not prove the full library is caught up.
```

---

## 7. Near-Term Operator Guidance for `recent_count`

Define recommended settings:

### Normal small update

```text
recent_count = 25
```

Use when:

```text
only a few recent iPhone photos/videos expected
```

### Safer catch-up check

```text
recent_count = 100
```

Use when:

```text
not sure how many recent files were added
```

### Larger recent window

```text
recent_count = 250–500
```

Use when:

```text
catching up after travel
after many photos/videos
after a period without running acquisition
```

Warn:

```text
A larger recent window may take longer but is safer for catching more recent additions.
```

---

## 8. Until-Found / Checkpoint Strategy

Do not implement full until-found/checkpoint in 12.44.0 unless trivial.

But document it as the likely future production completeness strategy.

Future desired behavior:

```text
Acquire/check recent iCloud items until a threshold of consecutive already-known items is encountered.
```

or:

```text
Maintain remote cloud asset ID checkpoint.
```

Questions for future milestone:

- Does `icloudpd --until-found` solve this?
- Does `icloudpd` maintain enough local state?
- Can Photo Organizer determine “already acquired” by staged file, provenance, or remote ID?
- How many consecutive known items are enough?
- Should completeness be source-specific?
- How should Admin report “caught up”?

Add to parking lot if not already captured:

```text
PX-ICLOUD-004 — iCloud Acquisition Until-Found / Checkpoint Strategy
```

---

## 9. Test Source Identification

Development created multiple test iCloud sources.

12.44.0 should not delete them, but should document how to distinguish them.

Possible rules:

```text
production source labels should not contain:
test
trial
adapter
backend_test
12_37
12_38
```

Test sources can remain for provenance history but should eventually be marked inactive/archived.

Do not hard-delete source rows in 12.44.0.

Future source registry improvement:

```text
Source Registry Archive / Inactive Source Support
```

---

## 10. Cleanup Readiness Rules for 12.44.1

Before deleting any local iCloud staging files, 12.44.1 must know:

```text
source is registered
source root path is canonical
file is under source root
file has matching source provenance
asset exists
Vault copy exists
file was not failed/rejected/deferred
```

12.44.0 should explicitly record these as prerequisites.

---

## Optional Low-Risk UI Updates

If low-risk, update the Admin iCloud Acquisition card with clearer wording:

### Source guidance

```text
Use one stable iCloud source per iCloud account.
Create/manage sources in Source Registry.
```

### Recent count guidance

```text
This checks the most recent N iCloud items. It does not prove the entire iCloud library is caught up.
```

### Staging guidance

```text
Files are downloaded to local staging. Source Intake imports them. Cleanup is separate.
```

### Username guidance

```text
Apple ID username identifies the iCloud account. Password and 2FA are not stored by Photo Organizer.
```

---

## Documentation Deliverable

Create or update an operations/design note.

Suggested file:

```text
docs/operations/icloud_source_model_and_acquisition_rules_12_44_0.md
```

Include:

1. Definition of iCloud source
2. One-source-per-account rule
3. When multiple sources are acceptable
4. Source creation steps
5. Username/account identity policy
6. Recent count semantics
7. Acquisition completeness limitations
8. Recommended recent count values
9. Future until-found/checkpoint strategy
10. Test source cleanup/archival note
11. Cleanup prerequisites for 12.44.1

---

## Coder Reconnaissance Required

Before coding, answer:

1. Does `IngestionSource` currently have any metadata/notes field suitable for iCloud username?
2. Would adding `account_username` / `source_username` require schema change?
3. Is a schema change worth it now?
4. Can Admin UI display clearer source/recent-count guidance without backend change?
5. Does backend currently expose enough run data to add completeness notes?
6. Does `icloudpd` expose/use `--until-found` in the installed version?
7. Does source registry support active/inactive/archive status today?
8. How many iCloud test sources currently exist?
9. What source labels look production-worthy vs test-only?

Pause before adding schema changes unless clearly low-risk.

---

## Coder Clarification Expectations

Before implementation, answer:

1. Should username be stored on source now or deferred?
2. Should 12.44.0 be mostly documentation/UI guidance or include model changes?
3. What exact UI wording will be added?
4. How will recent-count semantics be shown?
5. How will source creation guidance be shown?
6. What cleanup prerequisites will be passed to 12.44.1?

---

## Validation Plan

### Documentation

Verify the new/updated doc clearly explains:

```text
iCloud source model
one source per account
recent_count limitations
cleanup prerequisites
```

### UI Guidance, If Implemented

Verify Admin UI shows:

```text
one source per iCloud account guidance
recent window limitation
source registry guidance
password/session policy
```

### No Behavior Regression

Verify:

```text
iCloud Acquisition still runs
Prepare Source Intake still works
Source Intake still runs
No staging cleanup occurs
```

### Build

Run:

```powershell
npm run build
```

if frontend changes are made.

---

## Safety Requirements

- do not delete staging files
- do not delete source registry rows
- do not store passwords
- do not store 2FA
- do not store session cookies
- do not auto-create sources silently
- do not auto-run Source Intake
- do not implement scheduled acquisition

---

## Deliverables

- source/acquisition rules document
- optional Admin UI wording improvements
- decision on username association
- note on recent_count limitations
- note on future until-found/checkpoint work
- cleanup prerequisites for 12.44.1
- validation summary

---

## Definition of Done

12.44.0 is complete when:

- iCloud source model is clearly defined
- one-source-per-account rule is documented
- source creation workflow is clear
- username/account identity policy is decided or explicitly deferred
- recent_count semantics are clearly explained
- acquisition completeness limitation is documented
- future until-found/checkpoint strategy is parked
- 12.44.1 cleanup prerequisites are defined
- no cleanup/deletion is implemented

---

## Explicit Deferrals

The following remain deferred:

```text
Delete successfully ingested staging files
Source registry archive/inactive support
multi-account session manager
credential/session manager
until-found/checkpoint implementation
cloud-native iCloud provenance
scheduled acquisition
NAS operation
automatic Source Intake
automatic post-intake enrichment
```

---

## Notes

This milestone is intentionally small but important.

It prevents iCloud ingestion from becoming operationally confusing before cleanup and production use.

The aim is to make the model clear:

```text
one iCloud account → one stable source → one staging folder → Source Intake → Vault
```
