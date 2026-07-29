# Milestone 005B - Linux Controlled Fixture Ingestion and Persistence Validation Closeout

## 1. Outcome

Milestone 005B completed successfully after one preserved intake failure, one
approved narrow correction, and one approved recovery intake.

The Ubuntu Development stack:

- generated and independently verified four deterministic, non-personal media
  fixtures;
- created exactly one Development-only path-based Source Profile;
- kept Source Endpoint count at zero;
- proved selection and readiness fail closed without explicit acknowledgment;
- selected the exact configured fixture root only with acknowledgment;
- completed one recovery Source Intake through the supported dispatch route;
- produced three Assets and three immutable Vault objects from three unique
  content hashes;
- preserved four provenance observations, including both paths for the exact
  duplicate;
- extracted and canonicalized the expected metadata;
- generated one supported TIFF display preview;
- served all three Assets and the preview through the supported API;
- rendered all three Assets in the Workbench;
- preserved all evidence through exactly one four-service restart;
- returned the backend to the permanent Development Compose topology;
- removed the temporary non-secret fixture override and read-only bind;
- retained the fixture media, manifest, database, Vault, reports, and preview.

The final stack is healthy. General durable Linux Source identity remains
unsupported and was not implied by this validation.

## 2. Repository State

### Windows repository

- Path:
  `C:\Users\chhen\My Drive\AI Photo Organizer\Photo Organizer_v1`
- Branch: `feature/deployment-linux-runtime`
- 005B execution-contract commit:
  `c4f7acdff409413f24c5fdbe718a307ffd830a8c`
- Final approved correction commit:
  `31630971842644fc7593dc49faaa7d636566cdbd`
- Local and remote branch HEAD matched before closeout creation.
- Working tree was clean before closeout creation.

### Server repository

- Path: `/home/chuck/projects/photo-organizer-dev`
- Branch: `feature/deployment-linux-runtime`
- Initial 005B fast-forward target:
  `c4f7acdff409413f24c5fdbe718a307ffd830a8c`
- Final server HEAD:
  `31630971842644fc7593dc49faaa7d636566cdbd`
- Protected `docker/.env.development`: present, ignored, and unchanged.
- Protected environment SHA-256:
  `bdae51b28053b2af35b56ac69f78132120baa271b52182dab6ee72bb373d359e`
- Final server tracked working tree: clean.

Only fast-forward reconciliation was used. No reset, clean, stash, rebase,
forced checkout, non-fast-forward merge, or server hot-patch occurred.

## 3. Starting Runtime and State

At the 005B baseline:

- PostgreSQL, Redis, backend, and frontend were healthy;
- backend and frontend were published only on loopback;
- PostgreSQL and Redis were unpublished;
- Redis returned `PONG` and database size `0`;
- Assets, runs, provenance, Vault files, and previews were zero;
- `STORAGE_MODE=local`;
- the effective minimum media size was `51200` bytes;
- PyTorch CUDA was operational on the NVIDIA GeForce RTX 5070 Ti;
- no Windows, NAS-authoritative, Test, or Production resource was used.

The retained named volumes were:

- `photo-organizer-dev_postgres_data`;
- `photo-organizer-dev_redis_data`;
- `photo-organizer-dev_application_storage`;
- pre-existing `portainer_data`.

The protected container IDs retained throughout all operations that did not
explicitly restart or recreate them were:

| Service | Container ID |
|---|---|
| PostgreSQL | `42bbb232f702da07dd6a302153c0a4aebd910aa148a7d82b7285ed4080112712` |
| Redis | `107e680b822a993871afff260e4e55273e8d30ea405b2474070678f849a08a57` |
| Frontend | `4403b0d146f730581fa725dc62bc330b3fe92241011e8e4ce3f39689756904e9` |

## 4. Generator Execution

### Image and tool identity

- Backend image:
  `sha256:823e68da6a74883920b934931a18f7d1d96f1a83082c10a9b67a4e97dfa1b2b7`
