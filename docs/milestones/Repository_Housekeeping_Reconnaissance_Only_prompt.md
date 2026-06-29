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
