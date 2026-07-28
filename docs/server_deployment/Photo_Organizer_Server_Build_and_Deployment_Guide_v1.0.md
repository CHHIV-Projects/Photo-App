# Photo Organizer Server Build and Deployment Guide

**Filename:** `Photo_Organizer_Server_Build_and_Deployment_Guide_v1.0.md`  
**Version:** 1.0  
**Status:** ACTIVE WORKING GUIDE — PRE-FIRST-POWER  
**Owner/Operator:** Chuck Henderson  
**Created:** July 26, 2026  
**Last updated:** July 26, 2026  
**Current execution point:** Arc 1, Milestone 1.1 — Final physical inspection before first power-on

---

## Document Mission

This is the durable installation, deployment, administration, troubleshooting, and recovery record for Chuck’s mini server.

The server mission is:

> A reliable, always-on, self-hosted home application platform whose primary production workload is Photo Organizer.

Photo Organizer is the flagship workload. Future applications may include Plex or Jellyfin, local AI services, Ollama, Open WebUI, personal applications, monitoring tools, Home Assistant, automation services, and game servers. New applications must be added in a reproducible, isolated, documented manner without destabilizing Photo Organizer.

This document is designed to be used interactively with ChatGPT, one milestone at a time. Do not attempt to complete an entire arc in one uninterrupted session.

---

## Source-of-Truth Rules

| Category                            | Source of truth                                       |
| ----------------------------------- | ----------------------------------------------------- |
| Application code                    | Git repository and approved commit/tag                |
| Application deployment              | Docker Compose plus documented configuration          |
| Photo Organizer operational data    | PostgreSQL                                            |
| Photo Organizer physical file truth | Immutable Vault on Synology NAS                       |
| General durable storage             | Synology NAS                                          |
| Secrets                             | Approved secure secret-storage location               |
| Network assignments                 | Router reservation plus this guide                    |
| Server configuration                | This guide and its change log                         |
| Installed applications              | Application Inventory appendix                        |
| Backups                             | Documented destinations plus successful restore tests |

Portainer is a visibility and convenience layer, not the sole deployment source of truth.  
Cockpit is a management interface, not the sole configuration source of truth.  
Memory is not a source of truth.

---

## Safety Standard

> When an observed result differs materially from the expected result, stop, preserve the evidence, and review it with ChatGPT before continuing.

### Stop immediately when

- The CPU temperature rises rapidly toward 90°C during initial BIOS inspection.
- The expected 64 GB of RAM is not detected.
- The Samsung 990 PRO is not detected.
- The RTX 5070 Ti is not detected.
- A power connector is not fully seated.
- A fan or cable obstructs another fan.
- The wrong disk may be selected for erasure.
- Networking does not work as expected.
- A reserved address conflicts with another device.
- SSH fails after an authentication change.
- A NAS share mounts with more write access than intended.
- The Photo Organizer Vault path or permissions are uncertain.
- A database backup or restore cannot be verified.
- Containers repeatedly restart.
- NVIDIA is unavailable after driver installation.
- The server cannot reconnect to the NAS after reboot.
- A change could affect Vault immutability, provenance, or duplicate handling.
- A destructive command is not fully understood.

### Never use these as routine fixes

- `chmod 777`
- Running every container as privileged
- Deleting unknown files “to see if it helps”
- Reformatting a disk before evidence is collected
- Reinstalling Ubuntu as the first troubleshooting step
- Disabling security merely to make a service work
- Storing secrets in Git
- Mixing modular power-supply cables from different PSU models
- Manually editing or reorganizing managed Vault files
- Exposing Cockpit, Portainer, PostgreSQL, Redis, or Photo Organizer administration directly to the public internet

---

## Protecting Secrets

Before sharing screenshots, photographs, configuration files, or command output, remove or obscure:

- Passwords
- Recovery codes
- API keys
- GitHub tokens
- Private SSH keys
- NAS credential contents
- `.env` secret values
- Database passwords
- Session cookies
- Personal access tokens

IP addresses on the private home network are normally acceptable for troubleshooting, but they should still be recorded only where useful.

---

## Architecture Overview

```text
Windows 11 PC
    |
    | Wi-Fi
    |
Verizon 5G Home Router
    |
    |-- Ethernet --> Ubuntu Mini Server
    |
    |-- Ethernet --> Synology DS225+ NAS
```

Devices connected to the same home router can communicate even though the Windows PC uses Wi-Fi and the server and NAS use Ethernet.

### Windows PC responsibilities

- Primary development workstation
- VS Code, Git, GitHub, Copilot, and ChatGPT
- Browser interface for Photo Organizer
- Synology DSM access
- Server administration through browser, SSH, and VS Code Remote SSH
- Controlled deployment initiation

### Ubuntu mini-server responsibilities

- Photo Organizer backend and frontend
- PostgreSQL and Redis
- Background workers
- Docker and Docker Compose
- Media processing
- NVIDIA GPU and AI workloads
- Monitoring and management tools
- Future isolated self-hosted applications

### Synology NAS responsibilities

- Photo Organizer Vault
- Durable photo and video storage
- Snapshots and backups
- Shared folders
- Selected application backups
- Future Plex/Jellyfin media libraries
- Potential offsite replication to the Oregon NAS

> The NAS provides durable storage. The mini server provides compute and application services.

---

## How Chuck Will Interact With the Server

Use the simplest safe interface that accomplishes the task.

| Task                        | Preferred interface            | Backup interface              |
| --------------------------- | ------------------------------ | ----------------------------- |
| Use Photo Organizer         | Web browser                    | Local browser during recovery |
| Manage Synology NAS         | Synology DSM                   | NAS recovery process          |
| View server health          | Cockpit                        | SSH commands                  |
| Manage containers           | Portainer                      | Docker Compose through SSH    |
| View application logs       | Portainer or VS Code           | SSH                           |
| Edit approved configuration | VS Code Remote SSH             | SSH text editor               |
| Deploy Photo Organizer      | Git/Docker workflow            | Guided SSH procedure          |
| Restart server              | Cockpit                        | SSH or local console          |
| Troubleshoot boot/network   | Local monitor and keyboard     | Router diagnostics            |
| Emergency recovery          | Local console and recovery USB | Documented rebuild            |

SSH remains essential, but it is not the only management method.

---

## Operating-System Decision

### Approved initial baseline

**Ubuntu Server 24.04 LTS, current point-release installation media available from Ubuntu at execution time.**

Reasons:

- Mature LTS baseline suitable for production.
- Standard security maintenance through May 2029.
- Compatible with the project’s existing Ubuntu/Linux direction.
- Lower first-install risk than adopting a newly released LTS before its first point release.
- Hardware Enablement kernels can provide newer hardware support.
- The NVIDIA driver will be installed from Ubuntu’s supported package method rather than by running an unmanaged NVIDIA `.run` installer.

### Deferred alternative

Ubuntu Server 26.04 LTS was released in April 2026, but its first point release is scheduled after this guide’s creation date. We will not change the baseline merely because 26.04 is newer. Reconsideration requires a recorded decision reviewing:

- RTX 5070 Ti driver support
- Docker support
- NVIDIA Container Toolkit support
- PostgreSQL compatibility
- Photo Organizer dependencies
- Upgrade and rollback implications

**Decision record:** Remain on Ubuntu Server 24.04 LTS for initial deployment unless an execution-time compatibility check identifies a material blocker.

---

## Confirmed Hardware Record

