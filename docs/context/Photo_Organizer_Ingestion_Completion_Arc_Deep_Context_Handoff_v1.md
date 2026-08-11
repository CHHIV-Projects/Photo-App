# Photo Organizer — Ingestion Completion Arc Deep Context Handoff v1

## Purpose of This Document

You are taking over as the planning/architecture ChatGPT for the next major Photo Organizer arc.

This is NOT a coder implementation prompt.

Your role is to:

1. understand the current project and deployment state;
2. guide a controlled stabilization of the Linux deployment work;
3. help establish a clean, trusted Linux-based `main`;
4. preserve previously working ingestion behavior;
5. retain only the useful portions of the experimental Linux Source Access work;
6. then plan the new Source Provider / Windows Source Helper ingestion-completion arc;
7. return to the project's normal milestone-based SOP, producing lean coder prompts one milestone at a time.

Do not begin by coding.

Do not begin by asking for another broad repository reconnaissance.

Do not assume the existing Milestone 012 Source Access implementation should be completed as originally designed.

The immediate priority is repository stabilization and architectural cleanup.

# 1. Product Owner / Workflow Context

The user is the product owner and is not an expert software developer.

The working model is:

- ChatGPT:

  - architecture;
  - planning;
  - milestone design;
  - coder prompts;
  - interpretation of coder feedback;
  - testing guidance;
  - closeout review.

- Codex / GitHub Copilot in VS Code:

  - repository inspection;
  - implementation;
  - focused tests;
  - milestone closeouts.

The user controls:

- commits;
- pushes;
- merges;
- deployment gates;
- acceptance.

Coders must not commit or push unless explicitly authorized.

Normal project SOP is milestone-driven:

1. establish requirements;
2. reconnaissance only where necessary;
3. produce a bounded roadmap;
4. create lean implementation prompts;
5. coder implements smallest safe change;
6. coder produces closeout;
7. Product Owner / ChatGPT validates;
8. commit;
9. proceed to next milestone.

Avoid repeating broad reconnaissance after the architecture is already understood.

Avoid perfection loops and increasingly elaborate validation harnesses that are not required by the milestone.

If an architectural assumption is invalid, stop, reassess, and re-baseline rather than repeatedly patching around it.

# 2. Current Deployment Environment

Photo Organizer has been moved from a Windows-hosted development/runtime environment to a Linux mini-server.

Current server environment includes:

- Ubuntu Server 24.04.4 LTS;
- hostname `henderson-server1`;
- Docker / Compose;
- NVIDIA GPU runtime;
- Development environment;
- isolated Test environment;
- NAS mounted from Synology;
- VS Code Remote SSH development workflow;
- operator controls;
- application runtime operating from Linux.

Authoritative development repository:

`/home/chuck/projects/photo-organizer-dev`

The Linux deployment work through the pre-M012 point is considered valuable and should not be casually discarded.

# 3. NAS / Storage Environment

Synology NAS:

`//192.168.1.171/PhotoOrganizer`

Linux host mount:

`/mnt/nas/photo-organizer`

NAS subfolders include:

- development;
- test;
- production.

NAS is intended for durable Photo Organizer storage and related application data, not as the authoritative Git worktree.

Linux-hosted application runtime and mounted NAS access are valid parts of the future architecture.

# 4. Why the Current Deployment Arc Was Paused

The deployment arc worked successfully until Source ingestion had to deal with device/source identity that was originally developed around Windows.

Windows-specific source concepts included things such as:

- drive letters;
- Windows paths;
- Windows volume/device identity;
- external/removable device recognition;
- optical media;
- local Windows filesystems.

The Linux server cannot directly inspect or open arbitrary source paths such as:

`C:\Photos`

on a separate Windows client computer.

During Deployment Milestone 012, the project attempted to solve Linux Source Access through increasingly elaborate Linux namespace, mount, and identity-broker mechanisms.

