# Production Release Manifest (Milestone 12.47)

Date: 2026-05-17
Scope: Define production runtime package boundaries and promotion rules.

## Classification Categories

- production runtime required
- production operator/maintenance
- development/test
- experimental
- deprecated/archive

## Production Runtime Required

- backend application code under backend/app/
- backend dependency file backend/requirements.txt
- frontend application code under frontend/src/
- frontend package metadata frontend/package.json
- Docker runtime config docker/docker-compose.yml
- profile-aware backend config loader backend/app/core/config.py
- backend health route backend/app/api/health.py
- env templates:
  - backend/.env.development.example
  - backend/.env.production.example
  - frontend/.env.production.example

## Production Operator / Maintenance

- scripts/runtime/start_photo_organizer_prod.ps1
- scripts/runtime/stop_photo_organizer.ps1
- scripts/runtime/check_runtime_health.ps1
- scripts/runtime/bootstrap_production_storage.ps1
- docs/operations/production_bootstrap.md
- docs/operations/production_runtime_baseline.md

## Development / Test

- milestone prompts under docs/prompts/
- coder response history under docs/prompts/
- validation scripts under backend/scripts/check_*.py
- test suite under backend/tests/
- development startup script scripts/runtime/start_photo_organizer_dev.ps1
- local development storage under storage/ (workspace-local)

## Experimental

- feasibility notes and one-off iCloud trial docs under docs/operations/*feasibility*
- diagnostic scripts not listed as operator-maintenance
- any script with trial/test-only intent not documented for production use

## Deprecated / Archive

- legacy references under docs/legacy_photo_organizer_docs/
- superseded milestone notes retained for history
- old validation artifacts retained for traceability

## Promotion Rules for Future Tools/Scripts

Every new tool or script must be classified as one of:
- production runtime
- production operator/maintenance
- development/test
- experimental
- deprecated

Production promotion checklist:

1. Supports explicit profile/config behavior.
2. No hardcoded development-only paths.
3. Fails loudly when required production config is missing.
4. Avoids destructive defaults.
5. Logs to production log paths without secrets.
6. Documents data-touch scope (files, DB, source registry, vault, staging).
7. Passes syntax/basic validation before promotion.
8. Uses dry-run default for risky operations when practical.
9. Is listed in this release manifest.

## Explicit Exclusions from Production Runtime Package

The production runtime package must not include or depend on:

- milestone prompt history
- coder response history
- development test data
- one-off validation artifacts
- experimental ingestion trials
- old local dev logs
- temporary debug outputs

## Dev/Prod Separation Policy

- development DB name remains photo_organizer
- production DB name is photo_organizer_prod
- Docker project namespaces:
  - development: docker (legacy dev namespace, preserves existing dev volume/data continuity)
  - production: photo-organizer-prod
  - photo-organizer-dev is a prior transitional namespace; stop script may clean it up if present
- live PostgreSQL volume remains on Windows app host local disk
- NAS is used for vault and backup targets, not live DB volume