| Component   | Installed/planned part                           | Verification status                    |
| ----------- | ------------------------------------------------ | -------------------------------------- |
| Case        | Fractal Design Terra                             | Installed; physical inspection pending |
| CPU         | AMD Ryzen 9 7900X, 12C/24T, 170 W                | Installed; POST pending                |
| Motherboard | ASUS ROG Strix B650E-I Gaming WiFi               | Installed; BIOS version unknown        |
| CPU cooler  | Thermalright AXP90-X53 Full Copper               | Installed; mounting inspection pending |
| RAM         | G.SKILL Flare X5 64 GB (2x32 GB) DDR5-6000 CL30  | Installed; detection pending           |
| NVMe        | Samsung 990 PRO 2 TB, non-heatsink               | Installed; detection pending           |
| PSU         | Corsair SF1000 (2024), 80 PLUS Platinum, SFX     | Installed; cable inspection pending    |
| GPU         | ASUS Prime RTX 5070 Ti OC 16 GB                  | Installed; detection pending           |
| Network     | Motherboard 2.5 Gb Ethernet; Wi-Fi 6E            | Ethernet connected; validation pending |
| NAS         | Synology DS225+ with mirrored 12 TB-class drives | Existing                               |
| UPS         | DECISION REQUIRED                                | Not yet recorded                       |

### Important physical-layout conclusion

The ASUS GPU is approximately 304 x 126 x 50 mm. The AXP90-X53 cooler is approximately 53 mm tall. For a GPU no taller than 131 mm, Fractal’s Terra spine position 5 allows approximately 63 mm of GPU thickness and 57 mm of CPU-cooler height.

**Recommended starting spine position: 5**

This provides approximately:

- 13 mm of nominal GPU-thickness allowance
- 4 mm of nominal CPU-cooler clearance

Record the actual spine setting during Milestone 1.1. Do not force either side panel closed.

### CPU thermal-design note

The Ryzen 9 7900X is a 170 W processor with a 95°C maximum operating temperature. AMD recommends liquid cooling for optimal unrestricted performance. The AXP90-X53 is a compact low-profile cooler selected for the Terra form factor.

This is not an automatic build failure, but it is a deliberate design constraint.

Initial policy:

1. First POST at motherboard defaults.
2. Do not enable EXPO or overclocking.
3. Verify cooler mounting, fan detection, and BIOS temperature.
4. Install Ubuntu and collect idle/load temperature evidence.
5. Evaluate an AMD Eco Mode or power-limit configuration before sustained server workloads.
6. Prefer reliability, manageable noise, and predictable temperatures over maximum benchmark performance.

No power-limit change will be made until the baseline is recorded.

---

# Arc and Milestone Map

## Arc 0 — Document Control and Safety

- Milestone 0.1: Establish the working record
- Milestone 0.2: Confirm recovery and evidence-capture method

## Arc 1 — Hardware, First Power, and Firmware

- Milestone 1.1: Final physical inspection
- Milestone 1.2: First power-on and POST
- Milestone 1.3: BIOS baseline and update decision
- Milestone 1.4: Baseline hardware stability and thermal plan

## Arc 2 — Ubuntu Installation and Network Identity

- Milestone 2.1: Create Ubuntu installation and recovery media
- Milestone 2.2: Install Ubuntu Server
- Milestone 2.3: Initial Ubuntu validation and updates
- Milestone 2.4: DHCP reservation and stable network identity
- Milestone 2.5: Remote administration from Windows

## Arc 3 — Secure Headless Management Platform

- Milestone 3.1: SSH keys and access recovery
- Milestone 3.2: Firewall and security baseline
- Milestone 3.3: Cockpit
- Milestone 3.4: Linux directory and permissions conventions

## Arc 4 — Synology Storage Integration

- Milestone 4.1: NAS account and share inventory
- Milestone 4.2: Temporary SMB mounts and permission validation
- Milestone 4.3: Persistent mounts and unavailable-NAS behavior
- Milestone 4.4: Vault, staging, media, and backup access policies

## Arc 5 — GPU and Container Platform

- Milestone 5.1: NVIDIA driver installation and validation
- Milestone 5.2: Docker Engine and Compose
- Milestone 5.3: NVIDIA Container Toolkit
- Milestone 5.4: Portainer
- Milestone 5.5: Monitoring and resource baseline

## Arc 6 — Photo Organizer Deployment Preparation

- Milestone 6.1: Inventory the Windows production environment
- Milestone 6.2: Finalize server deployment architecture
- Milestone 6.3: Git-based server deployment
- Milestone 6.4: Photo Organizer production configuration
- Milestone 6.5: PostgreSQL migration plan
- Milestone 6.6: Redis migration decision

## Arc 7 — Startup, Validation, and Production Cutover

- Milestone 7.1: First controlled startup
- Milestone 7.2: Read-only and small reversible validation
- Milestone 7.3: Database migration and final synchronization
- Milestone 7.4: Production cutover
- Milestone 7.5: Stabilization and rollback retirement decision

## Arc 8 — Operations, Expansion, Backup, and Recovery

- Milestone 8.1: Development and deployment workflow
- Milestone 8.2: Backup and restore testing
- Milestone 8.3: UPS and power recovery
- Milestone 8.4: Routine operations and maintenance
- Milestone 8.5: Future application intake
- Milestone 8.6: Plex/Jellyfin planning
- Milestone 8.7: Local AI planning
- Milestone 8.8: Game-server planning
- Milestone 8.9: Troubleshooting framework
- Milestone 8.10: Full disaster-recovery rebuild

---

# Arc 0 — Document Control and Safety

## Milestone 0.1 — Establish the Working Record

### Objective

Make this guide the durable record of actual configuration rather than a generic plan.

### Checklist

- [ ] Save this file in at least two durable locations.
- [ ] Keep one working copy in the Photo Organizer project documentation.
- [ ] Keep one backup copy outside the server being built.
- [ ] Record changes in the Change Log appendix.
- [ ] Mark checkboxes only after validation.
- [ ] Do not store passwords or private keys in this guide.
- [ ] Record exact hardware model names and versions as discovered.
- [ ] Record every intentional deviation before continuing.

### Completion evidence

- Working-file location: ______________________________________
- Backup-file location: ______________________________________
- Guide checksum, if later used: _______________________________

## Milestone 0.2 — Confirm Recovery and Evidence Capture

### Required items

- Windows PC with browser and ChatGPT access
- Phone or camera for BIOS/POST photographs
- Monitor
- Wired keyboard
- Wired mouse
- Ethernet connection
- Ubuntu installer USB
- Separate recovery USB, or a documented plan to create one
- Access to Verizon router administration
- Access to Synology DSM
- Motherboard manual available on the Windows PC
- A place to record exact error text

### Checklist

- [ ] I can photograph the monitor if POST or BIOS behaves unexpectedly.
- [ ] I can use another device to consult this guide if the server is unavailable.
- [ ] I know where the motherboard manual is.
- [ ] I can access the router administration page.
- [ ] I can access Synology DSM.
- [ ] I will not share passwords or secret values in troubleshooting screenshots.

---

# Arc 1 — Hardware, First Power, and Firmware

## Milestone 1.1 — Final Physical Inspection

### Objective

Verify that the partially assembled server is safe to power on.

### Why this matters

Most first-start problems come from a loose power connector, improperly seated RAM, incorrect fan connection, a partially seated GPU, or cable interference. Discovering these before power-on is safer and easier than diagnosing them after a failed POST.

### Prerequisites

- Server shut down and unplugged
- PSU rear switch in the `O` position
- Work area dry and well lit
- Static precautions observed
- No metal tools resting inside the case

### Required information to record

- Terra spine position: ______
- CPU cooler orientation: ______________________
- CPU fan header used: _________________________
- GPU power cable type: ________________________
- BIOS FlashBack USB port identified: Yes / No
- Motherboard diagnostic LED location identified: Yes / No

### Inspection steps

#### A. External and case inspection

- [ ] Remove both Terra side panels.
- [ ] Confirm no loose screws or metal objects are inside.
- [ ] Confirm the case spine is locked in position.
- [ ] Prefer spine position **5** for the current GPU/cooler dimensions.
- [ ] Confirm both side panels can close without pressure.
- [ ] Confirm no cable presses into the GPU or CPU fan.
- [ ] Confirm all fan blades rotate freely by hand with power disconnected.
- [ ] Confirm ventilation openings are unobstructed.
- [ ] Confirm the case is placed on a hard surface, not carpet or fabric.

#### B. Motherboard power