Some of that work is useful for NAS/Linux-mounted Sources.

However, the effort began to blur two fundamentally different Source-access cases:

1. storage the Linux server can directly mount/read;
2. storage physically attached to a Windows client.

This produced unnecessary complexity and validation drift.

The project therefore stopped Milestone 012 implementation before proceeding further.

# 5. Key Architectural Realization

Windows paths belong to Windows.

Linux-mounted paths belong to Linux.

A Windows path such as:

`C:\Family Archive`

should not be translated into an artificial Linux filesystem path merely so the Linux backend can pretend it has direct access.

The future Source architecture will use provider-specific access mechanisms behind a common Photo Organizer ingestion interface.

# 6. Approved Source Provider Architecture

Three provider classes are currently planned.

## 6.1 Mounted Source Provider

Used when the Linux server can legitimately access the filesystem directly.

Examples:

- NAS;
- Linux server-local folders;
- disks physically attached to the Linux server.

This provider may reuse appropriate Milestone 012 Linux Source Access work.

## 6.2 Windows Source Helper Provider

Used when files reside on or are attached to the Windows client.

Examples:

- Windows local storage;
- Windows secondary internal disks;
- Windows external HDD/SSD;
- removable media;
- optical media.

A native Windows component will inspect the Windows Source locally and provide requested source files to the Linux Photo Organizer server over authenticated HTTPS or an equivalent HTTPS-compatible session.

The Linux backend does not directly open:

`C:\...`

The Windows computer reads its own filesystem.

## 6.3 Cloud Provider

Cloud acquisition remains provider-specific.

Initial provider:

- iCloud.

Possible future cloud providers are outside the current arc unless specifically added later.

# 7. Common Ingestion Boundary

The Source Provider determines how trustworthy candidate files are obtained.

The provider must not become a second ingestion engine.

Conceptually:

Mounted Source Provider -----------+
                                  |
Windows Source Helper Provider ----+--> Common verified intake boundary
                                  |              |
Cloud Provider --------------------+              v
                                         Existing ingestion
                                                |
                                                v
                                         Vault / database
                                                |
                                                v
                                           Provenance

The provider layer may handle:

- Source identity;
- Source readiness;
- inventory;
- provider-specific acquisition;
- selective hashing;
- transfer;
- transfer verification.

Existing common ingestion remains responsible for:

- authoritative content handling;
- duplicate handling;
- canonicalization;
- Vault placement/reuse;
- Asset creation;
- database persistence;
- provenance;
- skipped/deferred history;
- run reporting;
- cleanup.

Do not create parallel Vault or ingestion implementations for each provider.

# 8. Locked User Experience Requirements

Photo Organizer remains browser-first.

The existing ingestion UX direction is retained:

1. Create Source
2. Source Selector
3. Ingestion Workbench

Provider mechanics remain hidden behind this workflow.

## 8.1 Create Source

Source types remain user-oriented concepts such as:

- Local;
- External;
- NAS;
- iCloud;
- Removable;
- Optical.

The user does NOT select:

- Mounted Provider;
- Helper Provider;
- HTTPS Provider;
- broker;
- mount namespace.

Those are internal implementation concepts.

## 8.2 Windows Source Path Entry

For Windows Sources, the user may directly enter a normal Windows path.

Example:

`C:\Photos`

Typical Product Owner workflow is:

1. locate folder in Windows File Explorer;
2. copy its path;
3. paste the path into Photo Organizer.

Do not require a folder picker unless later determined useful as an optional convenience.

## 8.3 Source Selector

Source Selector should use understandable Source aliases/names.

A Source should not disappear merely because it is temporarily unavailable.

Example:

`Old Photos — External — Drive not connected`

is preferable to hiding the Source completely.

## 8.4 Starting Ingestion

The existing explicit Start/Run Ingestion action remains.

There should NOT be a required second approval step such as:

