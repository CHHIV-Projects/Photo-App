# iCloud Source Model and Acquisition Rules (Milestone 12.44.0)

Date: 2026-05-12  
Status: Approved and Implemented

---

## Overview

This document establishes the operational model for iCloud sources and acquisition completeness. It clarifies the one-source-per-account rule, the semantics of `recent_count` checks, and prerequisites for safe staging file cleanup.

---

## 1. Definition of iCloud Source

**An iCloud source is a registered Source Registry entry representing the local staging folder for one iCloud account/library.**

### Source Structure

Every iCloud source must have:

| Field | Value | Purpose |
|---|---|---|
| source_label | stable, human-readable name | Identify the source |
| source_type | cloud_export | Category for filtering |
| source_root_path | storage/exports/icloud/<source_label>/ | Staging folder location |
| account_username | (optional, non-secret) | Associate with iCloud account for safety |

### Production Naming Pattern

Recommended:

```text
<person_or_account>_icloudpd
```

Examples:

```text
chuck_icloudpd
family_icloudpd
spouse_icloudpd
```

### What account_username Is and Is Not

**Is:**
- The Apple ID username/email normally used for this source (for example: chuck@icloud.com)
- Non-secret reference data
- Used to warn operators if run-time username differs from source association
- Aids in supporting future multi-account workflows

**Is NOT:**
- Password
- 2FA code
- Session token
- Credential of any kind

---

## 2. One Source Per iCloud Account Rule

### Default Production Rule

```text
Use one stable iCloud source per iCloud account/library.
```

### Rationale

- Avoids source label confusion
- Preserves skip-known provenance behavior across runs
- Keeps source-level state consistent
- Simplifies cleanup and operator workflow
- Prevents accidental duplicates

### Multiple Sources for Same Account — Allowed Only For

- Testing
- Controlled experiments
- One-time migration or backfill
- Album-specific diagnostics
- Debugging specific scenarios

**Multiple sources for the same account should not be normal production practice.**

### Test Source Identification

Test-only labels typically contain patterns like:

```text
test
trial
adapter
backend_test
12_37
12_38
direct_new_asset
```

These should eventually be archived or marked inactive (future work); do not delete them yet.

---

## 3. Apple ID Username Association

### Why This Matters

iCloud Acquisition requires an Apple ID username at run time. Associating it with the source:

- Prevents wrong-account-on-wrong-source errors
- Makes the source identity clearer
- Supports future multi-account safety features
- Lets Admin prefill the username field safely

### Source-Level Username Storage

Starting in 12.44.0:

- Each iCloud source can store an associated `account_username` (non-secret)
- This is set when the source is created or updated
- The Admin UI prefills the username field from the source's account_username
- The operator can override the username at run time (with a warning if different)

### Prefill and Override Behavior

| Scenario | Behavior |
|---|---|
| Source has account_username | UI prefills username field; operator may override |
| Source has no account_username | UI username field is empty; operator enters manually |
| Operator enters different username | Warning shown: "This username differs from the account associated with the selected source." |
| Override is allowed | Operator may proceed; no hard block (for debug/test scenarios) |

### Password and Session Policy

Photo Organizer does NOT store:

```text
Apple ID password
2FA codes
Session cookies
Authentication tokens
```

Password and 2FA authentication are handled by icloudpd outside Photo Organizer.

---

## 4. Source Creation Workflow

### How to Create an iCloud Source

1. Open Admin UI
2. Go to **Source Registry** section (separate from iCloud Acquisition)
3. Click **Register New Source**
4. Fill in:
   - **Source Label** — use pattern `<account>_icloudpd`
   - **Source Type** — select `cloud_export`
   - **Source Root Path** — `storage/exports/icloud/<source_label>/`
   - **Account Username** — (optional) the Apple ID email for this source
5. Click **Create Source**

### Using the Source for Acquisition

After creating the source:

1. Go to **iCloud Acquisition** section
2. Select the source from the dropdown
3. Enter Apple ID username (prefilled if source has account_username)
4. Set Recent Count
5. Click **Run iCloud Acquisition**

### If No Source Is Registered

