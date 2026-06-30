# Repository Housekeeping Recon Report

## Executive Summary

Read-only reconnaissance completed with program-relevance evidence.

Key outcomes:

- Root folder `14/` is tracked but has no evidence of runtime/test/docs references outside `14/`; classify as `DELETE CANDIDATE` (or archive-then-delete).
- `README.md` is stale (Milestone 9.1 workflow-centric) and should be updated to current project entry points.
- `.gitignore` is mostly strong for generated artifacts but currently ignores `.env.example` and `docker/.env.example`; also lacks explicit patterns for `.partial`, `*.db`, `*.sqlite`, `*.tmp`, `*.patch`, and `*.tsbuildinfo`.
- A generated build artifact is tracked: `frontend/tsconfig.tsbuildinfo`.
- Runtime/generated folders (`storage/`, `backend/storage/`, `.venv/`, `.next/`, `node_modules/`) are untracked and ignored as desired.

## Current Git State

- Current branch: `main`
- Branches:
  - local: `main`, `diag-icloud-candidate-visibility`
  - remote: `origin/main`
- Working tree summary: one untracked file (`docs/milestones/Repository_Housekeeping_Reconnaissance_Only_prompt.md`)
- Latest 5 commits:
  - `7fb8dea` Checkpoint: finalize working iCloud all-supported ingestion
  - `f43a3b2` Milestone 12.62.24: validate all-supported iCloud assets
  - `18a9094` Milestone 12.62.23: enable all supported iCloud assets in single-flow wrapper
  - `c08b297` Milestone 12.62.22: add internal single-flow iCloud run UI and API
  - `be021d4` Milestone 12.62.20.1: harden internal iCloud cleanup continuation recovery
- Recent `v0.12.62.*` tags include: `v0.12.62.22`, `v0.12.62.23`, `v0.12.62.24`, `v0.12.62.24.1`, and earlier 12.62.x tags.

## Root Directory Findings

Top-level items observed:

- `.agents/`, `.git/`, `.tools/`, `.venv/`, `14/`, `backend/`, `docker/`, `docs/`, `frontend/`, `scripts/`, `storage/`, `.gitignore`, `README.md`

Program-relevance classifications:

| Item | Evidence of Use | Evidence Against Use | Classification | Recommended Action | Risk |
|---|---|---|---|---|---|
| `14/` | `14/manifest.json` references files inside `14/` | `git grep -n "Photo Organizer_v1\\14\\|^14/face_|14/manifest\.json" -- . ':!14/*'` found no external references | DELETE CANDIDATE | Archive to dedicated fixtures/archive location if needed, then remove from root in cleanup branch | Medium |
| `README.md` | Canonical entrypoint file expected at root | Content is milestone 9.1-era operations workflow, not current onboarding | UPDATE | Replace with current project overview/setup/run/test/docs index | Low |
| `.gitignore` | Covers `.venv`, `node_modules`, `.next`, `storage`, `backend/storage`, logs | Missing explicit patterns for `.partial`, db/sqlite/tmp/patch/tsbuildinfo; `.env.example` currently ignored | UPDATE | Add missing patterns and explicit allowlist for `.env.example` | Low |
| `storage/` | Runtime output path used by app workflows | Should not be tracked | KEEP | Continue ignored-only policy | Low |
| `backend/storage/` | Runtime output path used by backend workflows | Should not be tracked | KEEP | Continue ignored-only policy | Low |
| `.venv/` | Local dev environment | Not source-of-truth code | KEEP (local only) | Keep ignored | Low |

## Suspicious Items

| Item | Evidence of Use | Evidence Against Use | Classification | Recommended Action | Risk |
|---|---|---|---|---|---|
| `14/face_*.jpg` + `14/manifest.json` | Tracked by Git (`git ls-files 14`) | No code/tests/docs reference outside `14/` | DELETE CANDIDATE | Archive-then-delete (or delete directly if no retention need) | Medium |
| `frontend/tsconfig.tsbuildinfo` | Tracked by Git | Build artifact; not source code | DELETE CANDIDATE | Remove from tracking and ignore `*.tsbuildinfo` | Low |
| `docs/legacy_photo_organizer_docs/photo_organizer_legacy_folder_structure_all_files.md` (~4.2MB) | Legacy documentation artifact | Very large; likely generated inventory dump; unclear current use | NEEDS USER DECISION | Keep as historical archive or move to docs/archive with note | Medium |
| `docs/milestones/*/Coder response*.md` (76 files) | Historical conversational artifacts | Not direct runtime/test inputs; high doc noise | NEEDS USER DECISION | Decide keep-as-history vs archive subset | Medium |

## README Findings

- README is stale and heavily focused on older Milestone 9.1 face-cluster correction scripts.
- Outdated emphasis:
  - milestone-specific correction workflow as primary content
  - lacks current architecture/run/test/admin-flow guidance
- Suggested replacement outline:
  1. Project overview and current capabilities
  2. Backend/frontend setup
  3. Local run commands
  4. Testing strategy and common commands
  5. Ingestion/iCloud operational summary
  6. Docs index (`docs/architecture`, `docs/context`, `docs/milestones`)
