# Coder Response 12.35

## Milestone
Milestone 12.35: Direct iCloud Connector Staging Adapter

## Goal
Create a guarded wrapper workflow that reuses one iCloud auth session for inventory + controlled download into staging, enforces approved safety limits, and prints Source Intake handoff guidance without auto-running intake.

## What Changed

1. Added wrapper script:
- [backend/scripts/experimental/icloud_staging_adapter.py](backend/scripts/experimental/icloud_staging_adapter.py)

2. Updated operations notes for 12.35:
- [docs/operations/icloud_direct_feasibility_notes.md](docs/operations/icloud_direct_feasibility_notes.md)

## 12.35 Decisions Implemented

1. Wrapper location is under experimental scripts.
2. Source label is required (`--source-label`, no default).
3. One-session auth reuse for scan + download in a single run.
4. Hard cap guardrail:
- default hard max is 25 downloads
- limits above 25 require explicit `--allow-large-test`
5. Existing-file policy defaults to `skip` (no overwrite).
6. Read-only source registration lookup is included:
- checks source_label + source_type + source_root_path
- reports whether matching source is already registered
7. Source Intake is not auto-run:
- wrapper prints recommended Source Intake command only
8. Wrapper prints absolute staging path and experimental safety notice.

## Validation Runs

### 1. Wrapper CLI smoke test
- Command: help output for adapter
- Result: Passed

### 2. First run (new label)
Command used:
- `python scripts/experimental/icloud_staging_adapter.py --source-label chuck_icloud_direct_adapter_test --scan-limit 25 --download-limit 10 --username chhendersoniv@gmail.com`

Summary report:
- [storage/logs/icloud_connector_reports/icloud_staging_adapter_20260508T152145Z.json](storage/logs/icloud_connector_reports/icloud_staging_adapter_20260508T152145Z.json)

Key results:
1. Status: SUCCESS
2. Inventory scanned: 25
3. Download attempted: 10
4. Download successful: 10
5. Skipped existing: 0
6. Failed downloads: 0
7. Renamed for collision: 0
8. Total downloaded bytes: 109,828,545
9. Source registration check: not registered (expected read-only warning message)

Supporting reports:
- [storage/logs/icloud_connector_reports/icloud_adapter_inventory_20260508T152145Z.json](storage/logs/icloud_connector_reports/icloud_adapter_inventory_20260508T152145Z.json)
- [storage/logs/icloud_connector_reports/icloud_adapter_download_20260508T152145Z.json](storage/logs/icloud_connector_reports/icloud_adapter_download_20260508T152145Z.json)

### 3. Repeat run (same label, skip-existing proof)
Command used:
- `python scripts/experimental/icloud_staging_adapter.py --source-label chuck_icloud_direct_adapter_test --scan-limit 25 --download-limit 10 --username chhendersoniv@gmail.com`

Summary report:
- [storage/logs/icloud_connector_reports/icloud_staging_adapter_20260508T152318Z.json](storage/logs/icloud_connector_reports/icloud_staging_adapter_20260508T152318Z.json)

Key results:
1. Status: SUCCESS
2. Download attempted: 10
3. Download successful: 0
4. Skipped existing: 10
5. Failed downloads: 0
6. Renamed for collision: 0
7. Total downloaded bytes: 0
8. Existing-policy behavior confirmed as skip

Supporting report:
- [storage/logs/icloud_connector_reports/icloud_adapter_download_20260508T152318Z.json](storage/logs/icloud_connector_reports/icloud_adapter_download_20260508T152318Z.json)

## Safety Boundary Confirmation

1. Wrapper remains download-only from iCloud.
2. No direct writes to Drop Zone, Vault, DB, or provenance.
3. Source Intake remains explicit/manual handoff.
4. Source registration check is read-only.

## Milestone Closeout Checklist

### What changed
1. Added adapter wrapper script with guardrails and single-session orchestration.
2. Updated operations notes to include 12.35 workflow and options.

### How to run
1. From backend:
- `python scripts/experimental/icloud_staging_adapter.py --source-label <label> --scan-limit 25 --download-limit 10 --username <apple_id_email>`
2. Optional:
- add `--allow-large-test` only when intentionally exceeding hard max
- use `--existing-policy rename` only if collision renaming is desired

### What passed
1. Adapter CLI help validation.
2. First new-label adapter run (10 successful downloads).
3. Repeat same-label adapter run (10 skipped existing, 0 new downloads).
