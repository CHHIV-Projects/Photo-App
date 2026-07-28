# Photo Organizer Server Deployment Execution Record

**Filename:** `Photo_Organizer_Server_Deployment_Execution_Record_v1.0.md`  
**Version:** 1.0  
**Status:** ACTIVE EXECUTION RECORD  
**Server:** `henderson-server1`  
**Owner/Operator:** Chuck Henderson  
**Deployment started:** July 26, 2026  
**Record created:** July 27, 2026  
**Last updated:** July 27, 2026  
**Current execution point:** Platform baseline complete; pause before Arc 6 — Photo Organizer Deployment Preparation  
**Related guide:** `Photo_Organizer_Server_Build_and_Deployment_Guide_v1.0.md`

---

## 1. Purpose

This document records what was actually done to build and configure `henderson-server1`, including actual values, decisions, validation results, deviations, and unresolved items.

It complements the master guide:

- **Master guide:** How the server should be built, operated, maintained, and recovered.
- **Execution record:** What was actually done on this server, when, and with what result.

Do not store passwords, private SSH keys, setup tokens, API keys, recovery codes, database credentials, NAS credential contents, or secret `.env` values in this document or its evidence folders.

---

## 2. Current Status Summary

| Arc | Status | Completion date | Notes |
|---|---|---:|---|
| Arc 0 — Document Control and Safety | In progress | — | Master guide exists; execution record created; evidence archive pending |
| Arc 1 — Hardware, First Power, and Firmware | Complete | 2026-07-26 | 105 W Eco Mode enabled; EXPO left disabled |
| Arc 2 — Ubuntu Installation and Network Identity | Complete | 2026-07-27 | Ubuntu 24.04.4 LTS; static DHCP reservation confirmed |
| Arc 3 — Secure Headless Management | Complete | 2026-07-27 | SSH key-only login, UFW, Cockpit validated |
| Arc 4 — Synology Storage Integration | Complete at baseline | 2026-07-27 | Persistent SMB mount survives reboot; storage policy locked at architecture level |
| Arc 5 — GPU and Container Platform | Complete | 2026-07-27 | NVIDIA, Docker, GPU-in-container, Portainer, health baseline validated |
| Arc 6 — Photo Organizer Deployment Preparation | Not started | — | Requires deliberate reconnaissance and migration design |

---

## 3. Configuration Record

### 3.1 Hardware

| Item | Installed value | Verified |
|---|---|---|
| Case | Fractal Design Terra | Yes |
| Case spine position | 4 | Yes |
| CPU | AMD Ryzen 9 7900X, 12 cores / 24 threads | Yes |
| Motherboard | ASUS ROG Strix B650E-I Gaming WiFi | Yes |
| BIOS | 3602 | Yes |
| CPU cooler | Thermalright AXP90-X53 Full Copper | Yes |
| RAM | G.SKILL Flare X5 64 GB (2x32 GB), DDR5-6000 CL30 kit | Yes; currently running baseline DDR5-4800 |
| NVMe | Samsung 990 PRO 2 TB | Yes |
| PSU | Corsair SF1000 (2024), 80 PLUS Platinum | Yes |
| GPU | ASUS Prime GeForce RTX 5070 Ti OC 16 GB | Yes |
| GPU power | Native Corsair PSU-to-GPU 16-pin cable | Yes |
| Ethernet | Motherboard 2.5 Gb Ethernet | Yes |
| UPS | Not yet installed/recorded | No |

### 3.2 BIOS and firmware

| Setting | Actual value |
|---|---|
| BIOS version | 3602 |
| CPU Eco Mode | 105 W |
| EXPO | Disabled |
| Secure Boot | Disabled |
| fTPM state | Reset during first boot because no prior encrypted OS existed |
| UEFI dbx update | Deferred |
| Motherboard firmware update | None available through `fwupdmgr` |
| Samsung 990 PRO firmware update | None available through `fwupdmgr` |
| First BIOS CPU temperature | Stable at approximately 65°C |

### 3.3 Operating system and network