- Preserve before rewrite:
  - any still-relevant script command sequences can be moved into a dedicated workflow doc under `docs/context/`.

## Docs Findings

- Docs inventory is large (`384` files).
- Prompt/closeout organization is mostly consistent:
  - prompt files: `22`
  - closeout files: `21`
  - difference appears attributable to new untracked prompt file awaiting closeout counterpart.
- High-noise historical artifacts:
  - `Coder response*.md`: `76`
- Legacy docs subtree exists (`docs/legacy_photo_organizer_docs/`, `7` files), including one very large file.
- Recommendation:
  - keep final prompts + final closeouts for milestone history
  - define archival policy for intermediate conversational artifacts and legacy dumps
  - enforce naming convention and one prompt/one closeout parity per milestone task.

## Runtime / Generated Artifact Findings

- Untracked and ignored (good):
  - `.venv/`, `.tools/`, `frontend/.next/`, `frontend/node_modules/`, `storage/`, `backend/storage/`, `__pycache__/`
- Also ignored: temp logs like `backend/.tmp_test_all.log`, `backend/.tmp_test_icloud.log`
- Tracked generated artifact found:
  - `frontend/tsconfig.tsbuildinfo`
- Conclusion: runtime artifact protections are mostly effective, with a few pattern gaps.

## .gitignore Findings

Current coverage status:

- Python virtualenvs: covered (`.venv/`)
- Python cache files: covered (`__pycache__/`, `*.pyc`)
- Node modules: covered (`node_modules/`)
- Next.js build output: covered (`.next/`, `out/`)
- `.env` files: covered broadly (`.env`, `.env.*`)
- storage/log/export runtime dirs: covered (`storage/`, `backend/storage/`)
- OS junk: covered (`.DS_Store`, `Thumbs.db`)

Gaps:

- `.env.example` is currently ignored due `.env.*` and not re-allowed.
  - Evidence: `git check-ignore -v .env.example docker/.env.example` resolves to `.gitignore:14:.env.*`
- Missing explicit ignore patterns for:
  - `*.partial`
  - `*.db`, `*.sqlite`
  - `*.tmp`, `*.patch`
  - `*.tsbuildinfo`

## Large File / Media Findings

Largest tracked files (top sample):

1. `docs/legacy_photo_organizer_docs/photo_organizer_legacy_folder_structure_all_files.md` — 4,218,745 bytes
2. `docs/legacy_photo_organizer_docs/photo_organizer_legacy_folder_structure.md` — 202,861 bytes
3. `frontend/package-lock.json` — 196,507 bytes
4. `frontend/src/components/IngestionView.tsx` — 193,055 bytes
5. `14/face_29__asset_7a361a4ba64e__Portraits-387(1).jpg` — 167,394 bytes

Tracked media files found in root `14/` only (from the requested pattern set):

- `14/face_13__asset_c76217e9143f__IMG_0727(1).jpg`
- `14/face_16__asset_9328a21c93a2__IMG_0873(1).jpg`
- `14/face_27__asset_f6319a85403a__Portraits-387_low(1).jpg`
- `14/face_29__asset_7a361a4ba64e__Portraits-387(1).jpg`
- `14/face_30__asset_52df2153e980__Portraits-crop(1).jpg`
- `14/face_44__asset_96c620fb1c8f__010101e9b7df5b3af24311adbf554b92e464c425af(1).jpg`

## Test Fixture Findings

Requested `14/` checks:

1. Is anything outside `14/` referencing `14/`?
   - No external references found by targeted grep.
2. Is any test referencing `14/` or its files?
   - No evidence found.
3. Is the manifest referenced by code/tests/docs outside `14/`?
   - No evidence found.
4. Is `14/` documented as a fixture?
   - No explicit fixture documentation found.
5. Is it needed for current app runtime?
   - No evidence found.
6. Classification if not needed:
   - `DELETE CANDIDATE` (or archive-then-delete if user wants retention).

Additional fixture observations:

- No `backend/tests/fixtures/` directory currently exists.
- Tests do reference media-like filenames and paths extensively, but mostly as synthetic strings or temporary test data, not root `14/` assets.

## Branch Findings

| Branch | Evidence | Classification | Recommended Action | Risk |
|---|---|---|---|---|
| `main` | HEAD branch, origin default | active | Keep | Low |
| `diag-icloud-candidate-visibility` | Points to tagged commit `v0.12.62.24`, behind `main` head | needs user decision | If already merged/cherry-picked and no longer needed, mark safe deletion candidate | Low |

## Recommended Cleanup Plan