Scan Source
-> Review Candidate List
-> Start Ingestion

Instead:

Select Source
-> Start/Run Ingestion
-> Photo Organizer performs the complete run

That run may internally perform:

- readiness;
- inventory;
- comparison;
- selective hashing;
- candidate determination;
- acquisition/transfer;
- intake;
- Vault/database work;
- reporting.

Candidate counts and progress may be displayed during the run, but ordinary new candidates do not require another button press.

# 9. Windows Source Helper UX Requirements

The Windows Source Helper is implementation infrastructure, not a separate normal-user workflow.

The user should not normally have to:

- launch the Helper manually;
- click Open Tunnel;
- click Close Tunnel;
- configure SMB;
- enter Linux paths;
- use command shells;
- understand transport sessions.

The preferred behavior is automatic, provider-aware activation.

Example:

User chooses Windows Local / External / Removable / Optical Source
-> Photo Organizer automatically invokes Helper capability
-> Helper verifies Source
-> requested work occurs
-> Helper exits automatically after it is no longer needed

NAS and iCloud operations should not require the Windows Helper.

# 10. Windows Helper Process Requirements

The Helper:

- is a native Windows component;
- is not intended as an always-running startup program;
- should start automatically when Photo Organizer needs Windows-local Source access;
- should close automatically when no relevant operation remains;
- should not expose command prompts, PowerShell, Python consoles, or terminal windows during normal use.

It may be:

- integrated with an existing Photo Organizer client utility;
- a separate executable;
- or built from shared native client components.

That implementation choice has NOT yet been locked.

The product requirement is that it appears integrated into Photo Organizer.

# 11. Existing Client-Side Utility

Photo Organizer already has a client-facing/operator utility that can perform functions such as:

- opening tools;
- checking program status;
- starting/stopping applicable program components.

Before deciding the Windows Helper packaging architecture, inspect this existing client functionality.

Do not assume the Helper must be merged into it.

Do not assume it must be separate.

Choose the smallest clean architecture after understanding the existing implementation.

# 12. Windows Source Identity Requirements

Source identity must not depend solely on drive letter or path.

The model must distinguish:

- Windows Endpoint/computer identity;
- storage device/volume identity;
- Source Profile identity;
- approved Source root;
- currently observed path.

One Endpoint may have multiple Source Profiles.

Example:

Endpoint:
`Chuck's PC`

Sources:

`Chuck's Pictures`
`C:\Users\Chuck\Pictures`

`Family Archive`
`C:\Family Archive`

`Scanned Photos`
`D:\Scanned Photos`

`Old Photos`
`E:\Old Photos`

Several Sources may belong to the same Endpoint.

A changed external-drive letter must not break identity if the durable device/volume identity still matches.

Example:

Originally:

`E:\Old Photos`

Later:

`F:\Old Photos`

If the expected durable identity matches, this is still the same Source.

If another disk appears under the expected drive letter but has the wrong durable identity, ingestion must not silently continue.

# 13. Overlapping Source Roots

Multiple non-overlapping roots on one Endpoint/device are valid.

Example:

`C:\Pictures`

and

`C:\Family Archive`

An overlapping parent/child configuration such as:

`C:\Photos`

and

`C:\Photos\Family`

must not be silently accepted without explicit handling because it can cause:

- duplicate discovery;
- ambiguous Source ownership;
- confusing provenance.

Exact overlap UX may be finalized later.

# 14. Windows Helper Local Responsibilities

The Helper is expected to perform only Windows-local work such as:

- identify host;
- identify volumes/devices;
- validate approved roots;
- enumerate filesystem metadata;
- calculate requested hashes;
- read requested files;
- transfer requested files;
- maintain bounded local operational/cache state.

It must not become responsible for:

- Vault management;
- global duplicate decisions;
- Asset creation;
- authoritative provenance;
- authoritative ingestion history.

# 15. Local Helper Cache