- Image runtime user: `photo-organizer`
- One-off override user: UID/GID `1000:1000`
- Python: `3.11.9`
- Pillow: `12.2.0`
- Generator:
  `/home/chuck/projects/photo-organizer-dev/scripts/fixtures/create_controlled_photo_fixture_set.py`
- Generator SHA-256:
  `a03711da38b6d659e8e657ff50a34d72e6f344ad1d97dd2a5cc4ab4543322f68`

The generator was invoked once with this command contract:

```bash
time sudo docker run \
  --rm \
  --network none \
  --user 1000:1000 \
  --read-only \
  --tmpfs /tmp:rw,nosuid,nodev,noexec,size=64m \
  --env PYTHONDONTWRITEBYTECODE=1 \
  --mount type=bind,src=/home/chuck/projects/photo-organizer-dev/scripts/fixtures/create_controlled_photo_fixture_set.py,dst=/tool/create_controlled_photo_fixture_set.py,readonly \
  --mount type=bind,src=/home/chuck/photo-organizer-fixtures/m005,dst=/home/chuck/photo-organizer-fixtures/m005 \
  --entrypoint python \
  sha256:823e68da6a74883920b934931a18f7d1d96f1a83082c10a9b67a4e97dfa1b2b7 \
  /tool/create_controlled_photo_fixture_set.py \
  --fixture-root /home/chuck/photo-organizer-fixtures/m005 \
  --minimum-file-size-bytes 51200
```

Result:

```text
exit=0
duration=0.503s
source files=4
unique hashes=3
```

The container had no network, published port, application-storage mount,
database or Redis connection, Docker socket, credentials, NAS mount, Test
mount, or Production mount. Its root was read-only, and only the controlled
M005 fixture root was writable. The container was automatically removed.

## 5. Fixture Evidence

The fixture root remains:

`/home/chuck/photo-organizer-fixtures/m005`

The source files and manifest were generated by the committed deterministic
script. They contain synthetic patterns and controlled metadata, not personal
media or downloaded third-party media.

| File | Bytes | Dimensions | SHA-256 |
|---|---:|---:|---|
| `source/unique_a.jpg` | 1,594,899 | 1024 x 768 | `4d52dee4a8c4d53f292d00966e5d63a6c536f011ce64d0fa7c177ce826c163cb` |
| `source/unique_a_duplicate.jpg` | 1,594,899 | 1024 x 768 | `4d52dee4a8c4d53f292d00966e5d63a6c536f011ce64d0fa7c177ce826c163cb` |
| `source/unique_b.jpg` | 1,401,458 | 960 x 720 | `957a34f43fbb17ca7efe9b77b376c1b3737c4f1108fa436f1c5d237fa52d57ae` |
| `source/preview_source.tiff` | 1,440,356 | 800 x 600 | `46b4b7e8fcc21974e6ed89b37461d0ea9c34bff6e41d531153f7c13e5aa9bac8` |
| `fixture_manifest.json` | 4,318 | n/a | `bce699c85d0bfa608bba03e62813fe9d5a3fbc01e4e0b1ebd840987e42a7cc6b` |

All retained directories are owned by `chuck:chuck` with mode `0755`. All
media files and the manifest are owned by `chuck:chuck` with mode `0644`.
Every media file exceeds the live 51,200-byte threshold.

`unique_a_duplicate.jpg` is byte-for-byte identical to `unique_a.jpg`.
Independent verification proved four source files and three unique hashes.
The manifest was outside the mounted `source` directory and was not an intake
candidate.

## 6. Source Profile and Source Identity

Exactly one Source Profile was created through:

```text
POST /api/admin/source-profiles
```

Sanitized request:

```json
{
  "source_label": "M005 Controlled Fixture Source",
  "source_type": "local_folder",
  "source_root_path": "/mnt/photo-organizer-fixtures/m005",
  "profile_status": "active"
}
```

Result:

- HTTP `200`;
- `already_exists=false`;
- Source Profile ID `1`;
- profile status `active`;
- Source Endpoint ID `null`;
- Source Endpoint count `0`;
- endpoint-relative root `null`;
- no cloud provider, account, acquisition, or managed-staging value.