- [ ] Confirm the 24-pin motherboard power connector is fully seated.
- [ ] Confirm the CPU EPS power connector is fully seated.
- [ ] Confirm the connector latches are engaged.
- [ ] Confirm only cables supplied for this exact Corsair PSU, or explicitly approved compatible Corsair cables, are used.
- [ ] Do not use modular PSU cables from another power supply.

#### C. CPU and cooler

- [ ] Confirm the CPU cooler is firmly mounted and does not rock.
- [ ] Confirm mounting screws appear evenly tightened.
- [ ] Do not overtighten further merely “to be safe.”
- [ ] Confirm thermal paste was applied during assembly.
- [ ] Confirm the CPU fan cable is connected to `CPU_FAN`.
- [ ] Confirm the CPU fan cable cannot touch the fan blades.

#### D. RAM

- [ ] Confirm both 32 GB modules are installed in the motherboard’s two DIMM slots.
- [ ] Press only as needed to confirm each module is fully latched.
- [ ] Confirm the modules are level and evenly seated.
- [ ] Do not enable EXPO before baseline stability is established.

#### E. NVMe

- [ ] Confirm the Samsung 990 PRO is fully inserted and secured.
- [ ] Confirm the motherboard M.2 heatsink is installed if that slot uses one.
- [ ] Confirm any required thermal-pad protective film was removed.
- [ ] Confirm no M.2 screw is loose.

#### F. GPU

- [ ] Confirm the RTX 5070 Ti is fully inserted into the PCIe riser or slot arrangement used by the Terra.
- [ ] Confirm the retention latch and case screws are secure.
- [ ] Confirm the GPU does not visibly sag into a fan or cable.
- [ ] Confirm the 16-pin GPU power connector is completely inserted with no visible gap.
- [ ] Prefer the native PSU GPU cable supplied for the SF1000 when applicable.
- [ ] Confirm the cable is not sharply bent immediately at the GPU connector.
- [ ] Confirm the GPU fans can rotate freely.

#### G. Front panel and I/O

- [ ] Confirm the case power-switch connector is installed on the correct motherboard pins.
- [ ] Confirm front USB cables are fully seated and not strained.
- [ ] Confirm Ethernet is connected to the motherboard LAN port.
- [ ] Attach the motherboard Wi-Fi antennas even though Ethernet is preferred.
- [ ] Connect the wired keyboard and mouse.
- [ ] Connect the monitor to the **RTX 5070 Ti** first.
- [ ] Keep a motherboard video-output cable available as a fallback; the 7900X includes basic integrated Radeon graphics.
- [ ] Leave the Ubuntu installer USB disconnected for the very first POST unless needed.

#### H. Final power check

- [ ] Confirm the PSU input-voltage arrangement is correct for the location; do not alter anything not designed for user adjustment.
- [ ] Connect the PSU power cable.
- [ ] Leave the PSU switch at `O` until ready for Milestone 1.2.
- [ ] Confirm the monitor is powered and set to the correct input.

### Expected result

The system is fully assembled, all critical connectors are latched, fans are unobstructed, the side panels close without force, and no unresolved concern remains.

### Common acceptable variations

- The spine may be in position 4 or 5 if both side panels close freely and both coolers have reasonable clearance.
- Some GPU power cables may use a manufacturer-provided adapter. Record exactly what is used.
- The monitor may require HDMI instead of DisplayPort for first POST.

### Stop conditions

Stop before power-on if:

- The 16-pin GPU connector is not fully seated.
- A modular PSU cable’s origin is uncertain.
- The cooler rocks or mounting is visibly uneven.
- A RAM latch is not engaged.
- The side panel pushes on the CPU fan or GPU.
- A cable touches a fan.
- The NVMe thermal pad still has protective film.
- The GPU or riser is not securely seated.
- Any connector location is uncertain.

### ChatGPT Checkpoint

> I am completing Arc 1, Milestone 1.1 of `Photo_Organizer_Server_Build_and_Deployment_Guide_v1.0.md`.
> 
> My Terra spine position is:
> 
> My CPU cooler is connected to:
> 
> My GPU power connection uses:
> 
> I verified the 24-pin motherboard power:
> 
> I verified the CPU EPS power:
> 
> I verified both RAM modules:
> 
> I verified the Samsung 990 PRO:
> 
> I verified the GPU and 16-pin connector:
> 
> Side panels close without pressure:
> 
> Cables clear all fans:
> 
> Concerns, photographs, or uncertainties:
> 
> Please verify whether it is safe to perform first power-on.

---

## Milestone 1.2 — First Power-On and POST

### Objective

Confirm the system reaches BIOS and recognizes the essential hardware.

### Before pressing power

- [ ] Milestone 1.1 is complete.
- [ ] Monitor is connected to the GPU and set to the correct input.
- [ ] Keyboard and mouse are connected.
- [ ] Ethernet is connected.
- [ ] No installer USB is connected.
- [ ] Side panels may remain off for observation.
- [ ] PSU switch is changed from `O` to `I`.

### First-start procedure

1. Press the case power button once.
2. Observe fans and motherboard diagnostic indicators.
3. Do not repeatedly press the power button.
4. Allow several minutes for first DDR5 memory training.
5. Watch for video output.
6. Press `Delete` or `F2` repeatedly when the ASUS logo appears.
7. Enter BIOS/UEFI setup.

### Expected first-start behavior

- Fans may change speed.
- The system may appear inactive during memory training.
- It may restart automatically one or more times.
- Diagnostic lights may move among CPU, DRAM, VGA, and BOOT checks.
- The absence of an operating system may produce a boot-device message after POST; that is acceptable.

### BIOS items to record

- BIOS version: __________________________
- CPU shown: _____________________________
- CPU cores/threads, if shown: ___________
- Memory total: __________________________
- Memory speed at default: ______________
- Samsung 990 PRO detected: Yes / No
- GPU detected or display active: Yes / No
- CPU fan RPM: __________________________
- CPU temperature at BIOS entry: ______°C
- CPU temperature after five minutes: ___°C
- Date/time reasonably correct: Yes / No
- Diagnostic light remaining on: _________

### Expected minimum result

- CPU identified as Ryzen 9 7900X
- 64 GB RAM detected
- Samsung 990 PRO detected
- CPU fan reports RPM
- Stable BIOS display
- No persistent CPU, DRAM, or VGA diagnostic fault
- Temperature stable rather than rising rapidly

### Temperature guidance

The 7900X can operate up to 95°C under managed load, but BIOS is not a sustained workload. During this first inspection:

- A moderate BIOS temperature is expected in a compact build.
- A slowly stable temperature is more important than an exact number.
- Stop if temperature rises rapidly toward 90°C.
- Power down if the CPU fan reports zero RPM.
- Do not run a stress test in BIOS.

### If there is no display

1. Wait through possible memory training.
2. Confirm monitor input.
3. Try the other GPU output type.
4. Power down normally if possible.
5. Move the monitor cable to the motherboard video output.
6. Preserve the diagnostic-light observation.
7. Do not remove parts while power is connected.

### Stop conditions

- Burning smell, smoke, sparks, or unusual electrical noise
- CPU fan does not spin
- Temperature rapidly approaches 90°C
- Persistent CPU or DRAM diagnostic indication
- Repeated uncontrolled reboot loop
- No display after a reasonable memory-training interval and basic cable/input checks
- Only 32 GB RAM detected
- Samsung 990 PRO absent
- GPU fault remains indicated

### Completion checklist

- [ ] BIOS reached.
- [ ] Ryzen 9 7900X detected.
- [ ] 64 GB RAM detected.
- [ ] Samsung 990 PRO detected.
- [ ] CPU fan RPM detected.
- [ ] Temperature is stable.
- [ ] BIOS version recorded.
- [ ] No unresolved diagnostic indicator remains.
- [ ] EXPO remains disabled/default.
- [ ] No overclocking changes made.

### ChatGPT Checkpoint

