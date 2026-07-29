# Milestone 005A - Development Fixture Adapter Live Validation and Fixture Generator Closeout

## 1. Outcome

Milestone 005A completed successfully.

The Development-only Linux fixture adapter was validated on the Ubuntu
mini-server in the approved two-stage sequence:

1. one GPU backend image was built under the permanent Development Compose
   topology;
2. the backend alone was recreated without fixture configuration;
3. Stage 1 proved the adapter remained unavailable and fail-closed;
4. the empty controlled fixture boundary and temporary override were created;
5. the backend alone was recreated with the override, without rebuilding;
6. Stage 2 proved that all unrelated paths and missing gates failed closed and
   that only the exact acknowledged controlled root returned `needs_review`.

After live gate validation, a deterministic four-file synthetic-photo fixture
generator and focused regression coverage were implemented and validated
locally.

The milestone stopped before:

- server fixture generation;
- Source Profile creation;
- Source Endpoint creation;
- readiness or dispatch execution against a Source Profile;
- ingestion;
- Asset, provenance, or Vault mutation;
- TIFF preview processing;
- the controlled persistence restart;
- removal of the temporary fixture override.

Those operations remain reserved for a separately reviewed Milestone 005B.

## 2. Repository State

### Windows repository

- Path:
  `C:\Users\chhen\My Drive\AI Photo Organizer\Photo Organizer_v1`
- Branch: `feature/deployment-linux-runtime`
- Adapter/live-validation prompt commit used by the server:
  `3a46f20b020085692405496756ced5dbff2388cc`
- Final reviewed generator commit:
  `bd45c0653038c20e4f13afd9b0a7789a20f4f9b9`
- Remote branch HEAD:
  `bd45c0653038c20e4f13afd9b0a7789a20f4f9b9`
- Local and remote HEAD matched before this closeout was created.
- Working tree was clean before this closeout was created.

Commit `bd45c06` contains exactly:

- `scripts/fixtures/create_controlled_photo_fixture_set.py`;
- `backend/tests/test_controlled_photo_fixture_generator.py`;
- the Milestone 005 parent-prompt evidence record.

Its committed change count is:

```text
3 files changed, 1207 insertions(+)
```

The Coder did not commit or push. The Product Owner reviewed, committed, and
pushed the changes.

### Server repository

- Path: `/home/chuck/projects/photo-organizer-dev`
- Branch: `feature/deployment-linux-runtime`
- Starting HEAD:
  `e6961e8ae95dd0f30b869e03325205445cbb4618`
- Approved fast-forward target:
  `3a46f20b020085692405496756ced5dbff2388cc`
- Final server HEAD for 005A:
  `3a46f20b020085692405496756ced5dbff2388cc`
- Protected `docker/.env.development`: present and ignored before and after
  the fast-forward.
- Server worktree at reconciliation: clean.

No reset, clean, stash, rebase, tag, forced checkout, non-fast-forward merge,
or server hot-patch occurred.

The server was intentionally not fast-forwarded to generator commit
`bd45c06` during 005A. That fast-forward is the first separately authorized
005B action.

## 3. Pre-Mutation Baseline

Before the image build or backend recreation, all four Development services
were healthy with restart count zero:

| Service | Preserved container ID |
|---|---|
| PostgreSQL | `42bbb232f702da07dd6a302153c0a4aebd910aa148a7d82b7285ed4080112712` |
| Redis | `107e680b822a993871afff260e4e55273e8d30ea405b2474070678f849a08a57` |
| Frontend | `4403b0d146f730581fa725dc62bc330b3fe92241011e8e4ce3f39689756904e9` |

The pre-005A backend container was healthy and used image:

`sha256:1b57ab81f60d4039d5c3366701e523d30ffcb25e4f598c49215bfd02e399ea49`

The following volumes existed and were retained:

- `photo-organizer-dev_postgres_data`;
- `photo-organizer-dev_redis_data`;
- `photo-organizer-dev_application_storage`;
- pre-existing `portainer_data`.

Read-only database counts were:

| Relation | Rows |
|---|---:|
| `assets` | 0 |
| `ingestion_runs` | 0 |
| `ingestion_sources` | 0 |
| `provenance` | 0 |
| `source_endpoints` | 0 |

