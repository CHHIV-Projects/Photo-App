# Bug Fix 006 — NAS Source Namespace Propagation Closeout

## Summary

Repository implementation, isolated kernel proof, controlled host deployment, Development backend restart, pre-reboot validation, and the Product Owner-authorized full server reboot validation are complete. The corrected namespace topology survived reboot, all three NAS units recovered automatically after the accepted initial TEMPFAIL condition, every NAS slot remains exact and unstacked, and Development regained correct propagation, readability, health, and Source readiness without manual container intervention.

## Original Failure

After a full server reboot, all three registered NAS Source namespace services first encountered the accepted retryable NAS-not-ready condition and later failed deterministically with `Created NAS namespace slot failed exact validation.`

Affected units:

- `photo-organizer-source-nas@linux-nas-28494ff87f764f07.service`
- `photo-organizer-source-nas@linux-nas-94eac331738c49e9.service`
- `photo-organizer-source-nas@linux-nas-photo-organizer.service`

## Root Cause

The root filesystem and `/mnt/photo-organizer-sources` are both members of shared propagation peer group `1`. A NAS child bind under that topology propagates through the inherited root peer relationship and produces two distinct kernel mount objects at the same visible Source slot. The exact slot validator correctly rejects that evidence.

## Safety Invariants Preserved

- `require_slot()` remains fail-closed and was not weakened.
- Exactly one NAS slot mount record remains required.
- Exact SOURCE, `cifs` FSTYPE, `/` FSROOT, authoritative MAJ:MIN, and `shared` propagation checks remain unchanged.
- Duplicate and conflicting mount evidence remains rejected.
- Existing TEMPFAIL/exit `75` behavior remains unchanged.
- NAS identity, registration, Source/Profile state, ingestion, Windows Helper, iCloud, and unrelated providers are unchanged.
- Conversion is refused when any child mount exists beneath the Source namespace.
- Conversion uses non-recursive propagation operations and does not recursively alter child mounts.

## Repository Changes

`scripts/operator/linux/prepare_source_namespace.sh` now:

- reads exact root and Source namespace mount IDs and peer-group IDs from `/proc/self/mountinfo`;
- requires `/` to have one unambiguous shared propagation record;
- distinguishes inherited shared, private/interrupted, and independent shared Source topology;
- treats an already-independent shared Source namespace as a no-op;
- counts all child mounts beneath the Source namespace before conversion;
- refuses conversion if the child count is nonzero;
- detaches the Source namespace with `mount --make-private`;
- establishes a new independent group with `mount --make-shared`;
- validates the resulting independent shared topology before continuing.

`backend/tests/test_prepare_source_namespace.py` adds deterministic coverage for independent peer groups, inherited-group rejection, private/other propagation rejection, safe conversion ordering, active-child refusal, mountinfo authority, non-recursive operation, and already-correct idempotency.

## Namespace Initialization Correction

For a new self-bind or an existing safe namespace requiring correction, the implemented sequence is:

1. validate exact namespace filesystem identity;
2. obtain root and Source mount/peer IDs from `/proc/self/mountinfo`;
3. prove there are zero child Source mounts;
4. run `mount --make-private /mnt/photo-organizer-sources`;
5. run `mount --make-shared /mnt/photo-organizer-sources`;
6. re-read mountinfo and require a shared Source peer group different from the root peer group.

An already-correct independent shared namespace performs no mount operation. A private namespace left by an interrupted safe transition can complete the shared step on retry, provided it has no child mounts.

## Isolated Propagation Proof

The proof ran in a disposable privileged container mount namespace. The live read-only `Photos` CIFS authority was exposed to the isolated namespace; no host mount operation was performed.

The synthetic defective starting state was reproduced:

- synthetic root mount ID: `349`;
- synthetic Source mount ID: `596`;
- shared peer group before correction: `937` for both.

After non-recursive private-then-shared conversion:

- synthetic root peer group: `937`;
- synthetic Source peer group: `948`;
- proof that groups differ: `937 != 948`;
- root-peer child slot count after the NAS bind: `0`.

The isolated NAS slot evidence was:

- slot count: `1`;
- slot mount ID: `617`;
- SOURCE: `//192.168.1.171/Photos`;
- FSTYPE: `cifs`;
- FSROOT: `/`;
- slot MAJ:MIN: `0:109`;
- authoritative CIFS MAJ:MIN: `0:109`;
- propagation: `shared:952`.

The proof result was `ISOLATED_PROPAGATION_PROOF=PASS`.

Host topology was checked before and after the isolated proof and remained unchanged:

- host root: mount ID `30`, `shared:1`;
- host Source namespace: mount ID `51`, `shared:1`;
- result: `HOST_TOPOLOGY_UNCHANGED=PASS`.

## Exact Slot Validation

`require_slot()` was not changed. Existing tests continue to accept one exact registered slot and reject duplicate rows, wrong SOURCE, wrong FSTYPE, wrong FSROOT/shape, wrong MAJ:MIN, and non-shared propagation.

## Focused Tests

Seventy-three focused tests passed in the application container:

- namespace script tests: `17`;
- namespace systemd contract tests: `7`;
- Linux Source broker tests: `27`;
- Linux mounted Source service tests: `12`;
- NAS registration tests: `10`.

`bash -n` and `git diff --check` also passed. The SQLAlchemy identity-map warnings emitted by two existing service tests are pre-existing warnings and did not cause failures.

## Host Deployment

Performed under explicit Product Owner authorization.

Only this installed file was replaced:

`/usr/local/lib/photo-organizer/prepare-source-namespace.sh`

Installed SHA-256:

`6182aedab97903ae000c02bcf02f3cf87223e8a20acca252506a851d018ed91a`

The installed file is `root:root`, mode `0755`, and matches the reviewed repository replacement. No systemd unit content changed. The base namespace unit and the three authorized NAS instance units were restarted individually. No daemon unit replacement, database mutation, container recreation, or `docker compose down` occurred. One later full server reboot was performed only after separate Product Owner authorization.

## Rollback State

The currently installed script was copied before deployment to:

`/home/chuck/.local/state/photo-organizer/bug_fix_006/rollback-XrJEUxm7/prepare-source-namespace.sh`

Rollback SHA-256:

`7593e86d0ce81c049c46dfdbb2672e80f04efc1f4ab73eb69246f3584efd64c0`

The rollback copy remains unchanged and intentionally differs from the currently installed replacement. The reviewed repository replacement SHA-256 is:

`6182aedab97903ae000c02bcf02f3cf87223e8a20acca252506a851d018ed91a`

## Pre-Reboot Validation

Host namespace validation passed:

- root mount ID: `30`;
- root shared peer group: `1`;
- Source namespace mount ID: `51`;
- Source namespace shared peer group: `356`;
- peer groups differ: `1 != 356`;
- all three NAS units are active;
- every slot has exactly one exact CIFS mount;
- no duplicate or stacked NAS slot mounts remain.

The authorized ordinary Development backend restart rebuilt its existing `rslave` bind against the corrected Source namespace. The backend returned to healthy state without container recreation. Runtime mount visibility, readability, application health, and read-only identity probes all pass. Pre-reboot validation is complete.

## Full Reboot Validation

The Product Owner authorized one controlled full server reboot. The pre-reboot boot ID was `4bf20884-7696-40cc-8ab7-4f7e3e6c3a11`; the post-reboot boot ID is `33446b98-e211-4542-b027-12803b82807a`, proving that the reboot occurred.

The server returned normally as `henderson-server1`. SSH is active and listening on IPv4 and IPv6 port `22`. The expected Development containers returned to running/healthy state through normal boot recovery. The authoritative Synology CIFS automounts also returned. No post-reboot container restart, recreation, `docker compose down`, systemd-unit modification, or Source/Profile/database mutation was performed.

All three registered NAS units initially encountered `NAS automount did not become ready`, exited with the preserved status `75/TEMPFAIL`, and were scheduled for systemd restart. Restart counter `1` then recovered each unit automatically to the exact mounted state. This is the intended and accepted boot-order behavior.

## Post-Reboot Mount Topology