| Setting | Actual value |
|---|---|
| Hostname | `henderson-server1` |
| Ubuntu | 24.04.4 LTS |
| Kernel | `6.8.0-136-generic` |
| Architecture | x86-64 |
| Linux user | `chuck` |
| Linux UID/GID | `1000:1000` |
| Server IPv4 | `192.168.1.173` |
| Ethernet interface | `eno1` |
| Server Ethernet MAC | `30:C5:99:ED:46:11` |
| Router lease | Static DHCP reservation |
| NAS IPv4 | `192.168.1.171` |
| NAS router lease | Static DHCP reservation |
| Server timezone | UTC |
| NTP | Active and synchronized |
| Wi-Fi | Detected but disabled |

### 3.4 Platform software

| Component | Version/status |
|---|---|
| NVIDIA driver | 595.84 |
| Driver CUDA compatibility | 13.2 |
| NVIDIA Container Toolkit | Installed and validated |
| Docker Engine | 29.6.2 |
| Docker Compose | 5.3.1 |
| containerd | 2.2.6 |
| Cockpit | Installed; port 9090; LAN-only |
| Portainer CE | Installed; port 9443; LAN-only |
| UFW | Active |
| Automatic security updates | Enabled |
| CIFS utilities | 7.0 |
| lm-sensors | Installed |

### 3.5 Synology storage

| Setting | Actual value |
|---|---|
| NAS hostname | `HENDERSON-NAS` |
| NAS IP | `192.168.1.171` |
| NAS service account | `henderson-server` |
| Synology shared folder | `PhotoOrganizer` |
| Linux mount point | `/mnt/nas/photo-organizer` |
| SMB protocol | 3.1.1 |
| Persistent mount | Yes; systemd automount, `_netdev`, `nofail` |
| NAS capacity seen by Ubuntu | 11 TB |
| NAS used | 2.8 TB |
| NAS available | 7.7 TB |
| Recycle Bin | Enabled; `#recycle` present |

NAS folder structure:

```text
PhotoOrganizer/
├── production/
│   ├── vault/
│   ├── staging/
│   ├── backups/
│   │   ├── database/
│   │   ├── configuration/
│   │   └── deployment-records/
│   ├── exports/
│   └── recovery/
├── test/
│   ├── vault/
│   ├── staging/
│   ├── backups/
│   └── fixtures/
├── development/
│   ├── staging/
│   ├── fixtures/
│   ├── sample-media/
│   └── backups/
└── shared/
    ├── models/
    ├── reference-data/
    └── installation-records/
```

---

## 4. Security Baseline

| Control | Status |
|---|---|
| SSH public-key authentication | Enabled and validated |
| Windows `ssh-agent` | Enabled and validated |
| SSH password authentication | Disabled |
| Root SSH login | Disabled |
| Local console login | Available for recovery |
| UFW firewall | Active |
| SSH access | LAN only: `192.168.1.0/24` to TCP 22 |
| Cockpit access | LAN only: `192.168.1.0/24` to TCP 9090 |
| Portainer access | LAN only: `192.168.1.0/24` to TCP 9443 |
| Public router port forwarding | None |
| Automatic security updates | Enabled |
| Automatic rebooting | Not enabled |
| Unexpected listening services | None at baseline |
| Secure Boot | Disabled; review deferred |
| UEFI dbx update | Deferred |

---

## 5. Milestone Execution Records

### Arc 1, Milestone 1.1 — Final Physical Inspection

**Status:** Complete  
**Date:** 2026-07-26

**Actual results**

- Terra spine position set to 4.
- Clearance confirmed on CPU-cooler and GPU sides.
- CPU fan connected to `CPU_FAN`.
- 24-pin motherboard and CPU EPS connectors fully latched.
- Both RAM modules fully seated.
- Samsung 990 PRO and motherboard heatsink secured.
- Native Corsair 16-pin GPU power cable used.
- GPU connector fully seated with no visible gap.
- No cables touching fans.
- Side-panel clearance confirmed; panels kept off for initial startup.

**Result:** Pass.

---

### Arc 1, Milestone 1.2 — First Power-On and POST

**Status:** Complete  
**Date:** 2026-07-26

**Actual results**

- Successful POST.
- CPU detected: AMD Ryzen 9 7900X.
- RAM detected: 64 GB.
- SSD detected: Samsung 990 PRO 2 TB.
- GPU output functional.
- CPU fan approximately 2,129 RPM during BIOS review.
- BIOS CPU temperature stabilized at approximately 65°C.
- Motherboard temperature approximately 40°C.