Storage counts were:

| Location/classification | Files |
|---|---:|
| Vault | 0 |
| Previews | 0 |
| Thumbnails | 0 |
| Review | 0 |
| Ingestion failures | 0 |
| Known M005 artifacts | 0 |

The sanitized effective live ingestion threshold was:

```text
MINIMUM_FILE_SIZE_BYTES=51200
```

Before Stage 1:

- `DEVELOPMENT_FIXTURE_SOURCE_ROOT` was absent;
- the backend had no fixture bind;
- `/home/chuck/photo-organizer-fixtures` did not exist;
- the temporary override did not exist.

## 4. Single GPU Backend Image Build

The GPU backend image was built exactly once with the permanent Development
Compose file and permanent GPU overlay:

```bash
cd /home/chuck/projects/photo-organizer-dev

sudo docker compose \
  --env-file docker/.env.development \
  --file docker/compose.development.yml \
  --file docker/compose.development.gpu.yml \
  build backend
```

Result:

```text
BACKEND_BUILD_EXIT=0
duration=5.536s
image=photo-organizer-dev-backend:latest
image ID=sha256:823e68da6a74883920b934931a18f7d1d96f1a83082c10a9b67a4e97dfa1b2b7
runtime user=photo-organizer
working directory=/app
command=["python","scripts/container_entrypoint.py"]
```

The temporary fixture override did not exist and was not used during this
build.

## 5. First Backend-Only Recreation

Only the backend was force-recreated under the normal permanent topology:

```bash
sudo docker compose \
  --env-file docker/.env.development \
  --file docker/compose.development.yml \
  --file docker/compose.development.gpu.yml \
  up --detach --no-deps --force-recreate \
  --wait --wait-timeout 180 \
  backend
```

Result:

```text
FIRST_BACKEND_RECREATE_EXIT=0
duration=6.938s
container ID=1759f38decf5d7b5e594fbd03bf0a465e34609d303704637d422206d9a52bd84
restart count=0
status=running
health=healthy
publication=127.0.0.1:18001 -> 8001/tcp
```

PostgreSQL, Redis, and frontend were not restarted or recreated. Their exact
container IDs remained unchanged. All volumes remained intact.

The backend had only:

```text
photo-organizer-dev_application_storage -> /app/storage
```

It had no fixture bind and no `DEVELOPMENT_FIXTURE_SOURCE_ROOT` value.

GPU continuity passed:

```text
UID=999
TORCH=2.11.0+cu130
TORCH_CUDA=13.0
CUDA_AVAILABLE=True
DEVICE_COUNT=1
DEVICE_NAME=NVIDIA GeForce RTX 5070 Ti
CUDA_TENSOR_RESULT=357389824.0
GPU_CONTINUITY=PASS
```

The backend health endpoint returned HTTP 200 and Development health JSON.

TensorFlow/DeepFace separately logged that it could not find CUDA drivers.
That retained warning was not used as PyTorch GPU evidence. PyTorch CUDA
execution was directly proven and did not silently fall back to CPU.

## 6. Stage 1 - Configuration-Absent Validation

Stage 1 used only the public endpoints:

```text
GET  /api/admin/source-identity/capabilities
POST /api/admin/source-identity/probe
```

Results:

- Linux `default_provider` was `null`;
- Linux `supported_providers` was empty;
- `linux_development_fixture_probe_v1` was not advertised as a general Linux
  provider or capability;
- explicitly selecting the fixture provider while its configuration was
  absent returned:
  - `probe_status=blocked`;
  - `safe_to_run=false`;
  - blocker `development_fixture_root_not_configured`;
- an arbitrary Linux path without an explicit provider returned:
  - `probe_status=unsupported_provider`;
  - `safe_to_run=false`;
  - blocker `unsupported_os_provider`.

After Stage 1:

- the five selected database counts remained zero;
- all application-storage fixture counts remained zero;
- fixture directories and override remained absent;
- no Source Profile, Source Endpoint, or application state was created.

Stage 1 passed before any fixture-boundary mutation began.

## 7. Controlled Fixture Boundary and Temporary Override