| Item | Current Location | Classification | Evidence | Recommended Action | Risk |
|---|---|---|---|---|---|
| Root media bundle | `14/` | DELETE CANDIDATE | No external code/test/docs references outside `14/` | Move to archive or remove in cleanup branch | Medium |
| Stale root readme | `README.md` | UPDATE | Milestone 9.1-centric, not current onboarding | Rewrite to current setup/workflow summary | Low |
| Build artifact in Git | `frontend/tsconfig.tsbuildinfo` | DELETE CANDIDATE | Generated build output tracked | Remove from tracking; ignore pattern | Low |
| Env example ignore issue | `.gitignore` | UPDATE | `.env.example` currently ignored | Add `!.env.example` and `!**/.env.example` rules | Low |
| Missing generated-file ignores | `.gitignore` | UPDATE | No explicit patterns for partial/db/sqlite/tmp/patch/tsbuildinfo | Add targeted ignore rules | Low |
| Legacy large inventory doc | `docs/legacy_photo_organizer_docs/photo_organizer_legacy_folder_structure_all_files.md` | NEEDS USER DECISION | 4.2MB, likely generated inventory | Keep as archive or move/trim | Medium |
| Conversational artifact docs | `docs/milestones/**/Coder response*.md` | NEEDS USER DECISION | 76 files, high noise | Decide retention policy; archive if needed | Medium |

## Items Requiring User Decision

1. Keep/archive/delete strategy for root `14/` bundle.
2. Keep/archive strategy for `Coder response*.md` milestone artifacts.
3. Keep vs archive strategy for very large legacy inventory doc.
4. Whether to retain `diag-icloud-candidate-visibility` branch after verification.

## Proposed Follow-Up Milestones or Cleanup Commits

Safe branch approach (no history rewrite):

1. Create cleanup branch from `main` (example: `housekeeping/repo-cleanup-pass1`).
2. Commit 1: docs hygiene only
   - update `README.md`
   - add housekeeping policy doc under `docs/context/`
3. Commit 2: ignore hardening only
   - adjust `.gitignore` for `.env.example`, `*.partial`, db/sqlite/tmp/patch/tsbuildinfo
4. Commit 3: generated artifact untracking only
   - stop tracking `frontend/tsconfig.tsbuildinfo`
5. Commit 4: root artifact decision
   - archive or remove `14/` based on user decision
6. Commit 5: optional docs archival pass
   - archive conversational milestone artifacts per explicit retention policy

Suggested verification after each commit:

- `git status --short`
- targeted smoke tests (backend/frontend start)
- spot-check docs links/navigation

Recon boundary confirmation:

- No files were modified, moved, deleted, staged, committed, or tagged during this reconnaissance.

## Cleanup Action 1 - .gitignore Hardening

Scope confirmation for this action:

- Executed on branch: housekeeping/repo-cleanup-pass1
- Changed files in this action: .gitignore and this closeout file only
- No edits to README
- Did not touch 14/
- Did not remove frontend/tsconfig.tsbuildinfo
- No file deletes, moves, commit, or tag

### Exact .gitignore Changes Made

Added/updated sections:

- Python:
  - added .pytest_cache/
  - added .mypy_cache/
- Node / Next.js:
  - added *.tsbuildinfo
- Env files:
  - kept .env and .env.* ignored
  - added allowlist for examples:
    - !.env.example
    - !**/.env.example
    - !.env.*.example
    - !**/.env.*.example
- Logs / temp files:
  - kept *.log
  - added *.tmp, *.patch, *.bak
- Databases:
  - added *.db, *.sqlite, *.sqlite3
- Partial/interrupted downloads:
  - added *.partial
- Runtime storage:
  - preserved storage/ and backend/storage/
- Vision models:
  - preserved backend/app/services/vision/models/

Removed duplicate/noisy entries:

- removed duplicate trailing .env entry
- removed redundant separate onnx line because the enclosing models directory ignore already covers it

### Verification Commands Run

Commands executed exactly as requested:

- git diff -- .gitignore
- git check-ignore -v .env.example
- git check-ignore -v docker/.env.example
- git check-ignore -v .env.local
- git check-ignore -v backend/storage/logs/example.json
- git check-ignore -v test.partial
- git check-ignore -v frontend/tsconfig.tsbuildinfo
- git status

### Verification Results

- .env.example: NOT ignored
  - matched unignore rule: .gitignore line with !**/.env.example
- docker/.env.example: NOT ignored
  - matched unignore rule: .gitignore line with !**/.env.example
- .env.local: ignored
  - matched ignore rule: .env.*
- backend/storage/logs/example.json: ignored
  - matched ignore rule: backend/storage/
- test.partial: ignored
  - matched ignore rule: *.partial
- frontend/tsconfig.tsbuildinfo:
  - check-ignore produced no output (expected for a tracked file path in many Git workflows)
  - ignore rule exists in .gitignore: *.tsbuildinfo

### Unexpected Behavior

- One pre-existing working-tree modification was present and unrelated to this action:
  - docs/milestones/Repository_Housekeeping_Reconnaissance_Only_prompt.md showed as modified before/after verification.
- docker/.env.example appears as untracked after allowlisting, which is expected once it is no longer ignored.

### Final Changed File List

- .gitignore
- docs/milestones/Repository_Housekeeping_Reconnaissance_Only_closeout.md