A small local embedded database/cache is expected to be useful.

SQLite is a likely implementation but not yet a hard coding mandate.

Local cache may contain:

- paired-server information;
- Endpoint information;
- approved Source roots;
- volume identity;
- inventory metadata;
- file identifiers;
- cached hashes;
- recent transfer state.

This cache is disposable operational state.

Deleting it may require rescanning/rehashing, but must not destroy authoritative Photo Organizer data.

# 16. Preferred Windows Scan / Comparison Flow

Avoid hashing the entire Source unnecessarily on every run.

Preferred sequence:

1. Helper inventories inexpensive local metadata.
2. Helper supplies valid cached hashes where available.
3. Server compares inventory against authoritative Photo Organizer state.
4. Server identifies which files require stronger comparison.
5. Helper calculates requested hashes locally.
6. Server determines acquisition candidates.
7. Helper transfers only requested candidates.
8. Server verifies received content.
9. Existing ingestion takes over.

This occurs automatically after the user's normal Run/Start Ingestion action.

# 17. Transfer Scope

Current arc scope is home-network Windows client to Linux server.

Remote Windows clients over the Internet are explicitly OUT OF SCOPE.

Do not add:

- remote multi-user architecture;
- public server exposure;
- account-based remote Source access;
- WAN transport architecture;
- remote client authorization systems.

Those belong to a future multi-user/remote-access arc.

For the current arc, authenticated HTTPS-style communication is still the preferred client/server transport, but only within the current supported environment.

# 18. Provenance Requirement

Temporary transport infrastructure must never replace original Source provenance.

Example original Windows file:

`C:\Family Archive\1985\Vacation\IMG001.jpg`

Provenance should preserve concepts such as:

- Source Profile;
- Windows Endpoint;
- volume/device identity;
- original Source root;
- relative Source path;
- original filename;
- ingestion run;
- provider/transfer method where useful;
- final content identity;
- Vault Asset.

A temporary Linux receiving path must NOT become the original Source identity.

# 19. Existing Ingestion Must Be Protected

A major concern during stabilization is avoiding spaghetti code and preserving previously working ingestion.

The new Source Provider architecture must not unnecessarily rewrite:

- Vault behavior;
- duplicate handling;
- canonicalization;
- near-duplicate behavior;
- Asset identity;
- provenance semantics;
- iCloud behavior;
- skipped/deferred history;
- successful run reporting.

Default stabilization rule:

If Milestone 012 changed existing ingestion code and the change is not clearly required by the accepted provider architecture, prefer restoring the trusted pre-M012 behavior.

# 20. Current Source Selector Concern

In the current Development UI, Create Source still displays several Source types, but Source Selector was observed showing only:

- Local;
- Legacy source (1).

Do not assume this means the old Windows Source architecture is gone.

Possible causes include:

- current Development database contains only the controlled fixture;
- Windows Source Profiles are absent in this environment;
- backend filtering;
- frontend filtering;
- readiness/provider filtering;
- actual regression.

During stabilization, determine the cause with a narrowly scoped inspection.

Do not turn this into another repository-wide reconnaissance.

# 21. Frozen Git State

Current historical deployment branch:

`feature/deployment-linux-runtime`

Frozen tip:

`453032b3eddaa677094ef0eaadfa3711ff536989`

This branch is synchronized with its remote and should remain frozen.

Do not continue implementation directly on it.

Do not rewrite or sanitize this branch.

It is the historical record containing:

- successful deployment work;
- useful Source work;
- experimental M012 work;
- abandoned approaches;
- diagnostic evidence.

# 22. Candidate Pre-M012 Linux Baseline

Current candidate trusted pre-M012 Linux baseline:

`461653e`

Commit description:

`Close Linux source provider reconnaissance`

Immediately after this point the history includes:

`469980e  Add Linux source access foundation prompt`

`81a9bc5  Implement Linux source access foundation`

