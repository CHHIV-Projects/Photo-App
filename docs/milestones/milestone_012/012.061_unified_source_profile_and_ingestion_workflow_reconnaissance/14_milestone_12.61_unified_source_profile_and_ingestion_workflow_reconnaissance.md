# Milestone 12.61 — Unified Source Profile and Ingestion Workflow Reconnaissance

## Goal

Perform a careful reconnaissance and design pass for a future unified ingestion workflow.

This is a **planning / reconnaissance milestone**.

Do **not** implement schema, backend behavior, UI changes, cleanup behavior, or ingestion flow changes yet unless explicitly approved later.

The goal is to understand the current system deeply before we redesign anything.

The concern is that ingestion/source handling has not been revisited in a while, and we do not want to:

```text
break existing intake behavior
confuse source/provenance concepts
re-invent working functionality
collapse separate operations unsafely
delete or hide source history incorrectly
```

---

## Background

The current project has separate concepts and workflows around:

```text
source registry
known sources
source intake
iCloud acquisition
cloud export staging
local/external folder intake
intake reports
provenance
staging cleanup
source review
```

The current UI has useful development/admin views, including:

```text
Recent Intake Reports
Known Sources
```

But production workflow should eventually feel simpler:

```text
Choose Source Profile
Run Intake
Review combined acquisition/intake report
```

---

## Product Direction

The desired long-term model is **Source Profile driven ingestion**.

A Source Profile represents both:

```text
where files come from
how they should be acquired/scanned/intaken
```

Examples:

### Local Folder Source Profile

```text
Source Label: Chuck's PC
Source Type: local_folder
Root Path: C:\Users\chhen\Pictures
```

### External Drive Source Profile

```text
Source Label: External 1
Source Type: external_drive
Root Path: D:\Photos
```

### iCloud Source Profile

```text
Source Label: Chuck iCloud
Source Type: cloud
Cloud Provider: iCloud
Account Username: chhendersoniv@gmail.com
Managed Staging Path: storage/exports/icloud/<generated_source_slug>/
```

Important:

```text
The user should not manually create iCloud staging folders.
The system should manage iCloud staging paths.
```

---

## Key Principle

Do not treat cloud password/session handling casually.

For v1:

```text
Photo Organizer should not collect, store, or display cloud passwords.
Photo Organizer should not store Apple ID passwords.
Photo Organizer should not store 2FA codes.
Photo Organizer should not store iCloud session cookies/tokens in the database.
```

For iCloud v1:

```text
Authentication remains delegated to icloudpd.
Password/2FA input happens outside Photo Organizer, in terminal/PowerShell via icloudpd.
Photo Organizer may store account username/identifier for source matching.
Photo Organizer may show authentication/session status if detectable.
```

The UI should not contain an Apple password field.

---

## Desired End-State Workflow

### Normal operator workflow

```text
Open Ingestion tab
Choose Source Profile
Click Run Intake
View combined report
```

### For Local / External Sources

```text
1. Source profile identifies root path.
2. System scans source root.
3. System runs source intake.
4. System reports scanned / selected / skipped / failed / remaining / complete.
```

### For iCloud Sources

```text
1. Source profile identifies provider/account/staging path.
2. System runs iCloud acquisition through icloudpd.
3. Files download into system-managed staging folder.
4. System runs source intake against that staging folder.
5. System reports acquisition + intake together.
6. System handles or offers safe staging cleanup.
```

For normal UI, iCloud acquisition should not feel like a separate required user action.

However, advanced diagnostics may still expose:

```text
check iCloud session
run acquisition only
view acquisition report
view staging folder state
cleanup staged files
```

---

## Why This Must Be Recon First

This area touches production-critical systems:

```text
source registry
provenance
staging folders
iCloud acquisition
source intake
cleanup
reports
admin UI
source review
```

A wrong implementation could:

```text
hide source history
break provenance explainability
delete staged files prematurely
mix iCloud accounts
create duplicate source records
confuse local/export/cloud source types
make reports harder to trust
```

Therefore 12.61 should inspect, document, and recommend.

---

## Scope

### In Scope

Perform reconnaissance and produce a design document covering:

- current source registry model

- current source intake flow

- current iCloud acquisition flow

- current cloud export/staging behavior

- current cleanup behavior

- current Recent Intake Reports behavior

- current Known Sources behavior

- current provenance relationship to sources

- current Source Review relationship to sources

- current test source clutter

- source profile design options

- source type taxonomy