> I completed Arc 1, Milestone 1.2.
> 
> Time allowed for first memory training:
> 
> BIOS version:
> 
> CPU:
> 
> RAM total and reported speed:
> 
> NVMe:
> 
> GPU/display result:
> 
> CPU fan RPM:
> 
> CPU temperature at entry:
> 
> CPU temperature after five minutes:
> 
> Diagnostic lights:
> 
> Unexpected behavior:
> 
> Please tell me whether POST is validated and whether I should continue to the BIOS-baseline milestone.

---

## Milestone 1.3 — BIOS Baseline and Update Decision

### Objective

Record a stable firmware baseline and decide whether a BIOS update is justified.

### Policy

Do not flash BIOS merely because a newer version exists. Review the current version, ASUS release notes, CPU/memory compatibility, security fixes, and known issues.

### Baseline settings to inspect

- [ ] UEFI boot mode enabled
- [ ] Legacy/CSM not deliberately enabled
- [ ] Secure Boot state recorded
- [ ] AMD virtualization/SVM availability recorded
- [ ] Resizable BAR state recorded
- [ ] CPU fan monitoring enabled
- [ ] Fan profile recorded
- [ ] Restore-on-AC-power-loss setting recorded
- [ ] Wake-on-LAN decision recorded
- [ ] EXPO remains disabled
- [ ] Precision Boost Overdrive remains Auto/default
- [ ] No manual voltage or overclock set

### BIOS update decision record

- Current BIOS: ______________________
- Latest reviewed BIOS: ______________
- Release-note date: _________________
- Relevant fixes: ____________________
- Update required now: Yes / No / Defer
- Reason: ____________________________
- Recovery method reviewed: __________
- Stable power available: Yes / No

### Update prerequisites

- Known-good USB drive
- Correct BIOS file for the exact B650E-I model
- Stable power
- ASUS instructions reviewed
- BIOS FlashBack method understood
- Current settings photographed or recorded
- No interruption during update

### Stop conditions

- Exact motherboard model is uncertain.
- BIOS file model does not match.
- Power is unstable.
- Update method is not understood.
- Release notes do not justify the update.
- The system is already unstable for an unexplained reason.

### Completion

- [ ] BIOS baseline recorded.
- [ ] Update decision documented.
- [ ] If updated, POST was revalidated.
- [ ] Defaults were loaded where instructed by ASUS.
- [ ] EXPO remains deferred.
- [ ] No unrecorded tuning was performed.

---

## Milestone 1.4 — Baseline Hardware Stability and Thermal Plan

### Objective

Establish a safe operating plan for the 7900X in the Terra before production workloads.

### Initial policy

- Stock/default BIOS behavior for installation and basic validation
- EXPO disabled until OS and memory tests are stable
- No CPU overclock
- No undervolt or Curve Optimizer during first baseline
- No long stress test until temperature monitoring is installed
- Later compare:
  - Default power behavior
  - 105 W Eco Mode or equivalent controlled power limit
  - Optional 65 W mode only if noise/temperature goals require it

### Evidence to collect after Ubuntu is installed

- Idle CPU temperature
- Temperature during package updates
- Temperature during a controlled multicore load
- CPU frequency behavior
- Fan noise
- Thermal throttling status
- System stability
- Power consumption if measurable

### Decision principle

For this server, reliable 24/7 behavior and manageable acoustics matter more than extracting the final percentage of benchmark performance.

---

# Arc 2 — Ubuntu Installation and Network Identity

## Milestone 2.1 — Create Ubuntu Installation and Recovery Media

### Objective

Create verified bootable Ubuntu Server 24.04 LTS media without erasing the wrong USB device.

### Checklist

- [ ] Download Ubuntu Server 24.04 LTS from Ubuntu’s official server-download page.
- [ ] Record exact point release: __________________
- [ ] Record ISO filename: ________________________
- [ ] Record download date: ______________________
- [ ] Optionally verify the published SHA256 checksum.
- [ ] Use a USB drive whose contents may be erased.
- [ ] Verify the USB drive letter and capacity in Windows.
- [ ] Use Rufus or another approved imaging tool.
- [ ] Select GPT and UEFI when prompted and appropriate.
- [ ] Do not select the Samsung 990 PRO or another data drive.
- [ ] Label the completed USB.
- [ ] Create or preserve a separate recovery USB plan.

### Stop condition

Stop before writing if the target USB cannot be identified with certainty.

---

## Milestone 2.2 — Install Ubuntu Server

### Objective

Install Ubuntu Server to the Samsung 990 PRO with OpenSSH enabled.

### Installation decisions

| Item                    | Initial decision                               |
| ----------------------- | ---------------------------------------------- |
| Version                 | Ubuntu Server 24.04 LTS                        |
| Architecture            | amd64                                          |
| Installation target     | Samsung 990 PRO 2 TB                           |
| Network                 | Wired Ethernet                                 |
| Wi-Fi                   | Fallback only                                  |
| Hostname                | `photo-server` unless changed before install   |
| Disk encryption         | DECISION REQUIRED before storage screen        |
| LVM                     | Review installer default; record final choice  |
| OpenSSH                 | Install                                        |
| Ubuntu Pro              | Defer unless deliberately chosen               |
| Optional snaps/packages | Do not add unnecessary packages during install |
| Full desktop            | Do not install                                 |

### Destructive-storage warning

> The storage screen can erase disks. Confirm the selected disk by model and capacity before approving changes.

### Installer sequence

- [ ] Language
- [ ] Keyboard
- [ ] Installer update decision
- [ ] Standard Ubuntu Server installation
- [ ] Ethernet interface and DHCP address
- [ ] Proxy blank unless specifically required
- [ ] Default official mirror
- [ ] Samsung 990 PRO selected
- [ ] Partition/LVM decision recorded
- [ ] Encryption decision recorded
- [ ] User full name recorded
- [ ] Linux username recorded
- [ ] Hostname recorded
- [ ] Strong password stored in approved password manager/location
- [ ] OpenSSH server selected
- [ ] No unnecessary optional server snaps
- [ ] Installation completes
- [ ] USB removed when instructed
- [ ] First reboot completes
- [ ] Local console login succeeds

### Values to record

- Hostname: ______________________
- Linux username: _______________
- Disk layout: ___________________
- LVM used: Yes / No
- Encryption used: Yes / No
- Initial DHCP IP: _______________
- Ubuntu point release: __________

---

## Milestone 2.3 — Initial Ubuntu Validation and Updates

Run commands one group at a time and preserve output.

```bash
hostnamectl
```

Purpose: show hostname, operating system, kernel, and architecture.  
Changes system: No.

```bash
cat /etc/os-release
uname -r
```

Purpose: confirm Ubuntu and kernel versions.  
Changes system: No.

```bash
lscpu
free -h
lsblk -o NAME,MODEL,SIZE,FSTYPE,MOUNTPOINTS
```

Purpose: confirm CPU, RAM, and disk layout.  
Changes system: No.

```bash
ip -brief address
ip route
```

Purpose: show interfaces, addresses, and default route.  
Changes system: No.

```bash
ping -c 4 1.1.1.1
ping -c 4 ubuntu.com
```

Purpose: distinguish internet routing from DNS resolution.  
Changes system: No.

```bash
timedatectl
```

Purpose: confirm time, time zone, and synchronization.  
Changes system: No.

```bash
systemctl status ssh --no-pager
```

Purpose: confirm SSH service.  
Changes system: No.

```bash
sudo apt update
sudo apt full-upgrade
```

Purpose: refresh package metadata and apply reviewed updates.  
Changes system: Yes.  
Safe to rerun: Generally yes.

```bash
sudo reboot
```

Purpose: confirm a clean reboot after updates.  
Changes system: Yes; ends the current session.

### Validation

- [ ] Hostname correct
- [ ] Ubuntu version correct
- [ ] Kernel recorded
- [ ] 12 cores/24 threads visible
- [ ] Approximately 64 GB RAM visible
- [ ] Samsung 990 PRO visible
- [ ] Ethernet interface has an address
- [ ] Default route exists
- [ ] Internet access works
- [ ] DNS works
- [ ] Time synchronization works
- [ ] SSH active
- [ ] Updates complete
- [ ] Reboot successful