**Deviation/incident**

- First boot displayed an fTPM warning because the refurbished CPU had prior fTPM state.
- `Y` was selected to reset fTPM because this was a new server with no pre-existing encrypted OS or BitLocker dependency.

**Result:** Pass.

---

### Arc 1, Milestone 1.3 — BIOS Baseline

**Status:** Complete  
**Date:** 2026-07-26

**Decisions**

- BIOS 3602 retained; no update performed.
- 105 W Eco Mode enabled and confirmed after reboot.
- EXPO left disabled.
- Memory retained at DDR5-4800 baseline.
- Secure Boot left at default/disabled state.

**Result:** Pass.

---

### Arc 2, Milestone 2.1 — Ubuntu Installation Media

**Status:** Complete  
**Date:** 2026-07-26

**Actual results**

- 16 GB USB used.
- Ubuntu Server 24.04.4 LTS AMD64 ISO used.
- Rufus used on Windows.
- USB created successfully and labeled `Ubuntu-Serv`.

**Deviation/lesson**

- ISO was initially downloaded directly to the target USB. It was copied to the Windows PC before Rufus reformatted the USB.

**Result:** Pass.

---

### Arc 2, Milestone 2.2 — Ubuntu Server Installation

**Status:** Complete  
**Date:** 2026-07-26 to 2026-07-27

**Selections**

- Ubuntu Server, not minimized.
- Third-party drivers deferred during installer.
- Ethernet via DHCP.
- Proxy blank.
- Default Ubuntu mirror accepted.
- Entire Samsung 990 PRO used.
- LVM disabled.
- Full-disk encryption disabled to preserve unattended headless reboot behavior.
- Hostname: `henderson-server1`.
- Username: `chuck`.
- Ubuntu Pro skipped.
- OpenSSH installed.
- Password authentication temporarily enabled for first remote setup.
- Featured snaps not installed.

**Result:** Pass.

---

### Arc 2, Milestone 2.3 — Initial Validation and Updates

**Status:** Complete  
**Date:** 2026-07-27

**Actual results**

- Hostname, OS, kernel, CPU, RAM, storage, Ethernet, DNS, and SSH validated.
- `sudo apt update` completed successfully.
- `sudo apt full-upgrade` completed successfully.
- Reboot completed successfully.
- Updates pending after completion: 0 at that checkpoint.

**Result:** Pass.

---

### Arc 2, Milestone 2.4 — Stable Network Identity

**Status:** Complete  
**Date:** 2026-07-27

**Actual results**

- Router DHCP reservation created for server.
- Server reservation: `192.168.1.173` mapped to MAC `30:C5:99:ED:46:11`.
- Reservation survived server reboot.
- NAS also assigned a static DHCP reservation at `192.168.1.171`.

**Result:** Pass.

---

### Arc 3, Milestone 3.1 — SSH Key Authentication

**Status:** Complete  
**Date:** 2026-07-27

**Actual results**

- ED25519 key created on Windows.
- Private key retained on Windows only.
- Public key installed in `/home/chuck/.ssh/authorized_keys`.
- Windows `ssh-agent` configured and key loaded.
- New SSH sessions connect without Ubuntu password or repeated key passphrase.
- SSH password authentication disabled only after a second key-based session succeeded.
- Root SSH login disabled.
- SSH configuration syntax validated before reload.

**Result:** Pass.

---

### Arc 3, Milestone 3.2 — Cockpit and Firewall

**Status:** Complete  
**Date:** 2026-07-27

**Actual results**

- Cockpit installed and validated at `https://192.168.1.173:9090`.
- Administrative access, logout, and re-login validated.
- UFW enabled after SSH and Cockpit rules were added.
- SSH and Cockpit were retested from separate sessions after firewall activation.

**Result:** Pass.

---

### Arc 3, Milestone 3.3 — Security Baseline

**Status:** Complete  
**Date:** 2026-07-27

**Actual results**

- `unattended-upgrades` active.
- NTP active and synchronized.
- Server timezone retained as UTC.
- Listening services reviewed; only expected baseline services present.
- No public port forwarding configured.

