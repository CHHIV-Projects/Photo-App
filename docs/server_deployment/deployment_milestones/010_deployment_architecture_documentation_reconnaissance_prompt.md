Prompt file name:

010_deployment_architecture_documentation_reconnaissance_prompt.md

Task:

Perform a narrow, read-only repository reconnaissance to support an update of:

PROJECT_ARCHITECTURE_v6.md

This is documentation reconnaissance only.

Do not modify any file.
Do not create a closeout yet.
Do not run Docker commands.
Do not start, stop, restart, rebuild, deploy, or inspect live containers.
Do not connect to or modify the NAS.
Do not read or print protected environment files, credentials, secrets, or release-manifest contents.
Do not commit or push.

Authoritative repository:

/home/chuck/projects/photo-organizer-dev

Primary document being updated:

PROJECT_ARCHITECTURE_v6.md

The Product Owner is updating the architecture document to reflect the completed transition from a Windows-hosted Development environment to the current Windows-client/Linux-server/NAS architecture.

Scope is limited to the following questions.

1. Linux Source identity and selection support

Inspect the relevant tracked backend code and tests and report, by Source Type:

- Local
- External
- Removable Media
- NAS
- Optical
- iCloud

For each Source Type, state:

- whether Source creation currently operates on Linux;
- whether Source selection currently operates on Linux;
- whether readiness currently operates on Linux;
- whether selected-source Run Ingestion currently operates on Linux;
- whether durable identity evidence is implemented for Linux;
- whether the implementation remains Windows-specific;
- whether the path currently falls back to weaker path-only behavior;
- whether it explicitly blocks or reports unsupported behavior on Linux.

Name the exact provider, service, route, model, and test files that support each conclusion.

Do not infer functionality solely from abstract interfaces or intended architecture.
Distinguish:

- implemented and tested;
- implemented but not clearly tested;
- partial;
- Windows-only;
- unsupported;
- unclear from repository evidence.

Pay particular attention to:

- volume/device identity;

- drive-letter assumptions;

- Linux mount paths;

- UNC versus mounted NAS paths;

- Optical probing and fingerprinting;

- host operating-system branching;

- runtime-root resolution;

- endpoint-relative-root containment.
2. Current Development source and image model

Inspect the tracked Development Compose definitions, Dockerfiles, runtime scripts, and operator scripts.

Report exactly how the current Development backend and frontend run:

- whether application source is bind-mounted at runtime;
- which source directories are bind-mounted, if any;
- whether backend dependencies are built into the image;
- whether frontend dependencies and build output are built into the image;
- whether Development containers are rebuilt from the current workspace;
- whether Development runs immutable commit-specific images;
- whether code changes require rebuild, restart, or hot reload;
- whether PostgreSQL, Redis, and application storage use named volumes;
- whether any Development application storage is NAS-backed;
- whether any Development database or Redis data is NAS-backed.

Report the exact tracked files and relevant sections supporting each answer.

Clearly contrast Development with the validated Test model:

Development:

- mutable workspace-oriented environment;
- exact implementation to be confirmed by this reconnaissance.

Test:

- no runtime source bind mounts;
- immutable full-SHA backend and frontend images;
- separately recorded image IDs;
- separate PostgreSQL, Redis, application storage, networks, configuration, and release state.

Do not inspect live Docker state. Use tracked repository evidence only.

3. Current tracked deployment identity

Using tracked files only, confirm the intended current architecture values for:

Development:

- Compose project name;
- frontend loopback port;
- backend loopback port;
- PostgreSQL host publication state;
- Redis host publication state;
- named volumes;
- networks;
- runtime profile;
- storage mode;
- protected configuration path, if specified in tracked documentation or scripts.

Test:

- Compose project name;
- frontend loopback port;
- backend loopback port;
- PostgreSQL host publication state;
- Redis host publication state;
- named volumes;
- networks;
- runtime profile;
- storage mode;
- protected configuration path;
- release-manifest path;
- whether routine start rebuilds or replaces the deployed candidate.

Production:

- whether any tracked Production Compose project, operator, configuration, volumes, networks, or deployment resources currently exist;
- whether Production remains documentation/design only.

Do not treat example files as proof that a live protected configuration exists.
Distinguish tracked contract from live runtime evidence.

4. Repository and operator authority

Inspect tracked scripts and documentation and confirm:

- the intended authoritative editable repository location on the Linux server;
- the role of VS Code Remote SSH;
- whether any tracked workflow still identifies the Windows clone as the primary editable repository;
- the intended role of Windows operator controls;
- which Development operations have Windows-facing controls;
- whether Test has a Windows-facing operator control window;
- how Test is currently intended to be operated;
- whether Dev-to-Test candidate replacement is implemented;
- whether rollback is implemented;
- whether Production promotion is implemented.

Identify any tracked documentation that conflicts with the current server-authoritative model.

5. NAS and storage authority

Using tracked documentation, Compose files, and scripts only, confirm:

- the expected Linux NAS mount path;
- the expected NAS source/share identity;
- the expected protocol, if documented;
- the intended current role of the NAS;
- whether Development live application storage is currently NAS-backed;
- whether Test live application storage is currently NAS-backed;
- whether PostgreSQL live data is stored on the NAS;
- whether Redis live data is stored on the NAS;
- whether the NAS is currently a mounted durable-storage and backup layer rather than the live Development/Test storage authority.

Do not connect to or inspect the NAS.

6. Documentation conflicts

Review PROJECT_ARCHITECTURE_v6.md only for deployment-related accuracy.

List statements that are now:

- incorrect;
- outdated;
- still accurate;
- future-looking but still unresolved;
- too operational for an architecture document;
- duplicated more appropriately in docs/server_deployment/.

Focus on these sections:

- Document Status
- Current State Summary
- Architecture North Star
- Runtime and Deployment Layer
- Deployment Architecture
- Backup, Recovery, and Release Architecture
- Current Architectural Risk Register
- Development Phases
- Milestone Reality
- Parking Lot Integration Strategy
- Constraints for Future Work
- Near-Term Architecture Direction

Do not rewrite the document.

7. Provenance boundary

Do not analyze, verify, reinterpret, or propose edits to the provenance architecture or the Milestone 12.64 results.

For this reconnaissance, state only:

“Provenance sections are intentionally left unchanged. Their post-12.64 update will be completed separately using the authoritative 12.64 milestone record.”

Do not treat older provenance wording as a defect in this task.

Required output

Provide one concise reconnaissance report with these sections:

1. Executive Summary
2. Linux Source Support Matrix
3. Development Runtime Model
4. Development/Test/Production Contract Matrix
5. Repository and Operator Authority
6. NAS and Storage Authority
7. PROJECT_ARCHITECTURE_v6 Deployment Conflicts
8. Facts Safe to Use in the Rewrite
9. Unresolved Questions
10. Files Inspected
11. Provenance Boundary

For every material conclusion:

- cite the exact repository file;
- include class, function, service, or section names where useful;
- distinguish verified fact from inference;
- state when repository evidence is insufficient.

Stop and report rather than guessing if:

- tracked files conflict;
- a conclusion would require live Docker inspection;
- a conclusion would require protected configuration;
- a conclusion would require NAS access;
- a conclusion depends on the separate Milestone 12.64 provenance record.

Do not make implementation recommendations beyond identifying documentation corrections.
Do not modify any file.
Do not commit or push.