Without acknowledgment:

- Source Selection returned `not_selected`;
- availability was `needs_attention`;
- readiness returned `blocked`;
- blocker code was `development_fixture_acknowledgment_required`;
- no Source, run, Asset, provenance, Vault, preview, or Redis state changed.

With explicit acknowledgment and the temporary exact-path configuration:

- Source Selection returned `selected`;
- availability was `available`;
- workflow was `filesystem_source_intake`;
- provider was `linux_development_fixture_probe_v1`;
- runtime root was `/mnt/photo-organizer-fixtures/m005`;
- durable identity was `not_verified`;
- identity match was `development_fixture_path_only`;
- readiness was `needs_review`;
- `can_run_source_intake=true`;
- `requires_operator_acknowledgment=true`;
- `hard_block=false`;
- no durable identifier or Source Endpoint was invented.

After the backend returned to permanent topology, an acknowledged read-only
diagnostic correctly failed closed:

- selection: `not_selected`;
- readiness: `blocked`;
- hard block: `true`;
- blocker: `unsupported_source_root_boundary`.

The Source Profile remains recorded, but it is not durable-ready and cannot
access the retained host fixture without a future deliberate configuration
and bind.

## 7. Dispatch and Intake History

The public request schema accepted exactly:

```json
{
  "source_profile_id": 1,
  "filesystem_options": {
    "source_intake_limit": 4,
    "ingest_batch_size": 4,
    "acknowledge_legacy_or_review": true
  }
}
```

Both execution attempts used:

```text
POST /api/admin/run-ingestion/dispatch
```

### Run 1 - preserved failure

The initially authorized dispatch returned HTTP `200` and created:

- Source Intake Run `1`;
- Ingestion Run `1`.

It then failed asynchronously during `collect_input` because the configured
local Development drop zone did not exist:

```text
Error: Folder not found: /app/storage/drop_zone
```

Run 1 evidence:

| Field | Value |
|---|---|
| Status | `failed` |
| Started | `2026-07-29T21:55:37.233088Z` |
| Finished | `2026-07-29T21:55:37.265303Z` |
| Files scanned | 0 |
| Selected/staged/new unique | 0 / 0 / 0 |
| Error | `Stage failed: collect_input` |
| Report | `/app/storage/logs/source_intake_reports/source_intake_1.json` |
| Report bytes | 880 |
| Report SHA-256 | `a18bcdc0bcd43b4db77c95f356cb1e78adfe617664ee0be39f976d1ccae5e63d` |

The failure created no Asset, provenance observation, Vault object, preview,
or fixture mutation. The run, ingestion run, report, logs, Source Profile,
fixtures, database, volumes, and containers were preserved.

### Approved narrow correction

The failure showed that local Development startup created Vault, previews,
and review directories but not the configured drop zone required by Source
Intake.

The Product Owner separately authorized the smallest correction:

- `backend/app/core/runtime_paths.py`;
- `backend/tests/test_runtime_configuration.py`;
- the 005B prompt evidence/addendum.

Commit `3163097` makes local Development startup create the configured drop
zone alongside the already authorized local directories. It does not create
unrelated directories, change NAS fail-closed behavior, change Test or
Production behavior, or alter Source Intake, provenance, deduplication, Vault,
preview, schema, or public API semantics.

After Product Owner review and commit/push, the server fast-forwarded to
`3163097`. The GPU backend image was built exactly once:

```bash
time sudo docker compose \
  --env-file docker/.env.development \
  --file docker/compose.development.yml \
  --file docker/compose.development.gpu.yml \
  build backend
```

Build result:

```text
exit=0
duration=5.339s
image=photo-organizer-dev-backend:latest
image ID=sha256:3aff12de14ab834a9ea644fecb6f224de88fa3d19f5f69e7823ea159a08af072
size=3808360185
user=photo-organizer
working directory=/app
command=["python","scripts/container_entrypoint.py"]
```