**Result:** Pass.

---

### Arc 4, Milestone 4.1 — NAS Account and Share Structure

**Status:** Complete  
**Date:** 2026-07-27

**Decisions**

- Dedicated Synology service account created: `henderson-server`.
- One Synology shared folder created: `PhotoOrganizer`.
- Environment-specific subfolders created beneath the share.
- General `Photos` share was not reused as the managed Vault.

**Permissions baseline**

- `henderson-server`: Read/Write.
- Synology administrator account: Read/Write.
- Guest and unrelated users: No access.

**Result:** Pass.

---

### Arc 4, Milestone 4.2 — Temporary SMB Mount and Permission Test

**Status:** Complete  
**Date:** 2026-07-27

**Actual results**

- NAS ping: 0% packet loss.
- SMB TCP port 445 reachable.
- `cifs-utils` version 7.0 installed.
- Root-protected credentials file created at `/etc/samba/credentials/photo-organizer`.
- Credentials-file permissions validated as `-rw------- root root`.
- Temporary mount succeeded using SMB 3.1.1.
- Folder structure visible from Ubuntu.
- Write/read/delete test succeeded only in `development/staging`.
- No files were written to `production/vault`.

**Result:** Pass.

---

### Arc 4, Milestone 4.3 — Persistent SMB Mount

**Status:** Complete  
**Date:** 2026-07-27

**Actual results**

- `/etc/fstab` backup created before editing.
- Persistent CIFS entry added with `_netdev`, `nofail`, and `x-systemd.automount`.
- `sudo mount -a` returned no errors.
- Mount survived reboot.
- SSH, Cockpit, Portainer, and NAS mount all returned successfully after reboot.

**Result:** Pass.

---

### Arc 4, Milestone 4.4 — NAS Access Policy

**Status:** Complete at architecture-policy level  
**Date:** 2026-07-27

**Locked policy**

- Host mount remains read/write.
- Containers receive only the specific subfolders they require.
- Production services may receive production paths.
- Test services may receive only test paths.
- Development services may receive only development paths.
- Unrelated applications must never receive `production/vault`.
- `#recycle` must be excluded from application scanning.
- Live PostgreSQL and Redis data remain on local NVMe, not SMB.
- Database/configuration backups may be stored under `production/backups`.

**Deferred implementation detail**

- Exact Docker bind mounts and service-level read/write modes will be finalized during Photo Organizer deployment reconnaissance.

---

### Arc 5, Milestone 5.1 — NVIDIA Driver

**Status:** Complete  
**Date:** 2026-07-27

**Actual results**

- Ubuntu detected the RTX 5070 Ti on PCIe.
- Ubuntu recommended `nvidia-driver-595-open`.
- Driver installed and rebooted successfully.
- `nvidia-smi` validated:
  - Driver 595.84
  - 16,303 MiB VRAM
  - CUDA compatibility 13.2
  - Healthy idle temperature and power

**Result:** Pass.

---

### Arc 5, Milestone 5.2 — Docker Engine and Compose

**Status:** Complete  
**Date:** 2026-07-27

**Actual results**

- Docker installed from Docker’s official Ubuntu repository.
- Docker Engine 29.6.2.
- Docker Compose 5.3.1.
- Docker service active and enabled.
- `chuck` was deliberately not added to the Docker group; `sudo docker` remains required.

**Result:** Pass.

---

### Arc 5, Milestone 5.3 — NVIDIA Container Toolkit

**Status:** Complete  
**Date:** 2026-07-27

**Actual results**

- NVIDIA Container Toolkit installed.
- Docker runtime configured.
- GPU-enabled Ubuntu container successfully ran `nvidia-smi`.
- RTX 5070 Ti and full VRAM visible inside the container.

**Result:** Pass.

---

### Arc 5, Milestone 5.4 — Portainer

**Status:** Complete  
**Date:** 2026-07-27

**Actual results**

- Portainer deployed from `/srv/compose/portainer/compose.yaml`.
- HTTPS host port 9443 published.
- Firewall rule restricted access to the home LAN.
- Initial setup required a setup token from container logs.
- Initial setup timed out once; container restart restored the setup window.
- Local Docker environment validated.
- Compose file remains the source of truth.