---

## Milestone 2.4 — DHCP Reservation and Stable Network Identity

### Objective

Give the headless server a predictable address without manually hard-coding an Ubuntu static IP.

### Steps

```bash
ip link
```

Record Ethernet interface and MAC address.

- [ ] Open Verizon router administration.
- [ ] Find the server by hostname, current IP, or MAC.
- [ ] Create a DHCP reservation.
- [ ] Record reserved IP.
- [ ] Confirm no duplicate reservation exists.
- [ ] Reboot or renew the connection.
- [ ] Confirm the server receives the reserved address.
- [ ] Record NAS hostname and IP.
- [ ] From Windows, test `ping` by IP.
- [ ] Test hostname resolution if available.
- [ ] Record the IP as the reliable fallback.

### Network record

- Server hostname: ______________________
- Ethernet MAC: _________________________
- Reserved server IP: ___________________
- NAS hostname: _________________________
- NAS IP: _______________________________
- Router administration address: ________
- Local network range: __________________

---

## Milestone 2.5 — Remote Administration From Windows

### First SSH connection

From Windows Terminal:

```powershell
ssh <linux-username>@<server-ip>
```

Expected first-time behavior: Windows asks whether to trust the server host key.

- Verify the target IP.
- Type `yes` only when the target is correct.
- Linux does not display password characters while typing.
- Exit safely with:

```bash
exit
```

### Remote-context check

On the server:

```bash
hostname
whoami
pwd
```

These commands confirm where the terminal is running and which user is active.

### VS Code Remote SSH

- [ ] Install the official Microsoft Remote - SSH extension.
- [ ] Add the server SSH target.
- [ ] Connect using the reserved IP first.
- [ ] Confirm the bottom-left VS Code remote indicator.
- [ ] Open a remote terminal.
- [ ] Run `hostname` and `pwd`.
- [ ] Do not edit production application code directly as an unmanaged workflow.

---

# Arc 3 — Secure Headless Management Platform

## Milestone 3.1 — SSH Keys and Access Recovery

### Policy

Do not disable password authentication until:

1. Key-based login works.
2. A second independent session has confirmed it.
3. Local monitor/keyboard access remains available.
4. The private key is backed up securely.
5. Recovery steps are documented.

Windows PowerShell:

```powershell
ssh-keygen -t ed25519
```

Copy the public key using a reviewed method. Never share the private key.

Record:

- Key name: __________________________
- Public-key fingerprint: ____________
- Private-key backup location: _______
- Password authentication retained: Yes / No
- Date policy changed: _______________

---

## Milestone 3.2 — Firewall and Security Baseline

### Baseline principles

- No router port forwarding.
- Management tools available only on the home network.
- Use least privilege.
- Keep secrets outside Git.
- Review listening ports before opening firewall rules.
- Use Tailscale or another separately reviewed VPN-style solution for future remote access.

Initial commands:

```bash
sudo ss -tulpn
sudo ufw status verbose
```

Do not enable UFW until SSH access requirements and allowed ports are understood.

After review:

```bash
sudo ufw allow OpenSSH
sudo ufw enable
sudo ufw status verbose
```

Open Cockpit and application ports only when the service is installed and the LAN-only exposure is understood.

---

## Milestone 3.3 — Cockpit

```bash
sudo apt update
sudo apt install cockpit
sudo systemctl enable --now cockpit.socket
sudo systemctl status cockpit.socket --no-pager
```

Typical local address pattern:

```text
https://<server-ip>:9090
```

A local self-signed certificate warning is expected initially. Verify the IP before proceeding.

Validate:

- [ ] Login works
- [ ] CPU and memory visible
- [ ] Storage visible
- [ ] Network visible
- [ ] Logs visible
- [ ] Services visible
- [ ] Reboot control understood
- [ ] Cockpit not exposed through router port forwarding

---

## Milestone 3.4 — Linux Directory and Permissions Conventions

### Proposed platform layout

These paths are approved conceptually but must be validated before creation:

```text
/srv/compose/                 Docker Compose stacks
/srv/apps/                    Checked-out application code, where appropriate
/srv/data/                    Local persistent application data
/srv/backups/                 Local staging for selected backups
/srv/logs/                    Explicit host-side logs where required
/srv/tmp/                     Controlled temporary processing
/mnt/nas/                     NAS mount root
/mnt/nas/photo-vault/         Photo Organizer Vault mount
/mnt/nas/photo-staging/       Controlled staging/import mount
/mnt/nas/media/               Plex/Jellyfin media
/mnt/nas/app-backups/         Application backup destination
```

Rules:

- Each application receives its own directory.
- Each application receives only the NAS access it needs.
- The Photo Organizer Vault must not be a general-purpose writable share.
- Experimental applications do not share unrestricted credentials.
- Compose files remain readable and versioned.
- Secret files have restrictive permissions and are not committed.

---

# Arc 4 — Synology Storage Integration

## Milestone 4.1 — NAS Account and Share Inventory

Record before mounting:

| Purpose               | Synology share    | Linux mount                       | Access                             |
| --------------------- | ----------------- | --------------------------------- | ---------------------------------- |
| Photo Organizer Vault | DECISION REQUIRED | `/mnt/nas/photo-vault` proposed   | Controlled; policy-defined         |
| Photo staging/import  | DECISION REQUIRED | `/mnt/nas/photo-staging` proposed | Read/write as required             |
| General media         | DECISION REQUIRED | `/mnt/nas/media` proposed         | Usually read-only for media server |
| App backups           | DECISION REQUIRED | `/mnt/nas/app-backups` proposed   | Write for backup process           |
| Personal shares       | DECISION REQUIRED | Only when needed                  | Least privilege                    |

Create or identify a dedicated NAS service account. Do not use a NAS administrator account for routine mounts.

---

## Milestone 4.2 — Temporary SMB Mounts and Permission Validation

Install CIFS tools:

```bash
sudo apt update
sudo apt install cifs-utils
```

Create one mount point at a time:

```bash
sudo mkdir -p /mnt/nas/<mount-name>
```

Credentials must be stored in a root-readable credentials file, not directly in command history or Git.

Example structure:

```text
username=<nas-service-account>
password=<stored-secret>
domain=<only-if-required>
```

Set restrictive permissions:

```bash
sudo chmod 600 <credentials-file>
```

Test a temporary mount with the exact NAS share and intended read/write options.

Validation must separately prove:

- Directory listing
- Read behavior
- Write denied where read-only is required
- Write allowed only where required
- Correct Linux ownership/mapping
- Correct behavior for filenames with spaces and Unicode

Stop if the Vault unexpectedly permits broad write access.

---

## Milestone 4.3 — Persistent Mounts and NAS-Unavailable Behavior

Persistent mounts will be added to `/etc/fstab` only after temporary mounts work.

Requirements:

- Network-aware mount options
- Avoid indefinite boot hangs when NAS is unavailable
- Credentials file outside the repository
- Explicit read-only option where intended
- Reboot test
- NAS-offline test
- Recovery test

Before editing:

```bash
sudo cp /etc/fstab /etc/fstab.backup-YYYYMMDD
```

After editing:

```bash
sudo mount -a
findmnt
```

Do not reboot until `sudo mount -a` completes without error.

---

## Milestone 4.4 — Vault, Staging, Media, and Backup Policies

### Photo Organizer Vault

- Managed by Photo Organizer policy
- Physical file truth
- No casual manual editing
- No Plex/Jellyfin write access
- No game-server access
- No experimental AI write access
- Backup and snapshot policy recorded

### Staging/import

- Writable only by the ingestion workflow and approved operators
- Temporary content has defined cleanup rules
- Partial downloads and failures preserve evidence
- No automatic import by unrelated services

### General media

- Separate from the Vault
- Read-only for media server unless a specific feature requires writes
- Metadata/cache stored separately from media files where practical

### Application backups