Only the backend was recreated with the temporary fixture override. The
recreation completed in `6.941s`. Normal startup created:

```text
/app/storage/drop_zone
mode=0755
uid=999
gid=999
files=0
```

PostgreSQL, Redis, frontend, and all volumes remained intact.

### Run 2 - approved recovery

After an explicit recovery approval, the dispatch request was submitted
exactly once more. It returned HTTP `200` and created:

- Source Intake Run `2`;
- Ingestion Run `2`.

Run 2 completed:

| Field | Value |
|---|---|
| Status | `completed` |
| Started | `2026-07-29T23:05:41.782760Z` |
| Finished | `2026-07-29T23:05:42.045940Z` |
| Elapsed | `0.249047133s` |
| Files scanned | 4 |
| Skipped known | 0 |
| Selected | 4 |
| Staged | 4 |
| Processed new unique | 3 |
| Failed or rejected | 0 |
| Remaining unknown | 0 |
| Report | `/app/storage/logs/source_intake_reports/source_intake_2.json` |
| Report bytes | 1,119 |
| Report SHA-256 | `68e9f9f03bd47c811685f79bbefc017795414735a2129c7453a16f99bc1b5bda` |

The pipeline logged one exact duplicate, three copied Vault objects, three
inserted Assets, one added duplicate provenance observation, four metadata
observations, and zero processing failures. The drop zone was cleaned to zero
files.

No further dispatch was submitted.

## 8. Asset, Vault, Duplicate, and Provenance Results

Assets are keyed by SHA-256 rather than a separate numeric `id`. The final
three Asset identities are:

| SHA-256 | Canonical filename | Bytes | Vault path |
|---|---|---:|---|
| `4d52dee4a8c4d53f292d00966e5d63a6c536f011ce64d0fa7c177ce826c163cb` | `unique_a.jpg` | 1,594,899 | `/app/storage/vault/4d/4d52dee4a8c4d53f292d00966e5d63a6c536f011ce64d0fa7c177ce826c163cb.jpg` |
| `957a34f43fbb17ca7efe9b77b376c1b3737c4f1108fa436f1c5d237fa52d57ae` | `unique_b.jpg` | 1,401,458 | `/app/storage/vault/95/957a34f43fbb17ca7efe9b77b376c1b3737c4f1108fa436f1c5d237fa52d57ae.jpg` |
| `46b4b7e8fcc21974e6ed89b37461d0ea9c34bff6e41d531153f7c13e5aa9bac8` | `preview_source.tiff` | 1,440,356 | `/app/storage/vault/46/46b4b7e8fcc21974e6ed89b37461d0ea9c34bff6e41d531153f7c13e5aa9bac8.tiff` |

Every Vault object hash equals its Asset identity and controlled source hash.
There are exactly three Vault files for three unique hashes. No second Asset
or Vault object was created for `unique_a_duplicate.jpg`.

Four provenance observations were created:

| Provenance ID | Asset SHA-256 prefix | Source-relative path |
|---:|---|---|
| 1 | `46b4b7e8...` | `preview_source.tiff` |
| 2 | `4d52dee4...` | `unique_a.jpg` |
| 3 | `957a34f4...` | `unique_b.jpg` |
| 4 | `4d52dee4...` | `unique_a_duplicate.jpg` |

All four observations reference:

- Source Profile `1`;
- Ingestion Run `2`;
- source label `M005 Controlled Fixture Source`;
- source type `local_folder`;
- source root `/mnt/photo-organizer-fixtures/m005`;
- their exact source-relative path.

The current `source_hash` compatibility column remained `NULL`. Content
association is nevertheless explicit through `asset_sha256`, the observed
source path, Source Profile, Ingestion Run, and matching immutable Vault
hash. No provenance repair or schema change was authorized or performed.

## 9. Metadata Results

Final canonical Asset metadata matched the controlled fixture expectations:

| File | Dimensions | Captured at | Capture type | Trust |
|---|---:|---|---|---|
| `unique_a.jpg` | 1024 x 768 | `2020-01-02T03:04:05Z` | `digital` | `high` |
| `unique_b.jpg` | 960 x 720 | `2021-06-07T08:09:10Z` | `digital` | `high` |
| `preview_source.tiff` | 800 x 600 | null | `unknown` | `low` |

All three Assets are canonical and visible. The pipeline inserted four
metadata observations, canonicalized three Assets, and created two Events for
the two dated JPEG Assets. No GPS data was present, so place grouping skipped
all three Assets.

## 10. Preview, Media, and UI Validation

Before preview processing, the supported status endpoint reported one pending
preview. Exactly one supported preview run was started:

```text
POST /api/admin/heic-preview/run
```

Preview Run `1` completed:

| Field | Value |
|---|---|
| Pending | 1 |
| Processed | 1 |
| Succeeded | 1 |
| Failed | 0 |
| TIFF generated | 1 |
| HEIC generated | 0 |

Preview artifact:

- path:
  `/app/storage/previews/46/46b4b7e8fcc21974e6ed89b37461d0ea9c34bff6e41d531153f7c13e5aa9bac8.jpg`;
- bytes: `343628`;
- SHA-256:
  `46a2be8491f03b11c4d096e26095c4a4830db9beae554a4a43e3a94ee7f78347`;
- format: JPEG;
- dimensions: 800 x 600.

Preview report:

- path:
  `/app/storage/logs/heic_preview_reports/heic_preview_2026-07-29T23-12-03.56801200-00.json`;
- bytes: `583`;
- SHA-256:
  `8a79ef401d110a97942f1e8375f0b4b764468e58e1e3f6dea57fecc21b51303e`.

The original TIFF remained unchanged. The two JPEGs correctly used their
original Vault media for display. The TIFF correctly used the generated JPEG
preview. All three original-media URLs and the preview URL returned HTTP
`200`, correct content types and sizes, and matching SHA-256 values.

`GET /api/photos` returned exactly three Assets. Its stable captured response
hash was:

`20e939b7e0c5314706f0cd7b6f121b73cfb76cc29c2260171593a7531b5279f1`

The Product Owner manually confirmed that all three controlled Assets rendered
in the Workbench. No fourth duplicate card and no personal media appeared.

No general thumbnail was required by current behavior, and no thumbnail stage
was invoked.

## 11. Processing and GPU Evidence

The completed Source Intake invoked:

- ingestion-context schema synchronization;
- metadata-canonicalization schema synchronization;
- place schema synchronization;
- input collection and drop-zone staging;
- filtering;
- hashing;
- exact deduplication;
- Vault storage;
- database ingestion;
- drop-zone cleanup;
- EXIF extraction;
- metadata normalization;
- metadata observations and canonicalization;
- place grouping;
- event clustering.

Face processing, face embeddings, review crops, duplicate lineage, and place
geocoding enrichment remained decoupled and were not run.

No model was downloaded. The intake and preview evidence does not prove GPU
use by those stages.

PyTorch CUDA continuity passed before and after processing and again in the
final permanent topology:

```text
UID=999
torch=2.11.0+cu130
CUDA runtime=13.0
CUDA available=True
device count=1
device=NVIDIA GeForce RTX 5070 Ti
tensor result=357389824.0
```

TensorFlow emitted CPU-oriented CUDA-driver warnings. TensorFlow/DeepFace GPU
execution remains unvalidated; only PyTorch CUDA is confirmed.

## 12. Restart and Persistence

Before restart:

- no Source Intake or preview job was active;
- database counts, source and run IDs, fixture hashes, Vault hashes, preview
  hash, report hashes, API response hash, media hashes, image ID, mounts,
  ports, Redis state, and container IDs were recorded.

Exactly one four-service restart used:

```bash
sudo docker compose \
  --env-file docker/.env.development \
  --file docker/compose.development.yml \
  --file docker/compose.development.gpu.yml \
  --file /home/chuck/photo-organizer-fixtures/m005/compose.fixture.override.yml \
  restart
```