**Result:** Pass.

---

### Arc 5, Milestone 5.5 — Initial Health Baseline

**Status:** Complete  
**Date:** 2026-07-27

**Baseline results**

| Metric | Actual value |
|---|---|
| CPU | AMD Ryzen 9 7900X, 12 cores / 24 threads |
| Load average | 0.12, 0.17, 0.08 |
| RAM | 61 GiB usable; approximately 1.3 GiB used |
| Swap | 8 GiB; unused |
| NVMe filesystem | 1.8 TB; 14 GB used; 1% |
| NAS filesystem | 11 TB; 2.8 TB used; 27% |
| CPU Tctl | Approximately 50°C |
| CPU chiplets | Approximately 38°C |
| NVMe | Approximately 44°C |
| GPU | 47°C, 11 W, 0% utilization |
| Failed services | 0 |
| Active containers | 1: Portainer |
| Docker image storage | Approximately 348 MB |
| Firewall | Active; ports 22, 9090, 9443 LAN-only |
| Unexpected listeners | None |

**Non-blocking journal item**

- One boot-time input-device scan-code warning was observed: `EVIOCSKEYCODE ... Invalid argument`.
- No functional keyboard issue was observed.
- No action required unless a real input-device problem appears.

**Maintenance note**

- Package manager reported six packages not upgraded during `lm-sensors` installation. Review with `apt list --upgradable` before beginning Photo Organizer deployment; do not automatically force them without review.

**Result:** Pass.

---

## 6. Decision Log

| Date | Decision | Reason |
|---|---|---|
| 2026-07-26 | Use Ubuntu Server 24.04.4 LTS | Mature LTS baseline; lower deployment risk than newly released 26.04 |
| 2026-07-26 | Retain BIOS 3602 | Hardware POSTed successfully; no specific firmware need identified |
| 2026-07-26 | Enable 105 W Eco Mode | Improve compact-server thermals and efficiency |
| 2026-07-26 | Leave EXPO disabled initially | Establish stable baseline before memory tuning |
| 2026-07-26 | Disable LVM for the single-disk baseline | Simpler storage and recovery model |
| 2026-07-26 | Do not use full-disk encryption | Preserve unattended headless reboot behavior |
| 2026-07-27 | Use router DHCP reservations | Predictable addresses without manual static configuration in Ubuntu/DSM |
| 2026-07-27 | Use SSH keys and disable SSH passwords | Stronger remote authentication after key access was proven |
| 2026-07-27 | Keep Secure Boot disabled for initial deployment | Simplify NVIDIA and container baseline; revisit later |
| 2026-07-27 | Defer UEFI dbx update | Secure Boot disabled; recovery baseline should be completed first |
| 2026-07-27 | Keep `chuck` out of Docker group | Docker group grants root-equivalent control |
| 2026-07-27 | Use one `PhotoOrganizer` Synology share with environment subfolders | Clear structure and simple first deployment |
| 2026-07-27 | Keep live PostgreSQL and Redis on NVMe | Avoid running live database state over SMB |
| 2026-07-27 | Bind-mount only required NAS subfolders into containers | Prevent test/development/unrelated services from reaching production Vault |

---

## 7. Deviation and Lessons-Learned Log

| Date | Deviation or lesson | Guide update needed |
|---|---|---|
| 2026-07-26 | Ubuntu ISO was initially downloaded to the USB being prepared | Clarify that ISO and Rufus must reside on the Windows PC before writing USB |
| 2026-07-26 | Refurbished CPU presented prior fTPM state | Add explicit first-build fTPM decision guidance |
| 2026-07-27 | Portainer setup timed out before administrator creation | Add five-minute setup-window warning and restart procedure |
| 2026-07-27 | Portainer required a setup token from logs | Add token retrieval step to Portainer setup procedure |
| 2026-07-27 | Cockpit URL was typed once into Bash rather than browser | Clarify browser URLs versus shell commands |
| 2026-07-27 | Verizon router controls required horizontal scrolling | Add note to inspect the full-width device/DHCP tables |
| 2026-07-27 | Router calls reservations “Static Lease Type” | Use actual router terminology in the guide |
| 2026-07-27 | `findmnt` shows both `systemd-1` autofs and CIFS rows | Document this as expected for `x-systemd.automount` |

