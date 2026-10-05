FILE:
docs/bug_fixes/bug_fix_006_nas_source_namespace_propagation_prompt.md

# Bug Fix 006 — NAS Source Namespace Propagation

## Purpose

Correct the Photo Organizer Linux Source namespace propagation defect exposed by a full server reboot.

After reboot, all three registered NAS Source namespace services failed:

- photo-organizer-source-nas@linux-nas-28494ff87f764f07.service
- photo-organizer-source-nas@linux-nas-94eac331738c49e9.service
- photo-organizer-source-nas@linux-nas-photo-organizer.service

Investigation established that:

1. The initial failure while the Synology systemd automount was unavailable is expected and retriable.
2. Once the NAS becomes available, namespace activation deterministically fails because creation of a NAS child bind produces two real kernel mount objects at the same visible Source namespace slot.
3. The duplicate mounts occur because `/mnt/photo-organizer-sources` remains in the same shared propagation peer group as the server root filesystem.
4. The exact slot validator correctly rejects this topology.
5. The validator must NOT be weakened to accept duplicate rows.

This is a deployment/runtime namespace bug, not a Source identity, NAS availability, CIFS, permissions, or ingestion-engine defect.

The objective is to establish `/mnt/photo-organizer-sources` as an independent shared propagation domain before NAS child Source binds are created, while preserving all existing fail-closed validation.

---

# 1. Repository / Git Preflight

Repository:

/home/chuck/projects/photo-organizer-dev

Expected branch:

feature/windows-ingestion-throughput-hardening

Before implementation:

cd /home/chuck/projects/photo-organizer-dev

git branch --show-current
git status --short
git rev-parse HEAD
git rev-parse '@{upstream}'

Required:

- branch is `feature/windows-ingestion-throughput-hardening`;
- Bug Fixes 004 and 005 are already committed;
- this Bug Fix 006 prompt is committed before implementation;
- working tree is clean;
- HEAD matches upstream.

If any condition is false:

STOP AND REPORT.

Coder must not stage, commit, push, tag, merge, rebase, or reset.

---

# 2. Controlling Investigation Evidence

Use the existing:

`Photo Organizer — NAS Source Namespace Startup Failure Investigation Report`
dated 2026-10-04

as the controlling diagnosis.

Do not repeat broad deployment reconnaissance.

Confirm only the implementation-relevant facts before changing code.

Current proven defect:

- `/` is a shared mount;
- `/mnt/photo-organizer-sources` is currently a self-bind;
- both currently belong to the same shared peer group;
- creating a NAS child bind below `/mnt/photo-organizer-sources` creates two separate kernel mount objects at the same visible NAS slot;
- `/proc/self/mountinfo` proves they are distinct mount IDs;
- `require_slot()` correctly rejects two mount records.

---

# 3. Locked Safety Decisions

The following are NOT negotiable in this bug fix.

Do NOT:

- change `require_slot()` to accept two identical rows;
- weaken exact SOURCE validation;
- weaken FSTYPE validation;
- weaken FSROOT validation;
- weaken MAJ:MIN validation;
- weaken propagation validation;
- hide duplicate mount evidence;
- manually create persistent NAS slot binds as a workaround;
- redesign NAS Source identity;
- redesign NAS registration;
- redesign ingestion;
- alter unrelated Source providers.

Exactly one valid kernel mount object at the NAS slot remains required.

---

# 4. Required Topology

Current defective conceptual topology:

    /                               shared:1
    /mnt/photo-organizer-sources    shared:1

Required conceptual topology:

    /                               shared:<root-peer-group>
    /mnt/photo-organizer-sources    shared:<different-peer-group>

The Source namespace must:

1. be detached from the root filesystem's shared peer group;
2. become shared within its own independent propagation domain;
3. permit intended propagation within the Source namespace;
4. prevent child NAS Source binds from propagating back through the root peer relationship.

The exact implementation may use the appropriate Linux mount propagation operations, but the resulting kernel topology—not merely command syntax—is authoritative.

A likely conceptual sequence is:

    mount --bind "${SOURCE_NAMESPACE}" "${SOURCE_NAMESPACE}"
    detach Source namespace from inherited shared peer group
    make Source namespace recursively/shared as required

Do not assume a particular `mount --make-*` sequence is correct until proven in an isolated namespace.

---

# 5. Isolated Proof Before Live Modification

Before modifying the live Source namespace topology, prove the proposed sequence in a temporary private mount namespace or equivalent controlled isolated environment.

Demonstrate:

1. root filesystem retains its original shared propagation group;
2. temporary Source namespace becomes a different shared peer group;
3. a NAS CIFS bind below that namespace creates exactly one kernel mount at the slot;
4. SOURCE is the expected protected NAS source;
5. FSTYPE is `cifs`;
6. FSROOT is `/`;
7. MAJ:MIN matches the authoritative CIFS mount;
8. propagation is `shared`;
9. `/proc/self/mountinfo` contains exactly one slot mount object;
10. child bind does not propagate back through the root mount peer group.

Capture enough evidence for the closeout.