- Separate destination
- Retention recorded
- Restore tested
- Offsite replication considered

---

# Arc 5 — GPU and Container Platform

## Milestone 5.1 — NVIDIA Driver Installation and Validation

### Policy

Use Ubuntu’s supported package-management method. Do not use NVIDIA’s standalone `.run` installer unless a documented exception is approved.

First identify hardware:

```bash
lspci -nn | grep -i -E 'vga|3d|nvidia'
```

Review Ubuntu’s recommended drivers:

```bash
ubuntu-drivers devices
```

Install the approved current driver package identified at execution time. For RTX 50-series hardware, confirm whether Ubuntu recommends the open-kernel-module package.

After installation:

```bash
sudo reboot
nvidia-smi
```

Record:

- GPU model
- Driver version
- Reported CUDA compatibility
- VRAM
- Temperature
- Power state
- Errors

Do not install a full separate CUDA toolkit merely because `nvidia-smi` displays a CUDA compatibility version. Install development toolkits only when a workload requires them.

---

## Milestone 5.2 — Docker Engine and Compose

Install from Docker’s approved Ubuntu repository or another explicitly approved source.

Validate:

```bash
docker --version
docker compose version
sudo systemctl status docker --no-pager
```

Run a test container:

```bash
sudo docker run --rm hello-world
```

### Docker-group decision

Membership in the `docker` group effectively grants root-level control. Do not add users casually. Record the decision.

### Platform conventions

- One Compose stack per application or tightly coupled service group
- Fixed image versions or controlled version policy
- Restart policy documented
- Health checks where practical
- Persistent data clearly mapped
- Log rotation configured
- No privileged containers without explicit justification
- No host network mode without explicit justification
- Backups cover persistent data, not disposable containers

---

## Milestone 5.3 — NVIDIA Container Toolkit

Install from NVIDIA’s official repository using the current Ubuntu instructions at execution time.

Validate with a GPU-enabled container whose image and command are selected from current NVIDIA documentation.

Success criteria:

- Container sees RTX 5070 Ti
- `nvidia-smi` works inside the container
- GPU model and memory match the host
- No runtime errors
- Docker restarts cleanly

---

## Milestone 5.4 — Portainer

Deploy with Docker Compose, not an undocumented one-off command, where practical.

Requirements:

- Persistent Portainer data
- Strong administrator credentials
- Local-network-only access
- Backup of persistent data
- Compose files remain authoritative
- No important production stack exists only as manual Portainer form data

Validate:

- Stacks visible
- Containers visible
- Logs visible
- Start/stop controls understood
- Resource use visible
- Portainer data location recorded

---

## Milestone 5.5 — Monitoring and Resource Baseline

Initial tools:

- Cockpit for system health
- Docker/Portainer for containers
- `journalctl` for system services
- `nvidia-smi` for GPU
- `df`, `du`, and `findmnt` for storage
- PostgreSQL health checks
- Photo Organizer health endpoints

Record baseline:

- CPU idle temperature
- CPU controlled-load temperature
- GPU idle temperature
- RAM use
- Swap configuration
- NVMe free space
- Docker disk use
- NAS mount status
- Typical Photo Organizer idle resource use

Grafana/Prometheus may be added later; they are not required for first production cutover.

---

# Arc 6 — Photo Organizer Deployment Preparation

## Milestone 6.1 — Inventory the Windows Environment

Before migration, record:

- Repository URL
- Current branch
- Git status
- Latest approved commit
- Release tags
- Docker Compose files
- Environment-variable names
- Secret locations
- PostgreSQL version
- Database names and roles
- Redis role and persistence
- NAS paths
- Vault path
- Staging and Drop Zone paths
- Runtime scripts
- Backend/frontend ports
- Worker processes
- ExifTool and FFmpeg requirements
- Python version
- Node.js version
- Scheduled jobs
- Current backups
- GPU dependencies
- Existing health-check scripts

Do not assume copying the application directory reproduces the production environment.

---

## Milestone 6.2 — Finalize Server Deployment Architecture

Define:

- Which components run in containers
- Which code is built into images
- Which host paths are mounted
- Which services start automatically
- Which networks are internal
- Which ports are exposed to the LAN
- Health checks
- Startup order
- Resource limits
- Database backup method
- Log locations
- Upgrade and rollback process

Preserve:

- Vault immutability
- PostgreSQL operational truth
- Source identity
- Provenance
- Exact duplicate behavior
- Near-duplicate grouping
- Controlled ingestion
- Development/production separation

---

## Milestone 6.3 — Git-Based Server Deployment

Proposed controlled workflow:

```bash
sudo mkdir -p /srv/apps/photo-organizer
sudo chown <deployment-user>:<deployment-group> /srv/apps/photo-organizer
```

Authenticate to GitHub with a reviewed method, preferably a scoped deploy key or another controlled credential.

```bash
git clone <repository-url> /srv/apps/photo-organizer
cd /srv/apps/photo-organizer
git fetch --all --tags
git checkout <approved-tag-or-commit>
git status
git rev-parse HEAD
```

Rules:

- No uncommitted production-code edits
- Production `.env` not committed
- Exact deployed commit recorded
- Compose configuration validated before start
- Images built before production activation
- Rollback commit/tag known

---

## Milestone 6.4 — Photo Organizer Production Configuration

Configure and validate:

- PostgreSQL connection
- Redis connection
- Backend URL
- Frontend URL
- CORS/host settings
- Worker configuration
- GPU access
- Model paths
- ExifTool
- FFmpeg
- NAS Vault mount
- Staging path
- Drop Zone path
- Source-profile behavior
- Logging
- Health checks
- Restart policy
- Secret permissions

No large job is allowed during first startup.

---

## Milestone 6.5 — PostgreSQL Migration Plan

### Conservative process

1. Identify source database and version.
2. Quiesce or stop writes.
3. Create a verified logical backup.
4. Record backup size and optional checksum.
5. Transfer backup safely.
6. Create destination database and roles.
7. Restore.
8. Apply or verify migrations.
9. Compare key row counts.
10. Validate representative records.
11. Preserve source database.
12. Define rollback.
13. Do not delete old production.

Required evidence:

- Backup command
- Backup filename
- Backup size
- Checksum, if used
- Source PostgreSQL version
- Destination PostgreSQL version
- Restore log
- Row-count comparison
- Application validation

---

## Milestone 6.6 — Redis Migration Decision

Determine whether Redis contains:

- Disposable cache
- Rebuildable queues
- Durable job state
- Scheduled work
- Important runtime state

Decision options:

- Recreate empty
- Drain queues, then recreate
- Backup and migrate
- Preserve source only for rollback

Do not blindly copy Redis state.

---

# Arc 7 — Startup, Validation, and Production Cutover

## Milestone 7.1 — First Controlled Startup

Start in dependency order:

1. PostgreSQL
2. Redis
3. Backend
4. Worker
5. Frontend
6. Optional supporting services

Validate each before starting the next.

Check:

- Container health
- Logs
- Database connectivity
- Redis connectivity
- NAS mounts
- GPU access
- Backend health endpoint
- Frontend browser access
- No repeated restart loops
- No unexpected Vault writes

---

## Milestone 7.2 — Read-Only and Small Reversible Validation

Validation order:

- Read-only browser navigation
- Representative photo retrieval
- Thumbnails
- Metadata
- People
- Events
- Places
- Albums
- Search
- Source profiles
- Ingestion controls without execution
- One controlled staging test
- One small ingestion test
- Exact duplicate test
- Provenance test
- Face-processing test
- GPU test
- Service restart test
- Full server reboot
- NAS reconnect
- Backup test

Every test has explicit pass/fail evidence.

---

## Milestone 7.3 — Database Migration and Final Synchronization

- [ ] Maintenance window begins.
- [ ] Old production writes stopped.
- [ ] Final database backup created.
- [ ] Final transfer verified.
- [ ] Destination restore completed.
- [ ] Migrations verified.
- [ ] Counts and representative records validated.
- [ ] New server starts with final data.
- [ ] Old environment remains intact and stopped.
- [ ] Rollback command/process ready.

