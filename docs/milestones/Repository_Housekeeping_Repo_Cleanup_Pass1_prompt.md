We are proceeding with light repository cleanup only on branch:

```text
housekeeping/repo-cleanup-pass1
```

Do not work on `main`.

Do not do a broad audit.  
Do not run vulture/deptry/pyclean.  
Do not touch legacy docs or `Coder response*.md` files.  
Do not rewrite history.  
Do not delete storage/runtime data.  
Do not expose or print secret values from real `.env` files.

We will proceed in small actions.

## Current cleanup actions

### Action 1 — Finalize `.gitignore` hardening

If not already committed, stage and commit only:

```text
.gitignore
docs/milestones/Repository_Housekeeping_Reconnaissance_Only_closeout.md
```

Before committing, confirm no real env secret values are staged. Real secrets belong only in ignored files such as:

```text
backend/.env
frontend/.env.local
.env.local
```

Template/example files may be committed only if they contain placeholders, not real keys.

Commit message:

```text
Housekeeping: harden generated-file ignore rules
```

### Action 2 — Remove tracked generated TypeScript build info

Remove `frontend/tsconfig.tsbuildinfo` from Git tracking.

Because `.gitignore` now includes `*.tsbuildinfo`, use the safest form:

```powershell
git rm --cached frontend/tsconfig.tsbuildinfo
```

If the file does not exist or is already untracked, report that.

Append to the housekeeping closeout:

```markdown
## Cleanup Action 2 - Remove Tracked TypeScript Build Artifact
```

Include:

- command run

- whether the file remains locally

- final changed files

- `git status --short`

Do not commit until I review.

### Action 3 — Delete root junk folder `14/`

Before deletion, do one final reference check:

```powershell
git grep -n "14/" -- . ':!14/*'
git grep -n "14\\manifest.json\|face_13__asset\|face_29__asset" -- . ':!14/*'
```

If no external references are found, remove the tracked root folder:

```powershell
git rm -r 14
```

Append to the housekeeping closeout:

```markdown
## Cleanup Action 3 - Remove Root Artifact Folder 14
```

Include:

- reference check results

- deleted file list summary

- confirmation that no app/runtime/test references were found

- `git status --short`

Do not commit until I review.

## Boundaries

For now, do not update README.  
Do not touch `docs/legacy_photo_organizer_docs/`.  
Do not touch `Coder response*.md`.  
Do not delete branches.  
Do not edit source code except via Git removing the generated `tsbuildinfo` file and root `14/`.

After Action 2 and Action 3 are complete, report back with:

- `git status --short`

- `git diff --cached --name-only`

- updated closeout excerpt

- proposed commit message