iCloud Acquisition shows:

```text
No cloud_export source registered. Create one in Source Registry first.
```

Do not auto-create sources silently.

---

## 5. Acquisition Recent Count Semantics

### What `recent_count` Means

```text
Acquire/check the most recent N iCloud items
```

### What It Does NOT Mean

It does NOT mean:

```text
All unacquired iCloud items have been found.
The system has scanned the full iCloud library.
The library is fully caught up.
Entire library acquisition is complete.
```

### Practical Interpretation

| recent_count | Use Case | Risk |
|---|---|---|
| 25 | Small, expected updates | May miss items if >25 added since last run |
| 100 | Catch-up after a few days | More reliable but still a window, not full |
| 250–500 | Catch-up after travel or long break | Safer but longer to run |

**None of these values guarantee full-library completeness.**

### UI Wording

The Admin UI displays:

```text
This run checked the most recent N iCloud item(s). 
It does not prove the entire iCloud library is caught up.
```

---

## 6. Acquisition Completeness Limitations

### Current State

Acquisition uses icloudpd with `--recent N`:

- Does not maintain a checkpoint across runs
- Does not detect whether item N+1 exists and contains unacquired files
- Relies on operator judgment for `recent_count` sizing
- Does not auto-detect "caught up" state

### Completeness Status Values

Current status shown after acquisition completes:

```text
Completeness: recent window checked; full-library completeness not determined.
```

Do not claim:

```text
✗ "Caught up"
✗ "All files acquired"
✗ "Library fully scanned"
```

---

## 7. Recent Count Recommendations

### Small Regular Updates

```text
recent_count = 25
```

Use when:

- Only a few photos/videos expected since last run
- Running frequently (daily, weekly)

### Safe Catch-Up Check

```text
recent_count = 100
```

Use when:

- Not sure how many recent files were added
- Running after a few days of no acquisitions

### Larger Recent Window (Travel/Backlog)

```text
recent_count = 250–500
```

Use when:

- Catching up after travel
- Many photos/videos expected
- Long interval since last acquisition

**Warn:** Larger windows take longer but are safer for catching recent additions.

---

## 8. Until-Found / Checkpoint Strategy (Deferred)

### Current Limitation

The current acquisition flow cannot determine "caught up" state because:

- It checks only the recent N items
- It cannot know whether items N+1 contain unacquired files
- No checkpoint persists across runs

### Future Solution

A future milestone (**PX-ICLOUD-004**) will evaluate:

- icloudpd `--until-found` flag support
- Defining "until-found" behavior and thresholds
- Deciding whether "known" means: staged file, source provenance, or cloud asset ID
- Whether acquisition can reliably report "caught up"
- Safe-stopping criteria to avoid full-library scans

---

## 9. Test Source Policy

### Current Test Sources

Multiple test-only iCloud sources exist from development:

```text
chuck_icloudpd_backend_test
chuck_icloudpd_test
chuck_icloud_direct_adapter_test
chuck_icloud_direct_adapter_trial_12_36
chuck_icloud_direct_new_asset_test_12_37
chuck_icloud_direct_new_asset_test_12_37_1
chuck_icloud_direct_new_asset_test_12_37_album
chuck_icloud_direct_test
```

### Do Not Delete Yet

These sources remain in the database and storage for:

- Provenance history
- Debugging reference
- Future transition/archival

### Do Not Use for Production

Sources with test-like names should not be used for production photo organization.

### Future: Source Archive Support

A future milestone will add:

```text
Source Registry Archive / Inactive Source Support
```

This will let operators mark sources as archived without hard deletion.

---

## 10. Cleanup Readiness Rules for Milestone 12.44.1

Before any iCloud staging files are deleted, the following conditions must be confirmed:

| Condition | Reason |
|---|---|
| Source is registered in IngestionSource table | Avoids deleting files from unregistered sources |
| Source root path is canonical/normalized | Prevents double-deletion or missing paths |
| File is under the source root directory | Ensures we delete only the intended staging files |
| File has matching Provenance record | Confirms file was actually ingested |
| Provenance asset exists in Asset table | Confirms file is tracked in the system |
| Vault copy / storage exists | Prevents deleting if backup/archive is missing |
| File was not failed/rejected/deferred | Only delete files successfully processed |
| Source Intake reported success for this file | Only delete after confirmed staging-to-import |