followed by the namespace/broker/mount-propagation implementation and fixes.

The candidate stabilization audit range is therefore:

`461653e..453032b`

Before creating the integration branch, confirm `461653e` against milestone documentation/history as the correct trusted boundary.

Do not merely assume based on commit naming.

# 23. Deployment Work Before M012

The Linux deployment work before the M012 implementation boundary is presumed valuable unless evidence says otherwise.

This includes work such as:

- Linux runtime foundation;
- Development environment;
- controlled fixture validation;
- Remote VS Code workflow;
- Development operator controls;
- restart/recovery;
- isolated Test environment;
- runtime-neutral frontend work;
- deployment architecture documentation.

Do not rebuild this work from old `main` unless there is a demonstrated reason.

The clean integration branch should begin from the trusted Linux deployment baseline, NOT from the old pre-deployment `main`.

# 24. M012 Historical Work

Milestone 012 introduced or modified concepts including:

- Linux Source namespace;
- NAS source slot;
- Access Node identity;
- identity broker;
- protected broker socket;
- Linux Source readiness;
- container Source exposure;
- runtime-path evidence;
- mount propagation;
- rollback/diagnostic logic;
- Source dispatch tests.

Important historical commits include:

`81a9bc5  Implement Linux source access foundation`

`5fc5b91  Fix Linux source namespace mount parsing`

`5e5d80d  Fix Source namespace host mount persistence`

`a816498  Make Source namespace host mount explicit`

`ef7e3f5  Add bounded NAS slot diagnostic and rollback`

`10c37d3  Fix Linux Source namespace mount propagation order`

`453032b  Fix Linux source dispatch test run ID`

Some of this may remain useful for the Mounted Source Provider.

Some may be unnecessary under the newly accepted provider architecture.

Do not prejudge the classification.

# 25. Known M012 Validation History

The M012 namespace and broker ultimately passed controlled live host validation.

The namespace topology issue was identified and corrected.

A key mount-propagation fix changed the setup sequence to:

self-bind
-> make-rprivate
-> create nested NAS bind
-> validate one row
-> make-rshared
-> validate one row

The corrected topology produced one expected NAS mount rather than the previous duplicate.

Broker validation also passed after recognizing that an unprivileged `test -S` result was misleading due to parent-directory permissions.

Therefore:

Do not assume all broker/namespace work is broken.

The issue is architectural fit and complexity, not simply correctness.

# 26. M012 Validation Drift

Later full-backend test validation became problematic.

A custom validation container imposed filesystem restrictions that conflicted with unrelated tests.

The test run produced failures caused partly by the artificial harness rather than by M012 production behavior.

A focused backend Source-access suite passed after correcting one test-only fixture:

`run_id="run-1"` became `run_id=1`

The broader validation effort then became trial-and-error.

The Product Owner explicitly stopped this process.

Do not resume the same full-suite custom-container validation strategy unless there is a new, specific justification.

Use the repository's intended test environment and focused acceptance tests.

# 27. Stabilization Strategy

The objective is NOT:

"finish M012."

The objective is:

"produce a clean Linux-hosted Photo Organizer baseline containing only accepted deployment and mounted-source work."

Process:

1. confirm trusted pre-M012 Linux baseline;
2. keep historical deployment branch frozen;
3. create a new clean integration branch from the trusted Linux baseline;
4. audit only the bounded M012 delta;
5. classify each relevant change;
6. reconstruct only the accepted work;
7. validate the resulting clean branch;
8. align the actual server installation;
9. merge the clean branch into `main`;
10. preserve the historical deployment branch separately.

# 28. M012 Classification System

Every relevant M012 change should be classified as:

## KEEP

The code is clean, useful, compatible with the accepted provider architecture, and should survive substantially as written.

## REVISE

The concept is useful but the implementation needs to be simplified, narrowed, or made provider-aware.

## RESTORE