The command exited `0`. All four services were healthy by bounded poll `5`.
Container IDs and image IDs remained unchanged, and no image build or volume
operation occurred during restart.

Post-restart checks proved:

- no new Source Intake or preview run;
- all database counts unchanged;
- all seven application-storage files unchanged by path, size, and hash;
- fixture files and manifest unchanged;
- media and API responses unchanged;
- Redis still `PONG` with database size `0`;
- PyTorch CUDA still operational.

## 13. Return to Permanent Topology

Only the backend was recreated once using the permanent Development Compose
file and GPU overlay, without the temporary fixture override and without a
second image build.

Result:

```text
exit=0
backend container ID=2ce2bf2cbfe46b8b93e72423947f4ab6c2483e923a018248bce79617938235a0
backend image=sha256:3aff12de14ab834a9ea644fecb6f224de88fa3d19f5f69e7823ea159a08af072
restart count=0
status=running
health=healthy
```

PostgreSQL, Redis, and frontend container IDs remained unchanged. The backend
had only the application-storage volume mounted. It had:

```text
DEVELOPMENT_FIXTURE_SOURCE_ROOT entries=0
fixture bind mounts=0
```

Before removal, the temporary override was verified as:

```text
path=/home/chuck/photo-organizer-fixtures/m005/compose.fixture.override.yml
owner/group=chuck:chuck
mode=0644
bytes=284
SHA-256=6e6d7d26cd18f5ec628b4ebd0cb8fa296a8d02674fa3aa382370c83325742614
secret indicators=none
```

The exact regular file was then removed once. No fixture media, manifest,
database evidence, Vault object, preview, report, provenance row, run record,
or application volume was removed.

Final checks proved:

- override absent;
- fixture source and manifest retained;
- every fixture hash unchanged;
- backend fixture environment count `0`;
- backend fixture bind count `0`;
- permanent Compose topology healthy.

A future fixture rerun must deliberately recreate and review a temporary
override and bind. The retained Source Profile does not grant automatic host
access.

## 14. Final State

### Services

| Service | Final state | Publication |
|---|---|---|
| PostgreSQL | healthy | unpublished |
| Redis | healthy | unpublished |
| Backend | healthy | `127.0.0.1:18001 -> 8001/tcp` |
| Frontend | healthy | `127.0.0.1:13000 -> 3000/tcp` |

Every final container reported restart count `0`.

### Database

| Relation | Rows |
|---|---:|
| `access_nodes` | 0 |
| `asset_metadata_observations` | 4 |
| `assets` | 3 |
| `events` | 2 |
| `heic_preview_runs` | 1 |
| `ingestion_runs` | 2 |
| `ingestion_sources` | 1 |
| `provenance` | 4 |
| `source_endpoint_observed_paths` | 0 |
| `source_endpoints` | 0 |
| `source_intake_runs` | 2 |

### Application storage

Exactly seven files remain:

- three Vault media objects;
- one TIFF display preview;
- failed Source Intake Run 1 report;
- successful Source Intake Run 2 report;
- Preview Run 1 report.

Their SHA-256 values match the recorded baselines. The drop zone and
quarantine contain zero files. No ingestion-failure file or thumbnail exists.

### Isolation and resource policy

- No Windows path or data was mounted or ingested.
- No NAS-authoritative path or data was mounted or ingested.
- No Test or Production environment was started or accessed.
- No iCloud authentication or acquisition occurred.
- No credential, Docker socket, or personal-media directory was exposed.
- No CPU, memory, GPU, VRAM, worker, batch, or host resource limit changed.
- The only intake limits were the one-run request values `4` and `4`.

## 15. Deviations and Command Corrections

### Initial Source Intake failure

Run 1 exposed a real missing local Development drop-zone initialization
defect. The run and report were preserved. The Product Owner approved a
separate narrow correction and exactly one recovery dispatch. This is why the
final database contains two Source Intake Runs and two Ingestion Runs while
only Run 2 processed media.