Only after Stage 1 passed, these empty directories were created:

```text
/home/chuck/photo-organizer-fixtures
/home/chuck/photo-organizer-fixtures/m005
/home/chuck/photo-organizer-fixtures/m005/source
```

Validation confirmed:

- owner/group: `chuck:chuck`;
- mode: `0755`;
- filesystem: local `ext4` on `/dev/nvme0n1p2`;
- no path component was a symlink;
- exact resolved source:
  `/home/chuck/photo-organizer-fixtures/m005/source`;
- source entry count: zero;
- no NAS, repository, application-storage, Test, or Production redirection.

The temporary non-secret override was created at:

```text
/home/chuck/photo-organizer-fixtures/m005/compose.fixture.override.yml
```

Metadata:

```text
owner/group=chuck:chuck
mode=0644
SHA-256=6e6d7d26cd18f5ec628b4ebd0cb8fa296a8d02674fa3aa382370c83325742614
```

Its only functional additions were:

```text
DEVELOPMENT_FIXTURE_SOURCE_ROOT=/mnt/photo-organizer-fixtures/m005

/home/chuck/photo-organizer-fixtures/m005/source
  -> /mnt/photo-organizer-fixtures/m005
  read_only=true
```

Combined Compose validation passed and proved:

- `APP_RUNTIME_PROFILE=development`;
- `STORAGE_MODE=local`;
- `REQUIRE_GPU=true`;
- exactly one backend bind;
- backend and frontend remained loopback-only;
- PostgreSQL and Redis remained unpublished;
- no arbitrary resource limit was introduced.

No permanent Compose or tracked environment file changed.

## 8. Second Backend-Only Recreation

Only the backend was recreated a second time, using the same already-built GPU
image plus the temporary override. No second image build occurred.

Result:

```text
SECOND_BACKEND_RECREATE_EXIT=0
duration=6.864s
container ID=6a451fec30281470dffa50990b76c41939ac948585dc4522fceee9b39805c454
image ID=sha256:823e68da6a74883920b934931a18f7d1d96f1a83082c10a9b67a4e97dfa1b2b7
restart count=0
status=running
health=healthy
```

Docker inspection confirmed:

```text
TYPE=bind
SOURCE=/home/chuck/photo-organizer-fixtures/m005/source
DEST=/mnt/photo-organizer-fixtures/m005
RW=false
```

The application-storage volume remained attached normally. Backend UID 999
could read the controlled fixture root but could not write it, and the
container-visible source entry count remained zero.

PostgreSQL, Redis, and frontend retained their exact pre-mutation container
IDs. All volumes remained intact.

PyTorch CUDA validation passed again with the same versions, device, and CUDA
tensor result recorded in Section 5.

## 9. Stage 2 - Exact-Root Gate Validation

The following public-probe cases all failed closed as expected:

| Case | Expected result |
|---|---|
| Arbitrary Linux path without provider | `unsupported_os_provider` |
| Exact root without explicit provider | `unsupported_os_provider` |
| Exact root without acknowledgment | `development_fixture_acknowledgment_required` |
| Parent path | `development_fixture_root_mismatch` |
| Descendant path | `development_fixture_root_mismatch` |
| Sibling path | `development_fixture_root_mismatch` |
| Traversal path | `development_fixture_parent_traversal` |
| NAS path | `development_fixture_root_mismatch` |
| NAS source type | `development_fixture_source_type_blocked` |
| Repository path | `development_fixture_root_mismatch` |
| Application-storage path | `development_fixture_root_mismatch` |
| Test path | `development_fixture_root_mismatch` |
| Production path | `development_fixture_root_mismatch` |
| Windows drive path | `development_fixture_non_posix_path` |
| UNC path | `development_fixture_non_posix_path` |

The exact acknowledged root produced:

```text
provider_name=linux_development_fixture_probe_v1
provider_version=1
probe_status=completed_with_warnings
safe_to_run=needs_review
match_status=not_compared
confidence_tier=weak_manual_confirmation_required
identity_evidence=unverified_path_only
path_evidence=exact_readable_read_only_fixture_root
source boundary=local_folder
durable fingerprint=none
durable identifier=none
durable match=none
warning=development_fixture_identity_unverified
```