---

## Milestone 7.4 — Production Cutover

Record:

- Cutover date/time
- Authoritative production host
- Git commit/tag
- Database backup
- Compose versions
- Health checks
- NAS mounts
- GPU validation
- Browser validation
- Operator
- Rollback path

Do not erase the old environment.

---

## Milestone 7.5 — Stabilization

During stabilization:

- Review errors daily
- Check disk space
- Check database backups
- Check NAS mounts
- Check CPU and GPU temperatures
- Check container restarts
- Avoid unrelated new applications
- Avoid major upgrades
- Preserve rollback until confidence criteria are met

Rollback retirement requires an explicit recorded decision.

---

# Arc 8 — Operations, Expansion, Backup, and Recovery

## Milestone 8.1 — Development and Deployment Workflow

1. Develop on Windows.
2. Run tests.
3. Commit.
4. Push to GitHub.
5. Select approved commit/tag.
6. Deploy to server.
7. Rebuild or restart only affected services.
8. Validate.
9. Record deployment.
10. Roll back if validation fails.

VS Code Remote SSH is for inspection, configuration, logs, and guided administration—not undocumented production-code editing.

---

## Milestone 8.2 — Backup and Restore Testing

Back up:

- PostgreSQL
- Compose files
- Environment-file templates
- Secure secret backup reference
- Application persistent volumes
- Portainer data
- System inventory
- Deployment records
- NAS configuration
- Future Plex/Jellyfin metadata
- Game saves
- Monitoring configuration

Remember:

- RAID/SHR is not a backup.
- Snapshots are not the only backup.
- A backup is not proven until restoration is tested.
- The planned Oregon NAS is a disaster-recovery destination, not a substitute for local snapshots and backups.

---

## Milestone 8.3 — UPS and Power Recovery

Record:

- UPS model
- Server connection
- NAS connection
- Runtime estimate
- Shutdown threshold
- NAS UPS integration
- Ubuntu UPS service
- BIOS restore-on-power setting
- Startup order after power returns
- Test date
- Test result

---

## Milestone 8.4 — Routine Operations

### Weekly

- [ ] Review failed services
- [ ] Review backup status
- [ ] Review free space
- [ ] Review major application errors
- [ ] Confirm NAS mounts

### Monthly

- [ ] Review Ubuntu updates
- [ ] Review container updates
- [ ] Review Docker disk use
- [ ] Review database backups
- [ ] Review UPS health
- [ ] Review CPU/GPU temperatures
- [ ] Confirm recovery media
- [ ] Update this guide

### Quarterly

- [ ] Test PostgreSQL restore
- [ ] Test one configuration restore
- [ ] Review accounts
- [ ] Review firewall rules
- [ ] Review listening ports
- [ ] Review unused applications
- [ ] Review storage trends
- [ ] Review offsite backup status
- [ ] Review disaster-recovery readiness

---

## Milestone 8.5 — Future Application Intake

Every new application must document:

- Purpose
- Owner
- Image source and version
- Ports
- Volumes
- NAS access
- CPU/RAM/GPU needs
- Database needs
- Backup needs
- Security exposure
- Update policy
- Removal procedure
- Photo Organizer impact
- Rollback plan

Each application receives its own:

- Compose stack
- Directory
- Persistent-data location
- Environment file
- Port record
- Backup policy
- NAS permissions

---

## Milestone 8.6 — Plex or Jellyfin Planning

Review:

- Plex versus Jellyfin
- Media-share location
- Read-only media access
- Separate metadata storage
- NVIDIA transcoding
- GPU contention
- LAN and remote-access policy
- NAS and network load
- Photo Organizer processing schedule

The Photo Organizer Vault does not automatically become the writable media library.

---

## Milestone 8.7 — Local AI Planning

Review:

- Ollama
- Open WebUI
- Embedding services
- Model storage
- GPU memory
- CPU fallback
- Container isolation
- Access control
- Resource limits
- Model-update policy
- Competition with Photo Organizer GPU workloads

Experimental AI services must not exhaust resources required for production Photo Organizer work.

---

## Milestone 8.8 — Game-Server Planning

Document:

- Game
- Docker image
- CPU/RAM limits
- Persistent world data
- Backup schedule
- Port exposure
- Local-only or internet access
- Authentication
- Update schedule
- Restore process
- Scheduling around Photo Organizer
- Separate security review before public exposure

---

## Milestone 8.9 — Troubleshooting Framework

For every issue:

1. State the symptom.
2. State the last known-good condition.
3. Record recent changes.
4. Collect evidence.
5. Avoid destructive changes.
6. Verify whether the NAS and Vault are safe.
7. Establish whether local console access works.
8. Escalate with the ChatGPT template.
9. Change one controlled variable at a time.
10. Record the fix and validation.

Common symptom categories:

- No power
- No display
- Failed POST
- Missing RAM
- Missing NVMe
- High CPU temperature
- Ubuntu does not boot
- No Ethernet/IP
- SSH unavailable
- Cockpit unavailable
- Portainer unavailable
- NAS mount missing
- Docker unavailable
- Container restart loop
- PostgreSQL unavailable
- Redis unavailable
- GPU missing
- `nvidia-smi` failure
- GPU unavailable in Docker
- Frontend unavailable
- Backend health failure
- Vault unavailable
- Disk nearly full
- Unexpected slowness
- Router changed address
- Failure after update
- Power recovery failure

---

## Milestone 8.10 — Full Disaster-Recovery Rebuild

Rebuild order:

1. Replacement hardware and BIOS baseline
2. Ubuntu installation
3. Network identity
4. User and SSH restoration
5. Security baseline
6. Cockpit
7. Directory structure
8. NAS mounts
9. NVIDIA driver
10. Docker and Compose
11. NVIDIA Container Toolkit
12. Portainer
13. Compose-stack restoration
14. Secrets restoration
15. PostgreSQL restoration
16. Application-volume restoration
17. Photo Organizer validation
18. Future-application restoration
19. Production cutover
20. Recovery record

The rebuild must not depend on undocumented memory.

---

# Appendix A — Configuration Record

- Server hostname: ______________________________________
- Ethernet MAC: _________________________________________
- Reserved IP: __________________________________________
- Router administration address: ________________________
- Local network range: __________________________________
- NAS hostname: _________________________________________
- NAS IP: _______________________________________________
- Ubuntu version: _______________________________________
- Kernel version: _______________________________________
- BIOS version: _________________________________________
- Docker version: _______________________________________
- Compose version: ______________________________________
- NVIDIA driver: ________________________________________
- CUDA compatibility reported: __________________________
- Cockpit address: ______________________________________
- Portainer address: ____________________________________
- Photo Organizer address: ______________________________
- PostgreSQL version: ___________________________________
- Redis version: ________________________________________
- Deployment directory: _________________________________
- NAS mount points: _____________________________________
- Backup locations: _____________________________________
- UPS: __________________________________________________

---

# Appendix B — Service and Port Registry

| Service                  | Purpose                   | Port/protocol         | Exposure                 | Authentication           | Stack/data                |
| ------------------------ | ------------------------- | --------------------- | ------------------------ | ------------------------ | ------------------------- |
| SSH                      | Server administration     | 22/TCP unless changed | LAN/private VPN          | SSH key/password policy  | Host                      |
| Cockpit                  | Browser system management | 9090/TCP typical      | LAN only                 | Linux account            | Host                      |
| Portainer                | Docker visibility         | VALUE TO RECORD       | LAN only                 | Portainer account        | Compose/persistent volume |
| Photo Organizer frontend | User interface            | VALUE TO RECORD       | LAN                      | App policy               | Photo Organizer           |
| Photo Organizer backend  | API                       | VALUE TO RECORD       | Internal/LAN as designed | App policy               | Photo Organizer           |
| PostgreSQL               | Operational database      | 5432/TCP typical      | Internal only            | DB role                  | Photo Organizer           |
| Redis                    | Queue/cache               | 6379/TCP typical      | Internal only            | Configured secret/policy | Photo Organizer           |

