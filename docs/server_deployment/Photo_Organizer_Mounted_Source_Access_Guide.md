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
values belong to later host reconciliation and must not be committed.

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
make namespace private
-> create one exact NAS bind slot
-> validate exact identity
-> make namespace shared
-> validate again
```

Duplicate or ambiguous mount rows fail closed. Rollback may remove only mounts
created by the failing invocation; it must never unmount the authoritative NAS
mount or a pre-existing namespace/slot.

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

## Installation and activation boundary

The repository includes tracked installer, configuration, systemd, namespace,
Compose, and GID-helper assets. Their presence in Git is not proof that matching
host artifacts are installed or active.

Do not install, configure, enable, start, mount, rebuild, or recreate from this
guide without a separately approved host-state reconciliation milestone. That
later milestone must compare installed state with tracked state before changing
anything and must validate live Local/NAS behavior without claiming repository
tests as live provider evidence.