The M012 modification should be removed and the trusted pre-M012 implementation restored.

This is especially appropriate where generic ingestion behavior was changed unnecessarily.

## DISCARD

Experimental or obsolete implementation should not be carried into the clean baseline.

The historical deployment branch remains available if later reference is needed.

# 29. Likely Areas to Review Carefully

Do not treat this list as a predetermined decision.

Review carefully:

- Linux Source namespace;
- Source identity broker;
- broker socket/permissions;
- mount-propagation machinery;
- mounted NAS slot;
- Access Node identity;
- Source runtime-root handling;
- Endpoint/Source Profile integration;
- readiness behavior;
- provenance changes;
- generic filesystem Source assumptions;
- Source Selector changes;
- existing ingestion orchestration changes;
- M012-specific validation scaffolding.

Ask for each:

"Is this required for the Mounted Source Provider or provider-neutral Source architecture?"

If not, do not preserve it merely because it exists.

# 30. Historical Branch vs Trusted Main

Desired end state:

## Historical branch

`feature/deployment-linux-runtime`

Contains:

- original deployment history;
- successful implementation;
- experimental M012 work;
- abandoned approaches;
- debugging history;
- evidence.

This branch remains frozen/reference-only.

## Trusted main

After stabilization:

`main`

Contains:

- all accepted Linux deployment work;
- clean Development environment;
- clean Test environment;
- accepted NAS/Linux mounted-source support;
- accepted provider-neutral Source architecture;
- preserved existing ingestion;
- only the M012 components deliberately approved.

`main` becomes the authoritative baseline going forward.

# 31. Clean Integration Branch

Create the clean branch only after the baseline is confirmed.

Conceptual name:

`integration/linux-runtime-clean`

Base it on the trusted Linux deployment commit, not today's old `main`.

Then selectively reconstruct the accepted M012 outcome.

Prefer clean cherry-picks only where commits are internally clean.

Where commits mix useful and unwanted behavior, implement/reapply the smallest accepted change rather than importing the whole experimental commit.

# 32. Stabilization Validation Gates

Before merging the clean integration branch into `main`, establish confidence in the following areas.

## 32.1 Git / Repository

- expected branch/base;
- clean Git status;
- expected migrations;
- no abandoned validation artifacts;
- no unexplained deployment delta.

## 32.2 Linux Runtime

- Development starts normally;
- Development health checks pass;
- Test environment remains isolated and healthy;
- existing operator controls remain functional;
- no unrelated server workloads are disturbed.

## 32.3 Existing Ingestion

Use focused regression validation for:

- ingestion run creation;
- Vault behavior;
- duplicate handling;
- Source Profile behavior;
- provenance;
- skipped/deferred handling where applicable.

Do not invent a new broad validation harness merely for perceived completeness.

## 32.4 iCloud

Perform sufficient focused validation to demonstrate that stabilization did not break the existing independent iCloud provider.

Do not alter iCloud behavior to solve mounted-source problems.

## 32.5 Original Windows Source Architecture

Determine which existing Windows source/device components still exist and remain reusable.

Specifically understand:

- host/device probing;
- volume identity;
- Local Source logic;
- External Source logic;
- Removable Source logic;
- Optical Source logic;
- Source Endpoint relationships;
- readiness concepts.

The goal is not to make Linux directly ingest Windows paths.

The goal is to preserve useful Windows identity/source intelligence for the later Helper provider.

## 32.6 Source Selector

Determine why the current UI shows only the Local legacy fixture.

Classify the cause as:

- fixture/database state;
- intended filtering;
- backend regression;
- frontend regression;
- other specific cause.

Fix only what is actually broken.

## 32.7 Mounted Source Provider

Before merge, demonstrate at least one real NAS Source end-to-end:

Create/select Source
-> Endpoint/Source identity
-> readiness
-> Source Selector
-> run ingestion
-> Vault result
-> correct provenance