The failed report includes `source_complete=true` despite terminal run status
`failed`. Terminal run status was treated as authoritative. The report was not
edited or interpreted as success.

### Generator image inspection

An initial Go-template image inspection referenced absent
`.Config.Entrypoint` data and returned a template error. A corrected JSON
inspection established `ENTRYPOINT=None`. Generation did not begin until the
remaining identity gates passed.

### Post-generation metadata inspection

A Python formatting expression used `image['Id']` inside shell-conflicting
quoting and raised `NameError`. The guarded generation gate remained intact,
generation completed exactly once, and a corrected read-only inspection
recorded the image metadata afterward.

### Read-only readiness diagnostic

The first acknowledged diagnostic attempted to count `Asset.id`, but Assets
are keyed by `sha256`. It failed before any service call; rollback and close
executed. One approved corrected read-only diagnostic used
`select(func.count()).select_from(model)` and passed with unchanged database
and storage counts.

### Post-ingestion storage assertion and SSH session

The first post-ingestion validator incorrectly expected the quarantine
directory to remain absent. Existing pipeline behavior creates an empty
quarantine directory. The assertion failed after the database evidence had
already printed, and a surrounding shell `exit 1` closed the SSH session.
Services and application state remained healthy. A corrected read-only
validator required an empty quarantine directory and passed. No ingestion was
repeated.

Subsequent commands intentionally avoided shell-level `exit` statements.

### Permanent-topology fail-closed assertion

The final read-only diagnostic expected the lower-level blocker
`development_fixture_root_not_configured`. The readiness service correctly
normalized the permanent-topology result to
`unsupported_source_root_boundary`. Selection and readiness still failed
closed, database counts remained identical, ORM pending sets were empty, and
rollback executed. No rerun or application change was needed.

### Final storage multiset assertion

The final read-only inventory printed all seven correct files and hashes, but
the command's expected list contained an incorrectly transcribed successful
Run 2 report hash. The resulting boolean was `False`. Earlier pre-restart,
post-restart, post-ingestion, and final inventories all independently agree
that the stable report hash is:

`68e9f9f03bd47c811685f79bbefc017795414735a2129c7453a16f99bc1b5bda`

This was a validation-constant error, not a file mutation. No server rerun was
needed.

## 16. Known Limitations and Untested Behavior

- The fixture adapter is exact-path, Development-only, and path-based.
- It is not general or durable Linux Source identity.
- It has no Source Endpoint, durable fingerprint, access-node identity, or
  durable match.
- Explicit provider configuration and acknowledgment are still required.
- The retained Source Profile is not currently runnable in permanent topology.
- `source_hash` remains unpopulated in the current provenance representation.
- Background jobs remain in-process and non-durable.
- Only PyTorch CUDA is validated; TensorFlow/DeepFace GPU use is not.
- Personal-media and broad-library ingestion were not tested.
- Repeated intake/idempotency was intentionally not tested.
- Cross-Source duplicate behavior was not tested.
- General Linux removable, optical, NAS, and cloud Source identity was not
  tested.
- iCloud, NAS-backed application storage, face processing, sustained load,
  host-reboot persistence after ingestion, backup/restore, Test, Production,
  promotion, and rollback were not tested.

## 17. Recommended Next Milestone

Proceed to:

`006_deployment_remote_vscode_development_workflow_prompt.md`

The next milestone should establish the server repository as the normal
editable Development checkout through VS Code Remote SSH, validate
Copilot/Codex and server-side terminals/tests/Git review, and document the
division of responsibilities among the Windows PC, mini-server, and NAS.

It must not broaden Linux Source identity or ingest personal media.

## 18. Git Status

Immediately before closeout creation:

```text
branch=feature/deployment-linux-runtime
HEAD=31630971842644fc7593dc49faaa7d636566cdbd
remote HEAD=31630971842644fc7593dc49faaa7d636566cdbd
working tree=clean
```

This closeout and the parent Milestone 005 closeout are the only expected new
working-tree files. The Coder did not commit or push them.

