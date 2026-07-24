# Photo Organizer Mini Server Build & Deployment Plan

Version: Draft v1.0

## Purpose

Build a compact, production-quality Linux server to host the Photo Organizer application and related services.

The server will provide:

- Photo Organizer backend
- Photo Organizer frontend
- PostgreSQL
- Redis
- Local AI (Ollama)
- CUDA GPU processing
- Future surveillance AI
- Web services for approximately 3–5 users
- Durable storage hosted on Synology NAS

The mini server is intended to operate headless after commissioning.

---

# Hardware

Case

- Fractal Terra

CPU

- AMD Ryzen 9 7900X
- Configure in BIOS using AMD Eco Mode (65W or 105W)

Motherboard

- ASUS ROG Strix B650E-I Gaming WiFi

Cooler

- Thermalright AXP120-X67

RAM

- 64 GB DDR5-6000 EXPO
- Future upgrade path: 96 GB

GPU

- ASUS PRIME RTX 5070 Ti OC 16 GB

SSD

- Samsung 990 Pro 2 TB

Power Supply

- Corsair SF1000 Platinum SFX

Storage

- Synology DS225+ RAID1
- Vault storage
- Database backups
- Surveillance archive

Operating System

- Ubuntu Server 24.04 LTS

---

# Overall Architecture

Windows Development PC

↓

SSH / VS Code Remote SSH

↓

Ubuntu Mini Server

↓

Docker

├── Photo Organizer Backend

├── Photo Organizer Frontend

├── PostgreSQL

├── Redis

├── Ollama

├── Nginx

├── Frigate (future)

↓

Synology NAS

- Photo Vault
- Database backups
- Snapshots
- Long-term storage

---

# Commissioning Phases

## Phase 1 — Hardware Assembly

Assemble:

- CPU
- Cooler
- RAM
- SSD
- Motherboard
- PSU
- GPU
- Case

Connect:

- Ethernet
- Temporary HDMI monitor or TV
- Temporary USB keyboard

Power on.

Verify POST.

Enter BIOS.

---

## Phase 2 — BIOS Update

Update motherboard BIOS using ASUS EZ Flash.

Verify:

- Latest BIOS installed
- Stable POST

---

## Phase 3 — BIOS Configuration

Configure:

- Enable EXPO
- Enable AMD Eco Mode
- Set CPU to 65W or 105W profile
- Enable SVM virtualization
- Enable TPM
- Enable Secure Boot
- Configure fan curves
- Verify SSD detected
- Verify GPU detected

Set boot order:

1. USB
2. NVMe SSD

Save and reboot.

---

## Phase 4 — Ubuntu Installation Media

On Windows PC:

Download:

- Ubuntu Server 24.04 LTS ISO

Create bootable USB using Rufus.

---

## Phase 5 — Install Ubuntu Server

Boot from USB.

Configure:

- Language
- Keyboard
- Time Zone
- Username
- Password
- Hostname

Suggested hostname:

photo-server

Install onto Samsung 990 Pro.

IMPORTANT

Enable:

OpenSSH Server

Complete installation.

Remove USB.

Reboot.

---

## Phase 6 — Initial Login

Login locally.

Verify:

- Ubuntu boots normally
- Ethernet working
- IP address assigned

Run:

sudo apt update

sudo apt upgrade

---

## Phase 7 — Configure Networking

Assign static DHCP reservation in router.

Suggested IP:

192.168.1.50

Verify:

ssh chuck@192.168.1.50

Once SSH works:

Disconnect monitor.

Disconnect keyboard.

The machine now operates headless.

---

## Phase 8 — NVIDIA Driver Installation

Install latest NVIDIA driver.

Reboot.

Verify:

nvidia-smi

Confirm:

- GPU detected
- Driver version
- CUDA available

---

## Phase 9 — Docker

Install:

Docker Engine

Docker Compose

Verify:

docker --version

docker compose version

---

## Phase 10 — Cockpit

Install Cockpit.

Verify:

https://photo-server:9090

Use for:

- CPU
- Memory
- Logs
- Services
- Terminal
- Updates

---

## Phase 11 — Portainer

Install Portainer.

Verify:

https://photo-server:9443

Use for:

- Docker Containers
- Docker Compose
- Volumes
- Networks
- Logs

---

## Phase 12 — NAS Integration

Mount Synology shares.

Suggested mount point:

/mnt/photo-vault

Verify:

Read

Write

Performance

Automatic mounting after reboot.

---

## Phase 13 — Install AI Stack

Install:

CUDA Toolkit

Ollama

Future:

Open WebUI

Download preferred models.

Verify GPU acceleration.

---

## Phase 14 — Deploy Photo Organizer

Clone Git repository.

Configure Docker Compose.

Deploy:

Backend

Frontend

PostgreSQL

Redis

Nginx

Verify:

Application launches.

Database connects.

NAS storage accessible.

---

## Phase 15 — Data Migration

Copy existing Windows development Vault.

Restore PostgreSQL database.

Verify:

Assets

Metadata

Faces

Events

Places

Albums

---

## Phase 16 — Production Hardening

Configure:

Automatic security updates

Firewall (UFW)

SSH keys

Disable password SSH (optional)

Docker restart policies

Scheduled PostgreSQL backups

NAS backup verification

System monitoring

UPS integration (future)

---

# Normal Workflow

Development

Windows PC

↓

VS Code

↓

Remote SSH

↓

Ubuntu Server

↓

Docker

↓

Photo Organizer

Administration

Browser

↓

Cockpit

Portainer

Photo Organizer

Synology DSM

---

# Future Services

The server is expected to eventually host:

- Photo Organizer
- Ollama
- Open WebUI
- Frigate NVR
- Home Assistant (optional)
- Reverse Proxy
- Tailscale VPN
- Surveillance AI
- Future semantic search
- Local LLM services

---

# Long-Term Storage Philosophy

Mini Server

Purpose:

Compute

Docker

Database

AI

Temporary cache

Synology NAS

Purpose:

Immutable Vault

Database backups

Snapshots

Long-term storage

Disaster recovery

---

# Recovery Philosophy

Routine administration:

- SSH
- Cockpit
- Portainer

Emergency recovery:

Reconnect temporary monitor and keyboard

or

Future PiKVM installation for full remote BIOS-level access.
