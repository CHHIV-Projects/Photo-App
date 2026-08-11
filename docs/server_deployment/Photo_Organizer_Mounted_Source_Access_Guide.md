# Photo Organizer Mounted Source Access Guide

## Purpose

The Mounted Source Provider is the Linux implementation for media already
attached to, or mounted by, the Photo Organizer server. Its current repository
scope is limited to:

- one approved server-local location;
- the canonical NAS share `//192.168.1.171/PhotoOrganizer`.

Windows-connected External, Removable, and Optical media are not Mounted
Sources. They remain assigned to the future Windows Source Helper Provider.
iCloud remains an independent Cloud Provider.

## Authority boundaries

The provider preserves three distinct concepts:

```text
durable Source Endpoint/Profile identity
!= host Observed Path
!= container Runtime Root
```

For a Mounted Profile, `IngestionSource.source_root_path` is the
broker-verified host-side root, including its approved contained relative
folder. Readiness, Source Selection, and Run Ingestion derive and revalidate the
current container Runtime Root. They do not rewrite the Profile root.
Source Intake run evidence and provenance record the selected Runtime Root and
Source-relative path; the runtime path does not replace durable Endpoint/Profile
identity or the persisted host root.

Mounted access ends at the existing Source Intake seam. Source Intake remains
the only authority that writes Vault objects, Assets, ingestion runs, and
provenance.

## Tracked topology

The tracked contract uses:

- host namespace: `/mnt/photo-organizer-sources`;
- container namespace: `/app/sources`;
- broker socket directory: `/run/photo-organizer-source-access`;
- provider identifier: `linux_stable_mount_v1`;
- protected configuration: `/etc/photo-organizer/source-access.json`;
- stable Access Node state:
  `/var/lib/photo-organizer-source-access/access-node-id`.

The backend receives only fixed read-only bindings for the Source namespace and
broker directory. It is not privileged and has no Docker socket, broad host
mount, or mount authority.

Tracked examples contain placeholders for server-local filesystem identity.
Actual filesystem UUID, device, inode, group, and protected configuration
values remain protected host state and must not be committed. Accepted live
host reconciliation is recorded in the 12.65.3 closeout; this guide does not
duplicate protected values.

## Identity broker

The broker runs as a dedicated non-root user. It accepts only a versioned,
bounded JSON-lines protocol and opaque allowlisted `location_id` values.

It may inspect fixed mount and filesystem identity evidence. It may not:

- accept an arbitrary host or runtime path;
- read or transfer Source bytes;
- mount or unmount filesystems;
- execute caller-supplied commands;
- access Docker;
- perform ingestion.

Application-visible evidence is hashed, masked, or sanitized. Browser location
discovery returns only the opaque location ID, Source type, friendly name, and
availability information.

## Mounted Local

A Local Mounted Source requires the configured server-local filesystem type and
UUID, the exact fixed slot identity, the stable Linux Access Node, and a
contained POSIX relative root. Missing or conflicting evidence fails closed.

Backslashes, absolute roots, empty components, `.`, `..`, NUL values, and
symlink escapes are rejected.

## Mounted NAS

The NAS location requires the canonical share
`//192.168.1.171/PhotoOrganizer`, CIFS identity, the authoritative mount at
`/mnt/nas/photo-organizer`, and the fixed slot at
`/mnt/photo-organizer-sources/nas/photo-organizer`.

The namespace preparation contract is:

```text
inspect mount-table state first
-> if one exact shared CIFS slot already exists, validate and leave it untouched
-> if the slot is absent, prepare only the local mountpoint
-> make the namespace private
-> bind the exact authority to the exact slot
-> validate exact identity and uniqueness
-> make the namespace shared
-> validate again
```

Duplicate or ambiguous mount rows fail closed. Rollback may remove only mounts
created by the failing invocation; it must never unmount the authoritative NAS
mount or a pre-existing namespace/slot. An already-mounted NAS slot is never
passed to `install`, `chmod`, or `chown`, and the authoritative NAS target is
never a metadata-mutation target.

## Readiness, selection, and intake

Operators create or reuse a modern Endpoint-linked Profile. Before intake, the
normal application flow must:

```text
Profile
-> readiness
-> durable identity verified and matched
-> Source Selection
-> backend-derived Runtime Root
-> Run Ingestion / Source Intake
```

The browser supplies a Profile choice, not an authoritative path or
fingerprint. Intake must stop when identity, containment, mapping, or current
availability is wrong or ambiguous. Source media remains read-only; only Source
Intake may write application storage, Vault objects, Assets, runs, and
provenance.

## Development status

The Linux Development operator exposes a separate read-only command:

```bash
scripts/operator/development/photo_organizer_dev_operator.sh source-access-status
```

This checks tracked configuration, broker/service/socket evidence, and the
backend's fixed read-only bindings. It does not restart Docker, repair services,
remount NAS, recreate containers, or edit protected configuration.

Mounted Source unavailability is a provider-readiness result. It does not make
PostgreSQL, Redis, local application storage, or the general Development stack
unhealthy, and it is intentionally not folded into `recovery-status`.

## Operator-safe troubleshooting boundary

Use the read-only operator status command, service status, narrow mount-table
queries, and readiness/selection results to diagnose Mounted access. Do not
repair a mismatch by rewriting a Profile root, translating a Windows path,
relinking a legacy Profile, changing NAS permissions, stacking another bind,
or restarting/recreating unrelated application services.

If identity or topology evidence is missing, duplicated, changed, or
ambiguous, stop at the failed gate. Mount/service/configuration changes require
a separately approved operational milestone and ordered evidence gates.

## Installation and activation boundary

The repository includes tracked installer, configuration, systemd, namespace,
Compose, and GID-helper assets. Their presence in Git alone is never proof that
host artifacts are installed or active.

The accepted Development host was reconciled and activated through Milestone
12.65.3: the namespace and broker services are enabled and healthy, the broker
runs non-root, and the canonical NAS slot topology is live. Milestones 12.65.4
and 12.65.5 then validated NAS capability, modern Profile readiness/selection,
and bounded end-to-end intake. Mounted Local implementation is present, but its
live Profile/readiness/selection proof remains deferred.

Do not install, configure, enable, start, mount, rebuild, or recreate from this
guide. A future host change must compare installed state with tracked state,
preserve protected identity/configuration, and use a separately approved,
ordered operational milestone.