Also use a controlled Linux-local fixture where useful.

This is the key proof for any M012 mounted-provider work that survives.

# 33. Server Host-State Alignment

Repository cleanup and Linux-host cleanup are separate tasks.

Current host artifacts may include:

- `photo-organizer-source-namespace.service`;
- `photo-organizer-source-identity-broker.service`;
- `/etc/photo-organizer/...`;
- `/mnt/photo-organizer-sources`;
- broker state/configuration;
- temporary validation Docker images/logs.

After the accepted repository architecture is known, classify host artifacts:

- KEEP;
- REVISE;
- DISABLE;
- REMOVE;
- ARCHIVE.

Do not uninstall working host infrastructure before deciding whether the Mounted Source Provider still needs it.

Do not leave orphaned services/configuration after stabilization.

# 34. Merge Strategy

When stabilization gates pass:

`integration/linux-runtime-clean`
-> `main`

At that point `main` becomes the clean Linux-hosted Photo Organizer baseline.

Preserve the old deployment branch temporarily as historical reference.

Do not start the Windows Helper arc before this merge is complete.

# 35. New Ingestion Completion / Windows Helper Arc

After clean `main` exists:

Create a new feature branch from `main`.

Conceptual name:

`feature/windows-https-source-helper`

Exact naming/numbering should follow the current project workflow and should be agreed before implementation.

# 36. Instructions to the Future Windows Helper Coder

The future Helper coder should NOT be told:

"Review old M012 and decide what you want to resurrect."

That decision belongs to stabilization.

Instead tell the future coder:

"The current `main` is the accepted post-deployment baseline. Build against it. Do not resurrect superseded M012 mechanisms unless a milestone explicitly identifies a retained component or an architectural blocker requires escalation."

The historical deployment branch is reference material, not architecture authority.

# 37. Initial New-Arc Direction

The exact milestone roadmap should be designed by the new planning chat after stabilization.

Likely topics include:

- provider-neutral acquisition seam;
- review of reusable Windows device logic;
- native Helper application/component shell;
- automatic browser-to-Helper invocation;
- pairing/trust;
- Windows Endpoint identity;
- volume/device identity;
- approved Source roots;
- multiple Source Profiles per Endpoint;
- local inventory/cache;
- selective hashing;
- authenticated HTTPS transfer;
- verified server staging;
- connection to existing ingestion;
- automatic lifecycle;
- interruption/retry;
- controlled end-to-end validation.

Do not lock milestone numbering or overdesign all implementation details before the repository baseline is stabilized.

# 38. Scope Exclusions for This Arc

Do not expand this arc into:

- remote Internet Windows clients;
- multiple user accounts;
- public server exposure;
- macOS Helper;
- scheduled unattended ingestion;
- generalized enterprise security;
- additional cloud providers;
- unrelated UI redesign;
- broad Vault redesign.

Those can be future work.

# 39. Important Product Principle

Creating, selecting, and ingesting a Source must continue to look like creating, selecting, and ingesting a Source.

Provider mechanics must remain behind that interface.

The desired normal user flow is:

Create/select Source
-> Source ready
-> Run/Start Ingestion
-> progress
-> completion report

Not:

Create Source
-> start helper
-> open tunnel
-> scan
-> approve candidate list
-> transfer
-> close tunnel
-> close helper

# 40. Immediate Task for the New Planning Chat

Do NOT issue a coder prompt immediately.

First:

1. read this handoff;
2. review the project's current architecture/context/workflow documents supplied by the Product Owner;
3. confirm the frozen Git boundary and stabilization objective;
4. identify any genuine contradiction between this handoff and current project documentation;
5. discuss those contradictions with the Product Owner rather than silently resolving them;
6. then produce the stabilization roadmap.

The first coder-facing work should be narrowly focused on establishing the exact trusted baseline and bounded M012 delta, not broad repository reconnaissance.

