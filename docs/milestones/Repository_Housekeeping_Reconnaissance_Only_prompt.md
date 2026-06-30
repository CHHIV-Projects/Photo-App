# Repository Housekeeping Reconnaissance Only

We are doing repository housekeeping after stabilizing iCloud all-supported ingestion.

This is **reconnaissance only**.

Do **not** modify files.  
Do **not** delete files.  
Do **not** move files.  
Do **not** edit `.gitignore`.  
Do **not** edit `README.md`.  
Do **not** commit or tag.  
Do **not** run destructive cleanup commands.

The goal is to inspect the repository and produce a clear cleanup audit/report.

## Context

The repo has accumulated older files, milestone artifacts, prompt/closeout docs, runtime logs, possible test/export artifacts, and possibly stale root-level files. Example concerns:

- root folder `14/` appears to contain face image files and a `manifest.json`

- root `README.md` may be stale and reference old milestone 9.1-era information

- prompts and closeouts are currently committed under `docs/`

- runtime/generated artifacts should generally not be committed

- `.gitignore` should prevent storage/log/export/temp artifacts from entering Git

- we need to preserve useful project history while reducing clutter

Current desired repo policy, subject to audit:

```text
Keep:
- current source code
- tests
- intentional test fixtures
- architecture/context/workflow docs
- final milestone prompts if useful for handoff/history
- final milestone closeouts
- README, but updated to current project state

Do not keep:
- backup patches
- temporary scratch files
- generated runtime logs
- iCloud export/staging files
- .partial files
- actual user photo/media output unless intentionally used as test fixture
- duplicate prompt drafts
- stale root-level artifacts with no references
```

## Required Recon Tasks

### 1. Branch and Git State

Report:

```text
current branch
git status summary
latest 5 commits
recent tags related to v0.12.62.*
whether working tree is clean or has uncommitted files
```

Do not commit anything.

### 2. Root Directory Audit

List top-level files and folders.

For each suspicious root item, classify as:

```text
KEEP
UPDATE
MOVE
DELETE CANDIDATE
NEEDS USER DECISION
```

Pay special attention to:

```text
14/
README.md
.gitignore
any loose .patch files
any loose prompt/closeout files
any unexpected media files
any generated files
```

For `14/`, determine:

```text
what files are inside
approximate file count and file types
whether anything references it
whether tests depend on it
whether it appears to be a fixture, old export, milestone evidence, or accidental artifact
recommended action
```

Use read-only commands such as:

```powershell
Get-ChildItem
git ls-files
git status --ignored -s
git grep
```

### 3. README Audit

Inspect `README.md`.

Report:

```text
whether README is stale
what outdated milestones or instructions it references
what sections should be replaced
recommended current README outline
whether any information should be preserved elsewhere before rewriting
```

Do not edit README.

### 4. Docs Folder Audit

Inspect the `docs/` structure.

Report:

```text
current docs folders
milestone prompt/closeout organization
duplicate or draft-looking docs
large docs or pasted terminal-output docs
whether prompts and closeouts are consistently named
recommendation on keeping final prompts and final closeouts
recommended docs organization policy
```

Specifically identify any files that look like:

```text
temporary prompts
backup copies
duplicate closeouts
large pasted logs
old milestone docs no longer useful
```

Do not delete or move docs.

### 5. Runtime / Generated Artifact Audit

Check whether runtime/generated artifacts are tracked by Git.

Look for tracked or untracked files under patterns such as:

```text
backend/storage/
storage/
backend/storage/logs/
storage/logs/
backend/storage/exports/
storage/exports/
*.partial
*.log
*.tmp
*.patch
*.sqlite
*.db
frontend/.next/
node_modules/
__pycache__/
.venv/
```

Report:

```text
whether any are tracked
whether any are untracked but correctly ignored
whether .gitignore currently protects them
any missing .gitignore patterns
```

Do not force-add ignored files.  
Do not delete generated files yet.

### 6. Git Ignore Audit

Inspect `.gitignore`.

Report whether it covers:

```text
Python virtualenvs
Python cache files
Node modules
Next.js build output
.env files while preserving .env.example if applicable
storage/log/export directories
.partial files
database files
OS junk files
large generated reports
```

Recommend additions or changes, but do not edit.

### 7. Large File / Media Audit

Find tracked large files and tracked media files.

Use safe read-only commands.

Report:

```text
largest tracked files
tracked image/video/media files
whether they appear to be intentional test fixtures
whether they appear to be accidental user data or generated output
recommended action
```

Do not remove files.

### 8. Test Fixture Audit

Determine whether any media files are intentionally used by tests.

Report:

```text
test fixture directories
tests that reference media files
whether any root-level media folders should be moved under backend/tests/fixtures/
whether 14/ appears to be used as a fixture
```

Do not move fixtures.

### 9. Branch Audit

Report local and remote branches.

Classify branches as:

```text
active
merged/stale
safe deletion candidate
needs user decision
```

Do not delete branches.

### 10. Final Report Format

Produce a Markdown report named in your response only. Do not create the file unless explicitly asked later.

Report sections:

```markdown
# Repository Housekeeping Recon Report

## Executive Summary

## Current Git State

## Root Directory Findings

## Suspicious Items

## README Findings

## Docs Findings

## Runtime / Generated Artifact Findings

## .gitignore Findings

## Large File / Media Findings

## Test Fixture Findings

## Branch Findings

## Recommended Cleanup Plan

## Items Requiring User Decision

## Proposed Follow-Up Milestones or Cleanup Commits
```

For each recommended cleanup item, use this table format:

```markdown
| Item | Current Location | Classification | Evidence | Recommended Action | Risk |
|---|---|---|---|---|---|
```

Risk values:

```text
Low
Medium
High
Unknown
```

## Important Boundaries

This is recon only.

Do not modify anything.

Do not decide unilaterally that prompts/closeouts should be deleted. We may keep final milestone prompts and closeouts as part of project history.

Do not rewrite history.

Do not use destructive commands.

Do not commit or tag.

At the end, include exact next-step recommendations for a safe cleanup branch and staged cleanup commits.



The reconnaissance is not sufficient yet.

Please redo the cleanup audit using **program relevance**, not Git tracking status.

Being tracked by Git does not mean a file should be kept. A manifest referencing files in its own folder does not prove the folder is used by the program.

For every suspicious item, especially root `14/`, classify based on evidence:

```text id="lfxznv"
KEEP:
  required by runtime, tests, fixture setup, current docs, or milestone history

UPDATE:
  stale but important

MOVE:
  useful but in wrong location

DELETE CANDIDATE:
  tracked but not referenced, not used by tests, not current docs, not needed runtime

NEEDS USER DECISION:
  unclear after evidence search
```

For `14/`, answer specifically:

```text id="uh7lrk"
1. Is anything outside 14/ referencing 14/?
2. Is any test referencing 14/ or its files?
3. Is the manifest referenced by code/tests/docs outside 14/?
4. Is 14/ documented as a fixture?
5. Is it needed for current app runtime?
6. If not, classify as DELETE CANDIDATE or ARCHIVE CANDIDATE, not KEEP.
```

Use concrete read-only evidence, for example:

```powershell id="dgi20m"
git ls-files 14
git grep -n "14/" -- . ':!14/*'
git grep -n "face_13_asset\|manifest.json\|Portraits-387" -- . ':!14/*'
git grep -n "tsbuildinfo\|photo_organizer_legacy_folder_structure_all_files" -- .
git check-ignore -v .env.example
git ls-files "*tsbuildinfo" "*.jpg" "*.jpeg" "*.png" "*.mov" "*.heic" "*.json"
```

For each suspicious item, include:

```markdown id="c72dy2"
| Item | Evidence of Use | Evidence Against Use | Classification | Recommended Action | Risk |
|---|---|---|---|---|---|
```

Do not modify, move, delete, stage, commit, or tag anything.





Clean up actions:

We are on branch `housekeeping/repo-cleanup-pass1`.

Please do a narrow `.gitignore` hardening pass only.

Do not delete files.
Do not move files.
Do not remove tracked files yet.
Do not edit README.
Do not touch `14/`.
Do not commit unless I approve after review.

Current goals:

1. Fix `.env.example` handling.

   * `.env` and real `.env.*` files should stay ignored.
   * example/template env files should be allowed:

     * `.env.example`
     * `docker/.env.example`
     * `.env.dev.example`
     * `.env.prod.example`

2. Remove duplicate `.env` entry if present.

3. Add explicit ignore rules for generated/temp files:

   * `*.partial`
   * `*.patch`
   * `*.tmp`
   * `*.bak`
   * `*.db`
   * `*.sqlite`
   * `*.sqlite3`
   * `*.tsbuildinfo`
   * `.pytest_cache/`
   * `.mypy_cache/`

4. Keep existing protections for:

   * `.venv/`
   * `.tools/`
   * `__pycache__/`
   * `node_modules/`
   * `.next/`
   * `out/`
   * `storage/`
   * `backend/storage/`
   * vision model binaries/directory

Suggested structure:

```gitignore
# Python
.venv/
.tools/
__pycache__/
*.pyc
.pytest_cache/
.mypy_cache/

# Node / Next.js
node_modules/
.next/
out/
*.tsbuildinfo

# Env files
.env
.env.*
# Allow committed example/template files
!.env.example
!**/.env.example
!.env.*.example
!**/.env.*.example

# OS
.DS_Store
Thumbs.db

# Logs / temp files
*.log
*.tmp
*.patch
*.bak

# Databases
*.db
*.sqlite
*.sqlite3

# Partial / interrupted downloads
*.partial

# Runtime storage / vault / exports
storage/
backend/storage/

# Vision model binaries
backend/app/services/vision/models/
```

After editing, run and report:

```powershell
git diff -- .gitignore
git check-ignore -v .env.example
git check-ignore -v docker/.env.example
git check-ignore -v .env.local
git check-ignore -v backend/storage/logs/example.json
git check-ignore -v test.partial
git check-ignore -v frontend/tsconfig.tsbuildinfo
git status
```

Expected:

* `.env.example` and `docker/.env.example` should NOT be ignored.
* `.env.local` should be ignored.
* storage paths should be ignored.
* `*.partial` should be ignored.
* `frontend/tsconfig.tsbuildinfo` should be ignored for future files, though if already tracked it still requires a later separate `git rm --cached` cleanup.