This result is deliberately not durable-ready or verified identity. It
authorizes no general Linux provider and creates no Source Endpoint.

After Stage 2:

- `assets`: 0;
- `ingestion_runs`: 0;
- `ingestion_sources`: 0;
- `provenance`: 0;
- `source_endpoints`: 0;
- Vault files: 0;
- previews: 0;
- thumbnails: 0;
- review files: 0;
- ingestion-failure files: 0;
- known M005 artifacts: 0;
- host source entry count: 0;
- container source entry count: 0.

All four services remained healthy.

## 10. Deterministic Fixture Generator

No suitable existing tracked deterministic fixture generator or fixture set
was found. The approved implementation added:

```text
scripts/fixtures/create_controlled_photo_fixture_set.py
backend/tests/test_controlled_photo_fixture_generator.py
```

The generator uses the already pinned `Pillow==12.2.0` dependency and requires:

```text
--fixture-root <absolute-controlled-root>
--minimum-file-size-bytes <positive-sanitized-live-value>
```

Optional deterministic regeneration requires:

```text
--replace-known
```

The generator:

- uses deterministic SHA-256 counter-stream RGB content;
- uses no current time, randomness, hostname, username, personal media, or
  network input;
- creates exactly four approved media files under `source/`;
- creates `fixture_manifest.json`;
- never creates or changes the separately managed temporary override;
- adds no dependency;
- creates no database, Redis, Docker, Vault, NAS, Test, Production, or
  application-storage state;
- writes directories as mode `0755`;
- writes generated media and manifest as mode `0644`;
- refuses relative, broad, traversal, symlinked, repository,
  application-storage, NAS, Test, and Production roots;
- refuses unexpected existing content;
- permits replacement only when the complete known managed set already
  matches byte-for-byte and `--replace-known` is explicit;
- requires every generated media file to exceed the supplied threshold by
  more than 32 KiB.

The separately managed `compose.fixture.override.yml` is allowed to coexist
at the fixture root but is never modified or treated as generator-managed
content.

## 11. Deterministic Fixture Evidence

Two independent local generations at the sanitized live threshold of 51,200
bytes matched byte-for-byte. An explicit safe regeneration also matched.

| File | SHA-256 | Bytes | Dimensions |
|---|---|---:|---:|
| `unique_a.jpg` | `4d52dee4a8c4d53f292d00966e5d63a6c536f011ce64d0fa7c177ce826c163cb` | 1,594,899 | 1024 x 768 |
| `unique_a_duplicate.jpg` | `4d52dee4a8c4d53f292d00966e5d63a6c536f011ce64d0fa7c177ce826c163cb` | 1,594,899 | 1024 x 768 |
| `unique_b.jpg` | `957a34f43fbb17ca7efe9b77b376c1b3737c4f1108fa436f1c5d237fa52d57ae` | 1,401,458 | 960 x 720 |
| `preview_source.tiff` | `46b4b7e8fcc21974e6ed89b37461d0ea9c34bff6e41d531153f7c13e5aa9bac8` | 1,440,356 | 800 x 600 |

Manifest:

```text
filename=fixture_manifest.json
bytes=4318
SHA-256=bce699c85d0bfa608bba03e62813fe9d5a3fbc01e4e0b1ebd840987e42a7cc6b
```

Expected semantics recorded in the manifest:

```text
source files=4
unique hashes=3
expected Assets=3
expected Vault objects=3
expected provenance observations=4
TIFF preview-eligible files=1
general thumbnail required=false
```

`unique_a_duplicate.jpg` is an exact byte-for-byte duplicate of
`unique_a.jpg`. The other JPEG and TIFF have distinct hashes.

These hashes are local validation evidence produced with pinned Pillow. 005B
must independently verify the committed generator's server-container output
before ingestion.

## 12. Local Validation

Focused generator tests:

```powershell
$env:PYTHONPATH='backend'
.\.venv\Scripts\python.exe -m unittest `
  backend.tests.test_controlled_photo_fixture_generator -v