Post-reboot kernel evidence from `/proc/self/mountinfo` is:

- root `/`: mount ID `30`, shared peer group `1`;
- `/mnt/photo-organizer-sources`: mount ID `560`, shared peer group `440`;
- root remains shared;
- Source namespace remains shared;
- the propagation domains are independent: `1 != 440`;
- no unexpected child Source mount was present during base namespace initialization;
- all final registered NAS slots contain exactly one mount object.

## Registered NAS Unit Results

Final post-reboot state:

- `linux-nas-28494ff87f764f07`: initial TEMPFAIL `yes`; automatic retry recovery `yes`; final state `active`; slot count `1`; mount ID `2274`; SOURCE `//192.168.1.171/ExternalDrives`; FSTYPE `cifs`; FSROOT `/`; MAJ:MIN `0:111`; authoritative MAJ:MIN `0:111`; propagation `shared:1438`.
- `linux-nas-94eac331738c49e9`: initial TEMPFAIL `yes`; automatic retry recovery `yes`; final state `active`; slot count `1`; mount ID `2390`; SOURCE `//192.168.1.171/Photos`; FSTYPE `cifs`; FSROOT `/`; MAJ:MIN `0:113`; authoritative MAJ:MIN `0:113`; propagation `shared:1490`.
- `linux-nas-photo-organizer`: initial TEMPFAIL `yes`; automatic retry recovery `yes`; final state `active`; slot count `1`; mount ID `2362`; SOURCE `//192.168.1.171/PhotoOrganizer`; FSTYPE `cifs`; FSROOT `/`; MAJ:MIN `0:112`; authoritative MAJ:MIN `0:112`; propagation `shared:1457`.

Every slot has exactly one mount ID, every MAJ:MIN matches its authoritative CIFS automount, and no slot contains duplicate or stacked mount evidence.

## Photo Organizer Runtime Validation

The Product Owner authorized an ordinary restart of only the existing Development backend container. No force recreation or `docker compose down` occurred. The backend returned to `healthy` state.

Backend mount evidence after restart:

- `/app/sources`: mount ID `1860`; read-only; ext4 FSROOT `/mnt/photo-organizer-sources`; propagation `master:356`, proving attachment to the corrected Source namespace rather than former `master:1`.
- ExternalDrives: mount ID `1886`; SOURCE `//192.168.1.171/ExternalDrives`; FSTYPE `cifs`; FSROOT `/`; MAJ:MIN `0:101`; propagation `master:1330`.
- Photos: mount ID `1923`; SOURCE `//192.168.1.171/Photos`; FSTYPE `cifs`; FSROOT `/`; MAJ:MIN `0:109`; propagation `master:1445`.
- PhotoOrganizer: mount ID `1940`; SOURCE `//192.168.1.171/PhotoOrganizer`; FSTYPE `cifs`; FSROOT `/`; MAJ:MIN `0:108`; propagation `master:1393`.

Readability was verified as the non-root `photo-organizer` backend service account:

- ExternalDrives: `3/3` top-level entries readable;
- Photos: `6/6` top-level entries readable;
- PhotoOrganizer: `5/5` top-level entries readable;
- expected `Photos/Camera imports` subfolder: present and readable.

All three browser-safe location summaries report `available`. Read-only Source identity probes for all three registered NAS locations returned `safe_to_run=True` with zero blockers. The backend health endpoint reports application, database, Redis, and storage status `ok`.

No Source identities, registered NAS records, or database Source/Profile state were changed.

Post-reboot Development recovery also passed without intervention:

- backend state and Docker health: `running` / `healthy`;
- frontend, helper ingress, PostgreSQL, and Redis: `running` / `healthy`;
- API health: application, database, Redis, and storage `ok`;
- frontend HTTP status: `200`;
- `/app/sources`: mount ID `1675`, FSROOT `/mnt/photo-organizer-sources`, propagation `master:440`;
- ExternalDrives child: mount ID `2358`, SOURCE `//192.168.1.171/ExternalDrives`, FSTYPE `cifs`, FSROOT `/`, MAJ:MIN `0:111`, propagation `master:1438`;
- Photos child: mount ID `2395`, SOURCE `//192.168.1.171/Photos`, FSTYPE `cifs`, FSROOT `/`, MAJ:MIN `0:113`, propagation `master:1490`;
- PhotoOrganizer child: mount ID `2367`, SOURCE `//192.168.1.171/PhotoOrganizer`, FSTYPE `cifs`, FSROOT `/`, MAJ:MIN `0:112`, propagation `master:1457`.