- cloud provider/account handling

- password/session/security handling

- iCloud staging path management

- unified Run Intake workflow

- combined report model

- old source/archive/inactive strategy

- recommended implementation sequence

### Out of Scope

Do not implement:

```text
new tables
schema migrations
source profile model
new ingestion tab
source deletion
source cleanup
staging cleanup changes
iCloud acquisition changes
password/session UI
credential storage
run intake behavior changes
report UI changes
provenance model changes
source review changes
NAS scheduling
automatic post-intake jobs
```

This milestone is reconnaissance and planning only.

---

## Required Reconnaissance

Inspect the current implementation deeply.

Likely files/areas to inspect:

```text
backend/app/models/
backend/app/api/
backend/app/services/
backend/scripts/
frontend/src/components/
frontend/src/app/page.tsx
storage/logs/
docs/operations/
docs/prompts/
```

Specific areas likely relevant:

```text
source registry model/table
source intake API
source intake service
iCloud acquisition service/scripts
cloud export handling
staging folder handling
cleanup logic
provenance model/table
ingestion run model/table
source review service/API
Admin/Source Intake UI
Known Sources UI
Recent Intake Reports UI
```

Coder should identify exact current files and functions rather than guessing.

---

## Questions to Answer

### Source / Source Profile

1. What is the current data model for known sources?

2. Is “source” currently a durable registry object, a report-derived concept, or both?

3. What fields currently define a source?

4. Is source label unique?

5. Are multiple rows with the same label expected or accidental?

6. How are root paths stored?

7. How are source types represented?

8. How are cloud/export sources represented today?

9. What records are referenced by provenance?

10. What records are safe or unsafe to delete?

---

### Source Type Taxonomy

Evaluate recommended source types:

```text
local_folder
external_drive
cloud
cloud_export
scan_batch
other
```

Clarify distinction between:

```text
cloud
```

meaning system performs acquisition/download, and:

```text
cloud_export
```

meaning user already exported/downloaded files and system only intakes them.

Determine whether current code already has equivalent type values.

---

### iCloud Source Profile

For iCloud, evaluate future source profile fields:

```text
source_label
source_type = cloud
cloud_provider = icloud
account_username
managed_staging_path
acquisition_method = icloudpd
status
created_at
last_run_at
```

Determine what current code already supports and what is missing.

---

### Credential / Password Handling

Document current iCloud authentication assumptions.

Answer:

1. Does Photo Organizer currently ever collect Apple ID password?

2. Does Photo Organizer currently store Apple ID password?

3. Does Photo Organizer currently store 2FA code?

4. Does Photo Organizer currently store iCloud session cookies/tokens?

5. Where does icloudpd store session data?

6. Can the app detect whether icloudpd session is valid?

7. What errors are returned when authentication is missing/expired?

8. What should the UI show?

9. Should username/account identifier be stored?

10. Should username be masked in normal UI?

Design rule:

```text
No cloud passwords, 2FA codes, session cookies, or auth tokens in Photo Organizer DB for v1.
```

---

### iCloud Staging

Document current staging behavior.

Answer:

1. Where are iCloud downloads staged today?

2. Are folders manually created or system-created?

3. Are staging paths per source/account?

4. How are repeated iCloud acquisition runs handled?

5. Does cleanup remove successfully ingested files?

6. What happens to failed/deferred files?

7. Can cleanup be safely rerun?

8. What reports exist for acquisition and cleanup?

9. What should system-managed staging look like?

Desired direction:

```text
storage/exports/icloud/<source_profile_slug>/
```

or equivalent project-consistent path.

---

### Source Intake

Document current Source Intake behavior.

Answer:

1. How does user choose a source/root today?

2. How does intake scan files?

3. How does intake select files?

4. What does selected/skipped/deferred/failed/remaining/complete mean?

5. What is persisted as intake run history?

6. What is persisted as provenance?

7. How are exact duplicates handled during intake?

8. How does source intake relate to Drop Zone / Vault?

9. What reports are written?

10. What APIs/UI components drive current Source Intake?

---

### Provenance

Document how provenance depends on source records.

Answer:

1. What source identifier does provenance store?

2. Does provenance point to source registry rows?

3. Does provenance store source label, path, or both?

4. What happens if a source is renamed?

5. What happens if a source is deleted?

6. What should happen if a source is archived/inactive?

7. Can old test sources be safely hidden without harming provenance?

Important rule:

```text
Do not hard-delete sources referenced by provenance.
```

---

