# Milestone 005 - Linux Development Controlled Fixture Validation Closeout

## 1. Outcome

Milestone 005 completed successfully.

The complete milestone arc established a tightly bounded Development-only
Linux fixture pathway, generated deterministic non-personal media, completed
one controlled recovery ingestion through Source Intake, validated Asset,
Vault, provenance, exact-duplicate, metadata, preview, API, UI, GPU-continuity,
and restart behavior, and then removed the temporary fixture access.

The final backend is healthy under the permanent Development Compose topology
with no fixture environment value or host bind.

Detailed evidence is recorded in:

- `005A_deployment_linux_development_fixture_adapter_live_validation_and_generator_closeout.md`;
- `005B_deployment_linux_controlled_fixture_ingestion_and_persistence_validation_closeout.md`.

## 2. Repository State

- Windows repository:
  `C:\Users\chhen\My Drive\AI Photo Organizer\Photo Organizer_v1`
- Server repository:
  `/home/chuck/projects/photo-organizer-dev`
- Branch: `feature/deployment-linux-runtime`
- Final Windows, remote, and server commit:
  `31630971842644fc7593dc49faaa7d636566cdbd`
- Protected server `docker/.env.development`: present, ignored, and unchanged.
- Both working trees were clean before these closeouts were created.

No commit or push was performed by the Coder.

## 3. Complete Milestone Arc

### Initial Linux Source Identity stop

Reconnaissance found that existing Windows filesystem identity providers could
not be honestly reused as durable Linux Source identity. The milestone stopped
rather than enabling arbitrary Linux paths or inventing a durable identifier.

### Development-only fixture adapter

The Product Owner approved a narrow fixture adapter that:

- activates only in Development;
- requires exact configured-root equality;
- requires explicit provider selection and acknowledgment;
- rejects arbitrary Linux paths;
- returns `needs_review`, not durable-ready;
- creates no Source Endpoint or durable identity;
- remains inactive in Test and Production.

Acknowledgment propagation was added through the existing dispatch request
field without changing the public schema or weakening the independent Source
Intake launch guard.

### Milestone 005A live validation

005A used one backend image build and two backend-only recreations:

1. without fixture configuration, proving the adapter remained unavailable and
   fail-closed;
2. with an exact temporary read-only bind, proving only the approved fixture
   root could reach acknowledged `needs_review`.

The PostgreSQL, Redis, frontend, and named volumes remained intact. A
deterministic fixture generator and focused regression coverage were then
committed for 005B.

### Milestone 005B generation and ingestion

005B generated four deterministic synthetic files on server NVMe:

- two unique JPEG contents;
- one byte-identical duplicate JPEG;
- one unique TIFF eligible for the existing display-preview workflow.

It created Source Profile `1` and no Source Endpoint.

Selection and readiness failed closed without acknowledgment. With the exact
temporary root and explicit acknowledgment, selection succeeded while
readiness remained `needs_review` with no durable identity.

The first dispatch created Source Intake Run `1` and Ingestion Run `1` but
failed before scanning because local Development startup had not created its
configured drop zone. All evidence was preserved.

The Product Owner approved a narrow startup correction at commit `3163097`.
After one backend image rebuild and backend-only recreation, the configured
drop zone existed. One approved recovery dispatch created Source Intake Run
`2` and Ingestion Run `2` and completed:

```text
scanned=4
selected=4
staged=4
new unique=3
failed/rejected=0
remaining unknown=0
```

No further ingestion dispatch occurred.

## 4. Final Data and Provenance

Final database counts:

| Relation | Rows |
|---|---:|
| Source Profiles | 1 |
| Source Endpoints | 0 |
| Source Intake Runs | 2 |
| Ingestion Runs | 2 |
| Assets | 3 |
| Provenance | 4 |
| Metadata observations | 4 |
| Events | 2 |
| Preview runs | 1 |

The three Asset identities and Vault hashes are:

- `4d52dee4a8c4d53f292d00966e5d63a6c536f011ce64d0fa7c177ce826c163cb`;
- `957a34f43fbb17ca7efe9b77b376c1b3737c4f1108fa436f1c5d237fa52d57ae`;
- `46b4b7e8fcc21974e6ed89b37461d0ea9c34bff6e41d531153f7c13e5aa9bac8`.

The duplicate JPEG created no additional Asset or Vault object. It produced a
separate valid provenance observation for its distinct Source-relative path.
All four provenance observations reference Source Profile `1` and Ingestion
Run `2`.

The fixture source files and manifest remain unchanged outside application
storage at:

`/home/chuck/photo-organizer-fixtures/m005`

## 5. Metadata, Preview, API, and UI

The two JPEGs retained their controlled high-trust capture timestamps:

- `2020-01-02T03:04:05Z`;
- `2021-06-07T08:09:10Z`.

The TIFF correctly retained unknown/low-trust capture time.

Exactly one supported preview run generated an 800 x 600 JPEG preview for the
TIFF:

`46a2be8491f03b11c4d096e26095c4a4830db9beae554a4a43e3a94ee7f78347`

The JPEG Assets used their original Vault objects for display. The TIFF used
the generated preview while retaining its original TIFF. All media endpoints
returned HTTP `200`, and the Product Owner confirmed all three controlled
Assets rendered in the Workbench.

No general thumbnail was required or generated.

## 6. Restart, GPU, and Final Topology

Exactly one bounded four-service restart preserved:

- database counts and relationships;
- both intake runs and reports;
- the preview run and report;
- all Vault and preview hashes;
- API and media readability;
- fixture hashes;
- Redis state;
- PyTorch CUDA operation.

Final PyTorch evidence:

```text
torch=2.11.0+cu130
CUDA=13.0
device=NVIDIA GeForce RTX 5070 Ti
CUDA tensor validation=pass
```

The backend was then recreated once without the temporary fixture override.
The override file was verified and removed. The fixture media and manifest
were retained.

Final topology:

- PostgreSQL healthy and unpublished;
- Redis healthy and unpublished;
- backend healthy on `127.0.0.1:18001`;
- frontend healthy on `127.0.0.1:13000`;
- all Development volumes intact;
- backend fixture environment entries: `0`;
- backend fixture bind mounts: `0`;
- no Test or Production environment;
- no Windows or NAS-authoritative media access.

## 7. Authority and Safety Boundaries

The supported execution path remained:

```text
public dispatch API
-> backend Source Selection
-> backend readiness
-> independent Source Intake acknowledgment guard
-> existing Source Intake pipeline
-> existing Asset, Vault, provenance, metadata, and preview authorities
```

The milestone did not:

- enable a default Linux provider;
- accept arbitrary Linux paths;
- create a durable Source identifier;
- create a Source Endpoint;
- make acknowledgment implicit;
- bypass Source Intake;
- modify Production, Test, NAS, or Windows state;
- ingest personal media;
- change resource limits;
- introduce permanent fixture access.

## 8. Retained Limitations

- General durable Linux Source identity remains future work.
- The fixture adapter is Development-only, exact-path, manually configured,
  acknowledgment-gated, and non-durable.
- The retained Source Profile cannot run in permanent topology without a
  deliberate future fixture configuration and bind.
- Current provenance leaves the compatibility `source_hash` field null,
  although Asset SHA-256, Source, run, observed path, and Vault hash preserve
  the validated lineage.
- Background jobs remain in-process and non-durable.
- PyTorch CUDA is validated; TensorFlow/DeepFace GPU execution is not.
- Personal-media ingestion, broad libraries, repeated intake, cross-Source
  duplicates, iCloud, NAS-backed storage, Test, Production, sustained load,
  host-reboot recovery after ingestion, backup/restore, promotion, and
  rollback remain untested.

## 9. Approved Deviations

The principal deviation was the preserved first-intake failure caused by the
missing local Development drop zone. It was not concealed or reset. A
separately approved narrow startup correction and one recovery dispatch
completed the milestone while retaining Run `1`, Ingestion Run `1`, and their
failed report.

Several read-only validation commands also contained incorrect assumptions or
constants. They are documented in detail in the 005B closeout. None required
an application change or repeated intake/preview/restart operation.

## 10. Recommended Next Milestone

Proceed to:

`006_deployment_remote_vscode_development_workflow_prompt.md`

Its purpose should be to make the server repository the normal authoritative
editable Development checkout through VS Code Remote SSH, validate
Copilot/Codex and server-side development tooling, and document what remains
on the Windows PC, mini-server, and NAS.

Linux Source identity expansion and personal-media ingestion must remain
separate future work.

## 11. Git Status

Immediately before closeout creation:

```text
branch=feature/deployment-linux-runtime
HEAD=31630971842644fc7593dc49faaa7d636566cdbd
remote HEAD=31630971842644fc7593dc49faaa7d636566cdbd
working tree=clean
```

The only expected new files are:

- `005B_deployment_linux_controlled_fixture_ingestion_and_persistence_validation_closeout.md`;
- `005_deployment_linux_development_controlled_fixture_validation_closeout.md`.

They must remain uncommitted until Product Owner review.