```

Result:

```text
Ran 13 tests in 2.744s
OK (skipped=1)
```

The skipped case attempted a real Windows directory symlink, which the local
account could not create because Windows returned error 1314. The independent
mocked symlink-component rejection test passed.

Focused coverage proved:

- two independent generations are byte-for-byte deterministic;
- manifest content matches actual files;
- hashes, byte sizes, dimensions, and controlled metadata match;
- duplicate and unique-hash relationships are correct;
- only the approved files are generated;
- every media file exceeds threshold plus margin;
- invalid thresholds and unsafe roots fail closed;
- unknown existing content is preserved;
- the temporary override is preserved and unmanaged;
- known-set replacement is explicit and fail-closed;
- tampered managed content is not overwritten;
- symlink paths are rejected;
- generation requires no network or external service.

Python compilation:

```powershell
.\.venv\Scripts\python.exe -m compileall -q `
  backend\app backend\scripts backend\tests scripts\fixtures
```

Result:

```text
PYTHON_COMPILATION=PASS
```

Complete backend regression:

```powershell
$env:PYTHONPATH='backend'
.\.venv\Scripts\python.exe -m unittest discover `
  -s backend\tests -p 'test_*.py'
```

Result:

```text
Ran 578 tests in 55.091s
OK (skipped=1)
```

The generator CLI help path also passed after commit.

Pre-commit repository validation:

```text
git diff --check: PASS
new trailing-whitespace errors: none
```

## 13. Isolation and State Preservation

Throughout 005A:

- no Windows database, Redis, media path, drive path, or UNC path was used;
- no NAS-authoritative path or bind was used;
- no Test or Production configuration, path, credential, container, volume,
  or data was used;
- no Docker socket was mounted;
- no repository directory was mounted as fixture input;
- no credential or SSH directory was mounted;
- no application port beyond the existing loopback publications was exposed;
- PostgreSQL and Redis remained unpublished;
- the application-storage volume remained intact;
- no database reset, manual SQL mutation, or schema change occurred;
- no permanent Compose file changed;
- no dependency changed;
- no CPU, memory, GPU, VRAM, worker, batch, or host limit changed.

The fixture source is local NVMe, not NAS. The temporary fixture bind is exact
and read-only from the backend's view.

Isolation does not mean literal outbound IP-level isolation for the running
Development stack. It means no Windows, NAS-authoritative, Test, or Production
resource was configured, mounted, credentialed, migrated, queried, copied, or
actively used.

## 14. Final Server State

The final 005A server state is intentionally:

| Service | State |
|---|---|
| PostgreSQL | Running, healthy, original container preserved |
| Redis | Running, healthy, original container preserved |
| Backend | Running, healthy, restart count 0, GPU image active |
| Frontend | Running, healthy, original container preserved |

Application publications remain:

```text
backend:  127.0.0.1:18001
frontend: 127.0.0.1:13000
```

PostgreSQL and Redis remain unpublished.

The backend remains temporarily configured with:

```text
DEVELOPMENT_FIXTURE_SOURCE_ROOT=/mnt/photo-organizer-fixtures/m005
```

The retained exact read-only bind is:

```text
/home/chuck/photo-organizer-fixtures/m005/source
  -> /mnt/photo-organizer-fixtures/m005
  RW=false
```

The host source is intentionally empty. The temporary override is retained for
the separately reviewed 005B execution. The generated fixture files and
manifest do not yet exist on the server.

Current status command:

```bash
cd /home/chuck/projects/photo-organizer-dev

sudo docker compose \
  --env-file docker/.env.development \
  --file docker/compose.development.yml \
  --file docker/compose.development.gpu.yml \
  --file /home/chuck/photo-organizer-fixtures/m005/compose.fixture.override.yml \
  ps --all