The backend is attached to the corrected Source namespace peer group `440`, not root peer group `1`. All child identities are current rather than stale. Readability as non-root `uid=999(photo-organizer)` passed for `3/3` ExternalDrives entries, `6/6` Photos entries, and `5/5` PhotoOrganizer entries; `Photos/Camera imports` is also present and readable.

All three NAS Source summaries report `available`. All three read-only Source probes return `safe_to_run=True` with zero blockers. The Source/Profile identity baseline remained count `19` with SHA-256 `52fec0509871a217bb47b8d19e24eaaee048674ea0731c1f57ac6758d7f181df`. The Endpoint baseline remained `8|3971a5e74a07836cf514dbc0203f3f25`. Both exactly match their pre-reboot values, confirming that reboot recovery caused no Source/Profile/Endpoint identity mutation.

## Development Operator Validation

The server-side Development Operator `health` action passed after reboot: backend health and frontend endpoints both returned HTTP `200`. SSH recovered normally, and the user reconnected through VS Code after the reboot.

The Operator's static `self-test` and privileged `status` path are documented separately from Bug Fix 006:

- `self-test` reports `Unexpected Development service set` because its allowlist still expects only `backend`, `frontend`, `postgres`, and `redis`, while the current valid Compose configuration also contains `helper-ingress`;
- the noninteractive validation session cannot satisfy the Operator's intentional interactive `sudo` boundary for its privileged `status` action;
- direct read-only Compose evidence confirms all five current Development services are running and healthy.

This is a stale Development Operator contract/automation issue, not a Source namespace propagation failure. It did not prevent SSH/tunnel recovery, application availability, backend propagation, or NAS Source access, and Bug Fix 006 was not widened to alter the Operator.

## Exact Files Changed

- `scripts/operator/linux/prepare_source_namespace.sh`
- `backend/tests/test_prepare_source_namespace.py`
- `docs/bug_fixes/bug_fix_006_nas_source_namespace_propagation_closeout.md`

## Deviations

The external investigation report was not a repository artifact. By Product Owner direction, the diagnosis and evidence summarized in the committed Bug Fix 006 prompt were treated as controlling evidence.

The isolated proof used a disposable privileged container mount namespace because noninteractive host sudo and unprivileged user mount namespaces were unavailable. It used the real read-only `Photos` CIFS authority and verified that host topology was unchanged before and after the proof.

## Known Limitations

- The Windows graphical Operator itself was not remotely driven by the Linux validation agent. Server-side SSH recovery, endpoint access, and the Operator health action passed; the independent stale service-allowlist issue is recorded above.
- The initial NAS TEMPFAIL window remains expected during boot while authoritative automounts become ready. Existing automatic retry recovered all three registrations on the first scheduled retry.

## Git Status

The Product Owner-owned branch remains `feature/windows-ingestion-throughput-hardening`. The coder did not stage, commit, push, tag, merge, rebase, or reset. Final working-tree status:

- modified: `backend/tests/test_prepare_source_namespace.py`;
- modified: `scripts/operator/linux/prepare_source_namespace.sh`;
- untracked: `docs/bug_fixes/bug_fix_006_nas_source_namespace_propagation_closeout.md`.

## Final Recommendation

Bug Fix 006 satisfies its implementation and validation objectives. The independent shared Source namespace survived a full reboot, preserved fail-closed exact-slot validation, recovered all NAS registrations through the designed TEMPFAIL retry path, and propagated correct readable NAS mounts into the normally recovered Development backend. The change is ready for Product Owner commit. Track the stale Development Operator service allowlist separately if full `self-test` parity with the current five-service Compose configuration is desired.

BUG FIX 006 COMPLETE