# 41. Stabilization Success Definition

Stabilization is complete when:

- the trusted Linux deployment baseline is known;
- accepted M012 functionality has been deliberately reconstructed;
- experimental/unwanted M012 functionality is absent from the clean baseline;
- Linux Development works;
- Test remains healthy;
- mounted NAS ingestion works;
- existing ingestion behavior is protected;
- iCloud remains functional;
- Source Selector behavior is understood;
- useful original Windows Source/device architecture is preserved;
- installed server state matches the accepted repository;
- the clean integration branch has been merged into `main`;
- the historical deployment branch remains available for reference.

At that point the deployment arc can close.

# 42. New Arc Success Direction

The new ingestion-completion arc should ultimately produce a Photo Organizer where:

- Linux remains the server/backend runtime;
- NAS/Linux Sources use mounted access;
- Windows-local Sources use a native Helper;
- users continue entering ordinary Windows paths such as `C:\Photos`;
- Helper mechanics are invisible during normal operation;
- the existing Run/Start Ingestion action remains the single explicit ingestion-start action;
- device identity remains durable;
- multiple Sources can belong to one Windows Endpoint;
- original files remain read-only;
- only required candidates cross the network;
- existing Vault/duplicate/provenance behavior remains authoritative;
- no remote/multi-user architecture is required for this arc.

# 43. Governing Principle for the Next Chat

Do not optimize for preserving work already written.

Do not optimize for deleting work merely because it became complicated.

Optimize for the smallest clean architecture that:

1. preserves proven Linux deployment work;
2. preserves previously working ingestion;
3. cleanly supports NAS/Linux-mounted Sources;
4. creates a clear seam for the Windows Helper;
5. leaves `main` understandable and trustworthy for the next arc.

When evidence conflicts with an assumption, stop and report it rather than extending the architecture around the assumption.

# 44. Post-Stabilization Reconciliation — Milestone 12.65

The stabilization strategy described above has now been carried through on the
clean `integration/linux-runtime-clean` branch. The frozen
`feature/deployment-linux-runtime` branch remains historical evidence and was
not used as continuing implementation authority.

Accepted current state:

- the clean reconstruction retained the useful Linux deployment foundation and
  selectively reconstructed the accepted Mounted Source Provider;
- Linux Mounted access is the direct-filesystem provider for approved
  server-accessible Local and NAS locations;
- the protected namespace and non-root identity broker provide the bounded NAS
  mapping without giving the application mount authority;
- modern NAS Endpoint `1` and Profile `2` were created through the normal
  durable Endpoint/Profile workflow;
- NAS readiness and Source Selection were validated live while preserving the
  host Observed/Persisted root and distinct backend Runtime Root;
- a real bounded NAS intake produced Source Intake Run `3`, Ingestion Run `3`,
  16 Assets, 16 canonical Vault objects, and 16 Profile-2 provenance rows;
- the one authorized repeat, Source Intake Run `4` / Ingestion Run `4`, scanned
  the same 16 files, classified all 16 as known, and created no new Asset,
  Vault, or same-Source provenance state;
- Source bytes remained unchanged and the Profile identity, Runtime Root,
  provenance, and Vault contracts survived the live proof;
- Mounted Local implementation exists, but live Profile creation, readiness,
  and selection proof remains deferred;
- Windows Local, External, Removable, and Optical Sources remain Windows-side
  provider concepts for the future Windows Helper arc; they are not translated
  into artificial Linux paths;
- iCloud remains an independent provider using the common Source Intake
  boundary after provider-specific acquisition.

The final stabilization regression and documentation acceptance is Milestone
12.65.6. Merge of the clean integration branch into `main` remains a separate
controlled milestone. After stabilization and merge, the next architecture and
implementation arc is 12.66 for the Windows Source Helper. The principles and
future-arc requirements in this handoff remain authoritative unless a later
approved architecture milestone changes them.