**Deletion must be explicit and auditable. No silent cleanup.**

---

## 11. Password and Session Security Policy

### What Photo Organizer Does

- Delegates authentication to icloudpd
- Uses icloudpd's built-in session management (cookies stored in `.tools/icloud_session/`)
- Does NOT capture or store passwords

### How to Re-Authenticate

If Apple ID authentication expires or fails:

```bash
.tools/icloudpd/Scripts/icloudpd.exe \
  --username your@icloud.com \
  --cookie-directory .tools/icloud_session \
  --auth-only
```

This updates the session without Photo Organizer involvement.

### Operator Responsibility

Ensure:

- iCloud account has "Access iCloud Data on the Web" enabled
- iCloud account has Advanced Data Protection disabled (if required by icloudpd)
- Session cookie directory is kept private and not committed to version control

---

## 12. Deferred Work

The following remain explicitly deferred:

- Deleting staging files (12.44.1)
- Deleting or hard-archiving sources
- Implementing `--until-found` checkpoint logic
- Multi-account session management
- Password storage (forbidden)
- Scheduled acquisition
- Automatic Source Intake
- Automatic post-intake enrichment
- NAS deployment

---

## Summary: The Model

```text
One iCloud account/library
    ↓
One stable iCloud source (registered in Source Registry)
    ↓
Source stores optional account_username
    ↓
iCloud Acquisition downloads to staging folder
  (recent_count = N means "check most recent N items")
    ↓
Operator reviews staged files
    ↓
Source Intake ingests from staging folder
    ↓
Provenance records files as sourced
    ↓
[Future 12.44.1] Clean up staging files only if safe prerequisites are met
```

---

## Parking Lot Items

### PX-ICLOUD-004 — iCloud Acquisition Until-Found / Checkpoint Strategy

**Status:** Deferred from 12.44.0; future milestone pending evaluation

**Objective:** Determine whether Photo Organizer can reliably report "caught up" or "acquired all recent items" without doing expensive full-library scans.

**Acceptance Criteria:**

- [ ] Evaluate icloudpd `--until-found` behavior and version support
- [ ] Define "consecutive known items" threshold for stopping
- [ ] Decide whether "known" means: staged file, provenance, or cloud asset ID
- [ ] Determine whether Photo Organizer can ask icloudpd for totals/progress
- [ ] Design operator-facing completeness reporting
- [ ] Ensure no full-library scans occur unintentionally
- [ ] Test checkpoint persistence across multiple runs

**Open Questions:**

- Does icloudpd `--until-found` block when items are missing, or exit when threshold is reached?
- Can icloudpd report remote total counts vs. acquired count?
- Is Photo Organizer responsible for checkpoint persistence, or icloudpd?
- How should "caught up" be reported to operator (percentage, flag, warning)?

---

## Document History

| Date | Change | Author |
|---|---|---|
| 2026-05-12 | Initial 12.44.0 rules document | Coder Agent |

---

## Appendix: Quick Reference

### Source Registration

```bash
# Create new iCloud source
Admin UI → Source Registry → Register
  Label: chuck_icloudpd
  Type: cloud_export
  Path: storage/exports/icloud/chuck_icloudpd/
  Account: chuck@icloud.com (optional)
```

### Acquisition Run

```bash
# Run acquisition
Admin UI → iCloud Acquisition
  Source: chuck_icloudpd
  Username: chuck@icloud.com (prefilled from source)
  Recent Count: 25
  Click "Run iCloud Acquisition"
```

### Check Results

```text
Downloaded: [count]
Skipped existing: [count]
Failed: [count]
Files currently staged: [count]
Completeness: recent window checked; full-library completeness not determined.
```

### Next: Source Intake

```bash
Admin UI → Source Intake
  Source: chuck_icloudpd (auto-filled from acquisition handoff)
  Limit: [file_inventory_count] (auto-filled)
  Click "Run Source Intake"
```