### Source Archive / Inactive Lifecycle

Evaluate source lifecycle statuses:

```text
active
inactive
archived
test
deprecated
```

Desired behavior:

```text
Active sources show in normal intake dropdowns.
Archived/test/deprecated sources are hidden by default.
Provenance remains explainable.
Deletion is allowed only if no references exist.
```

Determine what the first safe implementation slice should be.

---

### Existing Test Source Clutter

Document current clutter situation.

Answer:

1. Are there many repeated Chuck’s PC source rows?

2. Are there old iCloud test sources?

3. Are there old test staging folders?

4. Which source records appear to be test-only?

5. Which may have provenance references?

6. What cleanup should be deferred until source archive/inactive support exists?

Do not clean anything in 12.61.

---

### Combined Reports

Current UI has separate Recent Intake Reports and Known Sources.

Future desired report view:

```text
Recent Ingestion Runs
```

Possible columns:

```text
Timestamp
Source Profile
Type
Provider
Acquisition count
Scanned
Selected/New
Skipped/Known
Deferred
Failed
Remaining
Complete?
Cleanup status
Details
```

Answer:

1. What reports exist today?

2. Are acquisition and intake runs linked?

3. Can they be linked by run ID, timestamp, source label, staging path, or report path?

4. What would be needed to show a combined row?

5. Should combined report be persisted or computed from existing reports?

6. What details should be visible in Details view?

---

## Design Deliverable

Create:

```text
docs/operations/unified_source_profile_ingestion_recon_12_61.md
```

The document should include:

1. Purpose

2. Current source/intake architecture

3. Current iCloud acquisition architecture

4. Current staging/cleanup behavior

5. Current provenance relationship

6. Current reports/UI behavior

7. Current source clutter/test-source findings

8. Credential/password/session handling findings

9. Proposed Source Profile model

10. Proposed source type taxonomy

11. Proposed iCloud source profile behavior

12. Proposed staging path behavior

13. Proposed unified Run Intake flow

14. Proposed combined report behavior

15. Proposed source archive/inactive lifecycle

16. Risks / things not to break

17. Open questions

18. Recommended implementation sequence

---

## Coder Closeout Response

Create:

```text
docs/prompts/Coder response 12.61.md
```

The closeout should include:

1. Milestone title and date

2. Scope completed

3. Files inspected

4. Current model findings

5. Current intake flow findings

6. Current iCloud flow findings

7. Current staging/cleanup findings

8. Current provenance findings

9. Credential/password/session findings

10. Source clutter findings

11. Proposed Source Profile model

12. Proposed unified workflow

13. Proposed report model

14. Risks and things not to break

15. Recommended next implementation milestones

16. Confirmation that no runtime behavior changed

---

## Recommended Implementation Sequence To Evaluate

Coder should recommend and refine a sequence like:

```text
12.61.1 — Source Profile Model Foundation
12.61.2 — Source Archive / Inactive Lifecycle
12.61.3 — Ingestion Tab Source Profile UI
12.61.4 — Unified Run Intake for Local / External Sources
12.61.5 — iCloud Source Profile + Managed Staging
12.61.6 — Unified iCloud Acquisition + Intake Run
12.61.7 — Combined Ingestion Report View
12.61.8 — Test Source Cleanup / De-Cluttering
```

Coder may suggest a better sequence based on code findings.

---

## Definition of Done

12.61 is complete when:

```text
current source/intake/iCloud/provenance/report behavior is documented
credential/password handling is explicitly documented
Source Profile design options are evaluated
unified Run Intake workflow is defined
staging cleanup behavior is understood
source archive/inactive lifecycle is scoped
combined report direction is defined
risks are clearly listed
next implementation milestones are recommended
no runtime behavior is changed
```

---

## Safety Requirements

For this milestone:

```text
No code behavior changes.
No schema changes.
No source deletion.
No staging cleanup changes.
No credential storage changes.
No UI behavior changes.
No ingestion workflow changes.
No iCloud acquisition changes.
No provenance changes.
```

This is recon only.

If coder discovers a small documentation formatting issue, documentation-only edits are acceptable.

---

## Important Final Note

This milestone should be treated as production-readiness reconnaissance.

Ingestion is a core system. The goal is not to move fast here.

The goal is to avoid breaking:

```text
existing source intake
existing iCloud acquisition
existing provenance
existing reports
existing source review behavior
existing staging cleanup assumptions
```

before we build the unified Source Profile / Ingestion workflow.