```

## 15. Untested and Deferred Behavior

Deferred to Milestone 005B:

- server fast-forward from `3a46f20` to `bd45c06`;
- one-off network-disabled server-container generator execution;
- verification of generated server hashes, sizes, dimensions, metadata,
  ownership, and modes;
- creation of the one approved path-only Development Source Profile;
- acknowledgment-aware Source Selection and readiness against that Source;
- exactly one controlled dispatch;
- Source Intake behavior for the four files;
- three expected Assets and Vault objects;
- four expected provenance observations;
- exact-duplicate behavior;
- canonical metadata validation;
- supported TIFF preview processing;
- display-media and read-only UI/API validation;
- post-ingestion PyTorch CUDA validation;
- one bounded four-service restart and persistence validation;
- removal of the temporary override;
- return to the permanent Compose topology;
- confirmation that no fixture bind remains after validation;
- final parent Milestone 005 closeout.

Personal-media ingestion, broad Linux Source identity, arbitrary Linux paths,
iCloud, NAS-backed operation, Test, Production, sustained workload,
backup/restore, and promotion/rollback also remain untested.

## 16. Deviations and Command Corrections

### Separate 005A closeout

The approved 005A prompt originally stated that the sub-prompt would not
receive a separate closeout and that its evidence would be incorporated into
the final parent Milestone 005 closeout.

After 005A changes were reviewed, committed, and pushed, the Product Owner
explicitly requested this separate closeout before proceeding to 005B. This is
a documentation-only deviation. The same 005A evidence remains recorded in
the parent prompt, and this closeout does not authorize any 005B execution.

### Local validation command corrections

- An initial `pytest` invocation found that `pytest` was not installed in the
  local virtual environment. No tests ran. The repository's available
  `unittest` runner was used and passed.
- An initial inline PowerShell/Python manifest verifier was affected by shell
  quoting.
- A replacement PowerShell verifier initially used a .NET path API unavailable
  in the installed runtime.
- The corrected native verifier passed, and the isolated temporary validation
  directory was safely removed.

These were validation-command issues, not generator or application failures.
No server or application state changed.

### Windows symlink privilege

The real-directory-symlink test was skipped because the Windows account lacked
the operating-system privilege to create that symlink. The independent mocked
symlink-component rejection test passed. Live host inspection also proved the
approved server path and every inspected parent component were not symlinks.

## 17. Known Limitations

- The fixture adapter is a Development-only exact-path gate, not general or
  durable Linux Source Identity.
- It provides no durable fingerprint, Source Endpoint, access-node identity,
  or durable match.
- Explicit provider selection and operator acknowledgment remain mandatory.
- The adapter remains unavailable in Test and Production.
- The current source root is intentionally path-only and reports
  `needs_review`.
- The temporary host override is not tracked and must be supplied deliberately.
- TensorFlow/DeepFace GPU execution remains unproven; only PyTorch CUDA is
  validated.
- Background jobs remain in-process and non-durable.
- The generated server hashes are not yet proven and must be checked before
  ingestion.
- No ingestion, persistence, preview, duplicate, metadata, or browser result
  may be inferred from the probe and generator-only evidence.

## 18. Recommended Next Continuation

Use:

`005B_deployment_linux_controlled_fixture_ingestion_and_persistence_validation_prompt.md`

Its required purpose is:

- fast-forward the clean server checkout to `bd45c06`;
- generate and verify the controlled fixture set through the approved one-off
  backend-image execution model;
- create exactly one approved path-only Development Source Profile through the
  supported API/ORM flow;
- execute exactly one acknowledgment-aware controlled Source Intake dispatch;
- validate Assets, Vault, provenance, duplicate handling, metadata, TIFF
  preview behavior, and display media;
- validate persistence through one bounded four-service restart;
- remove the temporary override and fixture bind;
- return the backend to the permanent Development Compose topology;
- create the final parent Milestone 005 closeout.

No 005B action should begin until that prompt is reviewed and approved.

## 19. Git Status

Immediately before this closeout was created:

```text
branch=feature/deployment-linux-runtime
HEAD=bd45c0653038c20e4f13afd9b0a7789a20f4f9b9
remote HEAD=bd45c0653038c20e4f13afd9b0a7789a20f4f9b9
working tree=clean
```

This closeout is the only expected new working-tree file.

Required final review commands:

```powershell
git status --short
git diff --name-only
git diff --stat
git diff --check
git ls-files --others --exclude-standard
```

Because this closeout is untracked, ordinary `git diff --name-only`,
`git diff --stat`, and `git diff --check` omit it by Git design.

The Coder must not commit or push this closeout.