If the proposed topology cannot satisfy all requirements:

STOP AND REPORT.

---

# 6. Initialization Safety

Do not perform propagation-domain conversion over a populated active Source namespace blindly.

The implementation must establish or verify the Source namespace topology before child Source mounts are created.

Before changing propagation state, ensure the operation is safe relative to currently mounted Source children.

If existing active child mounts make in-place correction unsafe:

STOP AND REPORT with the smallest safe transition procedure.

Do not recursively alter live child propagation without explicit review.

---

# 7. Idempotency

Namespace initialization must remain safe across:

- clean boot;
- service restart;
- already-correct namespace;
- NAS initially unavailable;
- later NAS automount activation;
- repeated namespace preparation.

A namespace already in the correct independent shared propagation domain must not accumulate self-binds or additional mount objects.

Repeated preparation must not create stacked mounts.

---

# 8. Existing TEMPFAIL Behavior

Preserve the current expected boot behavior when the Synology automount is not yet ready.

The existing sequence:

NAS unavailable
→ preparation returns TEMPFAIL / exit 75
→ systemd retries after RestartSec
→ NAS becomes available
→ preparation continues

is acceptable.

Do not redesign systemd ordering or NAS automount dependencies unless post-fix evidence demonstrates a separate defect.

The bug being fixed is the deterministic hard failure after NAS availability.

---

# 9. Exact Slot Validation

Preserve fail-closed `require_slot()` behavior.

For a valid NAS slot require exactly one mount record with:

- TARGET == expected NAS slot;
- SOURCE == protected NAS source;
- FSTYPE == `cifs`;
- FSROOT == `/`;
- MAJ:MIN == authoritative NAS CIFS mount;
- PROPAGATION == `shared`.

Duplicate or conflicting kernel mount evidence must continue to fail.

---

# 10. Focused Tests

Add or adjust deterministic tests for at least:

- Source namespace independent peer-group requirement;
- exactly one NAS slot mount;
- expected CIFS SOURCE;
- FSTYPE == `cifs`;
- FSROOT == `/`;
- matching MAJ:MIN;
- PROPAGATION == `shared`;
- rejection of duplicate slot mounts;
- rejection of conflicting slot evidence;
- already-correct namespace idempotency;
- retryable NAS-unavailable state remains TEMPFAIL;
- no weakening of existing namespace identity checks.

Use the smallest appropriate script/unit/integration test surface.

Do not create tests that merely mock away the propagation invariant.

---

# 11. Host Script / Installed Runtime Boundary

Identify:

- repository source file(s);
- root-owned installed host file(s);
- relevant systemd units;
- exact deployment/install mechanism;
- rollback copy requirement.

Repository implementation and root-owned host activation are separate actions.

Do not overwrite root-owned runtime files without Product Owner authorization.

---

# 12. Pre-Deployment Gate

After implementation and automated tests, but BEFORE modifying root-owned live scripts/services:

STOP AND REPORT:

STATUS: READY FOR BUG FIX 006 HOST DEPLOYMENT

Include:

Repository files changed:
Installed host files requiring replacement:
Systemd units affected:
Current namespace topology:
Expected post-fix topology:
Automated tests:
Rollback files/path:
Exact privileged actions required:
Expected service behavior:
Expected NAS automount behavior:
Risk if deployment fails:

Wait for Product Owner authorization.

---

# 13. Controlled Host Deployment

After authorization:

- install only the reviewed namespace/runtime files;
- preserve rollback copies;
- do not use unrelated package/system upgrades;
- do not change NAS mount definitions unless explicitly required;
- do not change Source identities;
- do not change registered NAS records;
- do not alter database Source/Profile state.

Do not use `docker compose down`.

This bug concerns host Source namespace activation.

---

# 14. Pre-Reboot Live Validation

Before reboot, validate all registered NAS namespace units individually.

Confirm:

- authoritative NAS automount is healthy;
- Source namespace base is valid;
- Source namespace peer group differs from `/`;
- each registered NAS unit reaches active state;
- each NAS slot has exactly one kernel mount ID;
- SOURCE/FSTYPE/FSROOT/MAJ:MIN/PROPAGATION all match;
- no stacked/duplicate mount exists;
- Photo Organizer Development can access each intended Source;
- exact validator passes without exceptions or weakened rules.

If any slot produces duplicate mount evidence:

STOP AND REPORT.

Do not proceed to reboot validation.

---

# 15. Full Server Reboot Gate

A full reboot is required for final acceptance because reboot exposed the defect.

Before reboot:

STOP AND REPORT:

STATUS: READY FOR BUG FIX 006 REBOOT VALIDATION

Include:

All pre-reboot NAS unit states:
Current root peer group:
Current Source namespace peer group:
NAS slot mount IDs:
Rollback readiness:
Expected reboot sequence:
Expected transient TEMPFAIL behavior, if any:
Expected final service state:

Wait for Product Owner authorization before reboot.

---

# 16. Post-Reboot Validation

After authorized reboot verify:

1. server returns normally;
2. authoritative Synology automount activates successfully;
3. `/` remains in its normal shared peer group;
4. `/mnt/photo-organizer-sources` is shared but in a different peer group;
5. all registered NAS Source namespace services become active;
6. an initial NAS-not-ready TEMPFAIL may occur but subsequently recovers;
7. every registered NAS slot contains exactly one kernel mount object;
8. no duplicate/stacked Source mount exists;
9. every slot retains correct SOURCE;
10. FSTYPE remains `cifs`;
11. FSROOT remains `/`;
12. MAJ:MIN matches the authoritative NAS CIFS mount;
13. propagation remains `shared`;
14. Photo Organizer Development NAS Source access works;
15. existing Source identity/Profile records are unchanged;
16. Development Operator tunnel/status refresh works after normal server recovery.

Use `/proc/self/mountinfo` or equivalent kernel evidence where required; do not rely only on formatted duplicate-suppressing output.

---

# 17. Regression Boundary

Do not modify or regress:

- Windows Helper 0.5.4 behavior;
- Windows Local/External/Removable ingestion;
- iCloud;
- Linux Local Source identity;
- NAS registration UX from Bug Fixes 004/005;
- NAS subfolder scope protections;
- Vault/Asset/Provenance behavior;
- Source Intake behavior;
- Test or Production runtime.

Only run broader application regression if the changed repository surface warrants it.

---

# 18. Operational Follow-Up

After server/runtime health is restored, re-test the Development Operator tunnel/status path that timed out during reboot recovery.

Treat that timeout as secondary unless it persists once the server and Source namespace services are healthy.

If it persists independently:

document it separately rather than widening this bug fix automatically.

---

# 19. Git / Repository Hygiene

No temporary investigation artifacts in the repository.

Temporary mount traces, mountinfo captures, journal extracts, or diagnostics belong outside the repository unless intentionally summarized in the closeout.

Coder performs no:

- stage;
- commit;
- push;
- tag;
- merge;
- rebase;
- reset.

Product Owner owns Git mutations.

---

# 20. Escalation Conditions

STOP AND REPORT:

STATUS: BUG FIX 006 ESCALATION REQUIRED

if:

- namespace isolation cannot produce a distinct shared peer group;
- exactly one NAS slot mount cannot be achieved;
- fixing propagation requires weakening the validator;
- fixing propagation requires changing Source identity;
- active child mounts make safe transition ambiguous;
- systemd boot semantics require broader redesign;
- NAS automount definitions must be changed;
- the proposed sequence affects unrelated host mount propagation;
- Test/Production modifications are required.

Report:

Observed topology:
Expected topology:
Exact failing invariant:
Kernel mount evidence:
Why current approach is unsafe:
Smallest safe alternative:
Rollback status:
Recommended Product Owner decision:

---

# 21. Required Closeout

Create exactly:

docs/bug_fixes/bug_fix_006_nas_source_namespace_propagation_closeout.md

Document:

## Summary

## Original Failure

## Root Cause

## Safety Invariants Preserved

## Repository Changes

## Namespace Initialization Correction

## Isolated Propagation Proof

## Exact Slot Validation

## Focused Tests

## Host Deployment

## Rollback State

## Pre-Reboot Validation

## Full Reboot Validation

## Post-Reboot Mount Topology

## Registered NAS Unit Results

## Photo Organizer Runtime Validation

## Development Operator Validation

## Exact Files Changed

## Deviations

## Known Limitations

## Git Status

## Final Recommendation

The closeout must explicitly record:

- root shared peer-group ID after reboot;
- Source namespace shared peer-group ID after reboot;
- proof they differ;
- each registered NAS service state;
- each registered NAS slot mount count;
- each slot mount ID;
- SOURCE;
- FSTYPE;
- FSROOT;
- MAJ:MIN;
- propagation;
- whether initial TEMPFAIL occurred;
- whether automatic retry recovered;
- whether any duplicate/stacked mounts remain.

End with exactly one:

BUG FIX 006 COMPLETE

or:

PRODUCT OWNER VALIDATION REQUIRED

or:

BUG FIX 006 NOT COMPLETE

---

# Definition of Done

Bug Fix 006 is complete when:

- the Source namespace no longer shares the root filesystem's propagation peer group;
- the Source namespace remains appropriately shared within its own independent domain;
- creating a NAS child Source bind produces exactly one kernel mount object;
- exact fail-closed slot validation remains unchanged in strength;
- duplicate/conflicting mount evidence remains rejected;
- all three registered NAS Source units activate correctly;
- transient NAS automount unavailability remains safely retryable;
- a full server reboot proves automatic recovery;
- every post-reboot NAS slot has exactly one valid mount;
- no stacked/duplicate Source mounts remain;
- Photo Organizer Development can access registered NAS Sources;
- Source identities and Profiles remain unchanged;
- the Development Operator tunnel/status works after normal recovery or is separately documented if independently defective;
- rollback evidence is preserved;
- no unrelated provider/runtime architecture is changed;
- coder performs no Git write operation;
- closeout contains complete kernel/topology and reboot evidence.