Do not open a port merely because it appears in this registry.

---

# Appendix C — Application Inventory

| Application     | Status            | Version | Compose stack | Data location | Backup |
| --------------- | ----------------- | ------- | ------------- | ------------- | ------ |
| Photo Organizer | NOT YET DEPLOYED  |         |               |               |        |
| PostgreSQL      | NOT YET DEPLOYED  |         |               |               |        |
| Redis           | NOT YET DEPLOYED  |         |               |               |        |
| Cockpit         | NOT YET INSTALLED |         | Host service  |               |        |
| Portainer       | NOT YET DEPLOYED  |         |               |               |        |
| Plex/Jellyfin   | FUTURE            |         |               |               |        |
| Ollama          | FUTURE            |         |               |               |        |
| Open WebUI      | FUTURE            |         |               |               |        |
| Game servers    | FUTURE            |         |               |               |        |

---

# Appendix D — Storage and Mount Registry

| NAS share | Linux mount | Application | Access | NAS account | Backup/snapshot |
| --------- | ----------- | ----------- | ------ | ----------- | --------------- |
|           |             |             |        |             |                 |
|           |             |             |        |             |                 |
|           |             |             |        |             |                 |

---

# Appendix E — Credential and Secret Record

Do not write actual passwords in this guide.

| Secret name                 | Purpose               | Account | Stored in | Recovery/rotation |
| --------------------------- | --------------------- | ------- | --------- | ----------------- |
| Linux account password      | Local/SSH recovery    |         |           |                   |
| SSH private key             | Remote authentication |         |           |                   |
| NAS service account         | SMB mounts            |         |           |                   |
| GitHub deploy credential    | Repository access     |         |           |                   |
| PostgreSQL password         | Database              |         |           |                   |
| Redis secret                | Redis                 |         |           |                   |
| Photo Organizer app secrets | Application           |         |           |                   |

---

# Appendix F — Safe Command Reference

| Command                      | Purpose                  | Changes system?    |
| ---------------------------- | ------------------------ | ------------------ |
| `hostnamectl`                | Host and OS identity     | No                 |
| `lscpu`                      | CPU details              | No                 |
| `free -h`                    | RAM use                  | No                 |
| `lsblk`                      | Block devices            | No                 |
| `ip -brief address`          | Network addresses        | No                 |
| `ip route`                   | Routing                  | No                 |
| `timedatectl`                | Time state               | No                 |
| `df -h`                      | Filesystem free space    | No                 |
| `findmnt`                    | Active mounts            | No                 |
| `systemctl status <service>` | Service status           | No                 |
| `journalctl -u <service>`    | Service logs             | No                 |
| `sudo apt update`            | Refresh package metadata | Yes, metadata only |
| `sudo apt full-upgrade`      | Install updates          | Yes                |
| `sudo reboot`                | Reboot server            | Yes                |
| `sudo shutdown -h now`       | Shut down                | Yes                |
| `docker ps`                  | Running containers       | No                 |
| `docker compose ps`          | Stack status             | No                 |
| `docker compose logs`        | Stack logs               | No                 |
| `docker system df`           | Docker disk use          | No                 |
| `nvidia-smi`                 | GPU/driver status        | No                 |

Potentially destructive commands such as `rm`, `mkfs`, `fdisk`, `parted`, `docker system prune`, database drops, and recursive permission changes require case-specific review and are intentionally not provided as casual reference commands.

---

# Appendix G — ChatGPT Troubleshooting Template

> Guide: `Photo_Organizer_Server_Build_and_Deployment_Guide_v1.0.md`
> 
> Arc and milestone:
> 
> Exact step:
> 
> Intended action:
> 
> Exact command, if any:
> 
> Expected result:
> 
> Actual result:
> 
> Complete error text:
> 
> Relevant photograph/screenshot:
> 
> Recent changes:
> 
> Server reachable by ping: Yes / No / Unknown
> 
> SSH reachable: Yes / No / Not configured
> 
> Local monitor and keyboard available: Yes / No
> 
> NAS reachable: Yes / No / Not tested
> 
> Vault data believed safe: Yes / No / Uncertain
> 
> Photo Organizer still running: Yes / No / Not deployed
> 
> Secrets removed from evidence: Yes / No
> 
> Please identify the safest next diagnostic step. Do not suggest destructive repair before the evidence is reviewed.

---

# Appendix H — Deployment Record

- Application/version: ___________________________________
- Git branch: ___________________________________________
- Git commit: ___________________________________________
- Git tag: ______________________________________________
- Deployment date/time: _________________________________
- Operator: _____________________________________________
- Database backup: ______________________________________
- Services changed: _____________________________________
- Images/versions: ______________________________________
- Validation performed: _________________________________
- Result: _______________________________________________
- Rollback target: ______________________________________
- Rollback result, if used: ______________________________

---

# Appendix I — Maintenance and Change Log

| Date       | Change/maintenance                                           | Before      | After      | Validation        | Result/rollback |
| ---------- | ------------------------------------------------------------ | ----------- | ---------- | ----------------- | --------------- |
| 2026-07-26 | Created active working guide and recorded confirmed hardware | Prompt only | Guide v1.0 | Structural review | Active          |
|            |                                                              |             |            |                   |                 |

---

# Appendix J — Glossary

**BIOS/UEFI:** Firmware that initializes hardware and starts the operating system.  
**POST:** Power-On Self-Test performed before the OS starts.  
**LTS:** Long-Term Support release with extended security maintenance.  
**Headless:** Operated without a permanently attached monitor, keyboard, or mouse.  
**SSH:** Secure remote command-line access.  
**DHCP:** Router service that assigns network addresses.  
**DHCP reservation:** Router rule that gives a device the same address based on its MAC address.  
**Static IP:** Address manually configured on the device rather than reserved by the router.  
**Hostname:** Human-readable device name, such as `photo-server`.  
**MAC address:** Hardware identifier used on a local network.  
**Docker image:** Packaged application filesystem and metadata.  
**Container:** Running instance of an image.  
**Volume:** Docker-managed persistent storage.  
**Bind mount:** Host path made available inside a container.  
**Docker Compose:** Reproducible multi-container configuration.  
**Stack:** Related group of services deployed together.  
**Port:** Numbered network endpoint used by a service.  
**Firewall:** Rules controlling permitted network traffic.  
**Reverse proxy:** Service that receives requests and routes them to internal applications.  
**TLS:** Encryption used by HTTPS and other secure protocols.  
**NAS:** Network-attached storage.  
**SMB/CIFS:** Network file-sharing protocol commonly used by Windows and Synology.  
**Mount point:** Linux directory where a filesystem or network share appears.  
**PostgreSQL:** Photo Organizer operational database.  
**Redis:** In-memory data service used for queues, caching, or runtime state.  
**CUDA:** NVIDIA GPU computing platform.  
**GPU transcoding:** Hardware conversion of media formats/resolutions.  
**Snapshot:** Point-in-time storage state; useful but not by itself a complete backup strategy.  
**RAID/SHR:** Disk redundancy that improves availability; not a backup.  
**Restore:** Recovering data or configuration from backup.  
**Rollback:** Returning to a previously known-good version or state.

---

# Official Reference Notes

The following official sources informed the initial hardware and OS decisions. Recheck current instructions at the relevant execution milestone.

- Ubuntu release lifecycle and Ubuntu Server download documentation
- Ubuntu 24.04 and 26.04 release notes
- AMD Ryzen 9 7900X product specifications
- ASUS ROG Strix B650E-I support information
- ASUS Prime RTX 5070 Ti technical specifications
- Fractal Design Terra CPU cooler/GPU support table
- Thermalright AXP90-X53 Full product specifications
- NVIDIA Linux driver guidance

---

# Current Next Action

Do **not** power on yet.

Complete **Arc 1, Milestone 1.1 — Final Physical Inspection**, record the requested values, and provide the checkpoint results before first power-on.