---

## 8. Evidence Index

Evidence is optional when the execution record already contains the necessary actual value. Save evidence when it materially helps troubleshooting, recovery, comparison, or audit.

Recommended repository structure:

```text
docs/server_deployment/
├── Photo_Organizer_Server_Build_and_Deployment_Guide_v1.0.md
├── Photo_Organizer_Server_Deployment_Execution_Record_v1.0.md
├── evidence/
│   ├── command-output/
│   ├── screenshots/
│   └── photos/
└── archived/
```

### Recommended command-output evidence

| Suggested filename | Contents | Priority |
|---|---|---|
| `2026-07-27_system_identity.txt` | `hostnamectl`, `uname -r`, `ip -br address` | High |
| `2026-07-27_network_and_firewall.txt` | UFW rules, listening ports, router reservation notes | High |
| `2026-07-27_nvidia_baseline.txt` | Host `nvidia-smi` and GPU-container validation | High |
| `2026-07-27_docker_versions.txt` | Docker Engine, Compose, containerd versions | High |
| `2026-07-27_storage_mount_baseline.txt` | Sanitized `findmnt`, `df -h`, NAS mount structure | High |
| `2026-07-27_health_baseline.txt` | CPU/RAM/disk/temperature/failed-service results | High |
| `2026-07-27_installed_packages_snapshot.txt` | Selected package versions or `dpkg-query` snapshot | Medium |
| `2026-07-27_service_inventory.txt` | Enabled/active core services | Medium |
| `2026-07-27_firmware_status.txt` | Sanitized `fwupdmgr get-upgrades`, Secure Boot state | Medium |
| `2026-07-27_portainer_compose_sanitized.yaml` | Copy of authoritative Compose file | High |
| `2026-07-27_fstab_sanitized.txt` | NAS mount entry without credentials or secrets | High |

### Recommended screenshots/photos

| Suggested filename | Contents | Priority |
|---|---|---|
| `bios-overview-baseline.jpg` | BIOS version, CPU, RAM, SSD, temperature | Medium |
| `bios-eco-mode-105w.jpg` | Confirmed Eco Mode setting | Medium |
| `cockpit-overview-baseline.png` | CPU/RAM/OS summary | Medium |
| `portainer-local-environment.png` | Local Docker environment healthy | Low |
| `synology-photoorganizer-structure.png` | NAS folder structure | Medium |
| `router-static-leases.png` | Server and NAS static reservations, with unrelated devices obscured | Medium |
| `hardware-cable-clearance.jpg` | GPU power seating and cable/fan clearance | Medium |

### Evidence safety rules

Before saving evidence to Git, remove or obscure:

- Passwords and passphrases
- SSH private-key content
- Portainer setup tokens
- NAS credentials
- GitHub tokens
- API keys
- `.env` secrets
- Router administrator passwords
- Serial numbers when not operationally needed
- Unrelated household device names, MAC addresses, or personal details

Do not commit the following files:

```text
/etc/samba/credentials/photo-organizer
C:\Users\chhen\.ssh\id_ed25519
Any real production .env file
Any database dump containing sensitive personal data unless encrypted and intentionally managed outside Git
```

---

## 9. Outstanding Items Before Arc 6

- [ ] Review the six packages reported as not upgraded.
- [ ] Decide whether to capture the recommended evidence files now or incrementally.
- [ ] Update the master guide from pre-first-power status through completion of Arc 5.
- [ ] Decide whether Synology Snapshot Replication should be configured before Photo Organizer cutover.
- [ ] Decide whether the one-share NAS structure remains appropriate for long-term snapshot and permission policy.
- [ ] Perform detailed Photo Organizer deployment reconnaissance before copying code, migrating PostgreSQL, or starting production services.
- [ ] Preserve the existing Windows production environment and rollback path during migration planning.

---

## 10. Next Checkpoint

> Platform build and NAS integration are complete through Arc 5. The next work is documentation synchronization, followed by a detailed discussion and reconnaissance plan for Arc 6 — Photo Organizer Deployment Preparation. No production Photo Organizer data, database, or application services have yet been migrated to `henderson-server1`.
