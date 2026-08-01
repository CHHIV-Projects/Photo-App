# Photo Organizer Test Environment Guide

## 1. Purpose

The Test environment is the isolated proving ground for an exact committed
Photo Organizer candidate on `henderson-server1`.

Development and Test have different jobs:

| Environment | Purpose | Runtime source | Mutable data |
|---|---|---|---|
| Development | Active coding and developer validation | Editable Development workspace and Development images | Development-only volumes |
| Test | Acceptance testing of one exact pushed commit | Immutable commit-specific images; no source mount | Test-only volumes |
| Production | Future approved deployment | Not implemented | Not implemented |

Test is not another editable source tree. Editing the repository does not
change a deployed Test container. A new Test candidate cannot replace the
first candidate in this milestone; controlled replacement and rollback belong
to a future promotion milestone.

Test data is disposable in principle, but it must never be deleted casually.
There is no reset, teardown, volume removal, or cleanup action in the Test
operator. Preserve unexpected resources and evidence, then escalate.

## 2. Locked Test Identity

The fixed Test identity is:

```text
Compose project:        photo-organizer-test
Frontend publication:  127.0.0.1:13001 -> container 3000
Backend publication:   127.0.0.1:18002 -> container 8001
Runtime profile:        test
Storage mode:           local
Configuration:          /home/chuck/.config/photo-organizer/test.env
Release manifest:       /home/chuck/.local/state/photo-organizer/test/release.json
```

PostgreSQL and Redis are not published to the host. Test owns two networks:

- `photo-organizer-test_application_internal` for PostgreSQL, Redis, and the
  backend; this network is Docker-internal;
- `photo-organizer-test_browser_edge` for the backend and frontend.

Test owns exactly three named volumes:

- `photo-organizer-test_application_storage`;
- `photo-organizer-test_postgres_data`;
- `photo-organizer-test_redis_data`.

None of those resources is shared with `photo-organizer-dev`. Test also has its
own Vault, previews, thumbnails, staging, logs, exports, model cache, database,
Redis state, credentials, and release state.

## 3. Safety Boundaries

Docker is shared host infrastructure. Portainer and Development are separate
workloads. Test actions are fixed and scoped only to project
`photo-organizer-test`.

Docker commands use the normal visible interactive `sudo` prompt. Type the
Ubuntu password only at that prompt. Do not add `chuck` to the Docker group,
change Docker socket permissions, store a sudo password, or modify sudoers.

Never use a broad Docker stop, restart, remove, or prune command. Never use a
Compose teardown operation or a volume-removal option. Do not recreate
Development, change Portainer, expose an application port to the LAN, copy
Development data or secrets, or mount Development storage into Test.

The NAS is not used by Test in this milestone. Test application data uses local
Docker named volumes.

## 4. Files and Runtime Artifacts

Tracked implementation files are:

- `docker/compose.test.yml`;
- `docker/compose.test.gpu.yml`;
- `docker/.env.test.example`;
- `scripts/operator/test/photo_organizer_test_operator.sh`;
- this guide.

The real configuration and release manifest live outside Git at their fixed
paths. The configuration is secret-bearing and must remain mode `0600`. The
release manifest is nonsecret, written atomically, and records:

- the full 40-character Git commit SHA;
- backend and frontend immutable image references;
- exact backend and frontend image IDs;
- PostgreSQL and Redis image references and IDs;
- Compose project and Test loopback ports;
- preparation and deployment timestamps.

Do not create `docker/.env.test` inside the repository.

## 5. Candidate Contract

`prepare-candidate` accepts only a repository state that is:

- clean, including untracked non-ignored files;
- at a full committed SHA;
- exactly equal to its configured upstream branch;
- built from committed Dockerfiles, Compose files, and source inputs.

It builds or verifies these immutable tags:

```text
photo-organizer-test-backend:<full-commit-sha>
photo-organizer-test-frontend:<full-commit-sha>
```

The backend uses the existing non-reloading GPU image target. The GPU overlay
sets `REQUIRE_GPU=true`, so the backend fails closed if CUDA is unavailable.
The frontend uses the production `next build` and `next start` stages. It
receives the private Test backend at runtime as:

```text
BACKEND_INTERNAL_BASE_URL=http://backend:8001
```

The browser uses same-origin `/api/*` and `/media/*` paths. No Test-specific
backend hostname or port is compiled into the frontend image.

The operator does not create a `latest` tag and does not push to a registry.
Future Production promotion must reuse the same Test-validated image IDs, or
equivalent immutable artifacts, rather than rebuilding an approved candidate.

## 6. Test Operator Actions

Run the operator from the authoritative repository:

```bash
cd /home/chuck/projects/photo-organizer-dev
./scripts/operator/test/photo_organizer_test_operator.sh <action>
```

Allowed actions are:

### `self-test`

Read-only and non-live. It checks fixed paths, required tools, the action
allowlist, candidate guard logic, atomic manifest writing, and key Compose
isolation assertions. It does not access the Docker daemon or create a resource.

### `init-config`

One-time configuration initialization. It refuses to overwrite the fixed Test
config, generates a separate Test-only PostgreSQL credential, uses mode `0600`,
prints no secret, and creates no Docker resource. Optional provider and cloud
credentials remain unset.

### `prepare-candidate`

Validates the clean pushed commit, builds immutable backend and frontend images,
records exact image IDs and labels, and atomically writes `release.json`. It
does not start or replace containers. If a commit-specific tag already exists,
the operator reuses it only after its exact revision, environment, and release
labels pass. It never overwrites a conflicting tag.

### `candidate-status`

Reports repository HEAD, upstream identity, cleanliness, prepared candidate,
image references and IDs, and—after deployment—the candidate identity actually
used by the backend and frontend containers.

### `deploy-candidate`

The guarded one-time first deployment. It refuses any existing or ambiguous
Test container, network, or volume. It then:

1. verifies config, manifest, image labels, image IDs, ports, and clean pushed
   repository identity;
2. creates only the four Test containers, two Test networks, and three Test
   volumes without starting application services;
3. starts only Test PostgreSQL and Redis and waits for health;
4. proves PostgreSQL has no application tables and Redis has no keys;
5. proves application storage is empty;
6. uses an ephemeral exact-candidate backend container to create only the fixed
   storage directories and ownership;
7. runs `python scripts/init_db.py` against Test only, without `--reset`;
8. proves the initialized database contains no Asset, Source Profile, or
   provenance rows;
9. starts the exact backend and frontend images and waits for health;
10. records the deployment timestamp, runs `release-status`, and checks health.

If any step fails or becomes ambiguous, resources and evidence are preserved.
Do not rerun deployment, delete partial resources, or improvise cleanup.

### `start`

Starts only the existing four Test containers. It verifies the recorded release
first and uses container start behavior only. It does not build, pull, create,
recreate, deploy, initialize, or replace a candidate.

### `stop`

Verifies release identity, then uses bounded Compose stop for only Test. It
retains containers, networks, images, named volumes, database state, configured
Redis storage, and application storage.

### `status`, `health`, and `release-status`

`status` shows all Test services. `health` checks server loopback and requires
the backend to report runtime profile `test` with database and Redis available.
`release-status` verifies the exact four services, candidate SHA and image IDs,
Test-only volumes and mappings, exact networks, loopback ports, unpublished
PostgreSQL and Redis, runtime profile, and runtime-neutral frontend destination.

`release-status` uses:

```text
PASS     exit 0
WARNING  exit 0 (normally retained Test services are intentionally stopped)
FAILURE  nonzero; stop and preserve evidence
```

### `logs` and `follow-logs`

Both remain scoped to `photo-organizer-test`. `logs` returns a bounded 200-line
tail. Press Ctrl+C to end `follow-logs`; exit code 130 is treated as normal user
cancellation.

## 7. Normal Operation After First Deployment

Start Test:

```bash
./scripts/operator/test/photo_organizer_test_operator.sh start
./scripts/operator/test/photo_organizer_test_operator.sh health
./scripts/operator/test/photo_organizer_test_operator.sh release-status
```

Inspect Test:

```bash
./scripts/operator/test/photo_organizer_test_operator.sh status
./scripts/operator/test/photo_organizer_test_operator.sh logs
```

Stop Test while retaining all state:

```bash
./scripts/operator/test/photo_organizer_test_operator.sh stop
./scripts/operator/test/photo_organizer_test_operator.sh status
```

Do not run `deploy-candidate` as a normal start action. A different candidate
must be handled by the future controlled promotion and rollback milestone.

## 8. Temporary Windows Test Tunnel

Test remains server-loopback-only. For Product Owner browser validation, open a
normal visible Windows terminal and run exactly:

```powershell
ssh -N `
  -L 127.0.0.1:13001:127.0.0.1:13001 `
  -L 127.0.0.1:18002:127.0.0.1:18002 `
  henderson-server1
```

Then open:

```text
Photo Organizer Test: http://localhost:13001
Test backend health:  http://localhost:18002/health
```

This tunnel is explicit, loopback-only, non-persistent, and separate from the
Development tunnel. Press Ctrl+C in its terminal immediately after validation.
Do not add these ports to the Development Windows operator in this milestone.

## 9. Product Owner Live Validation Gates

Do not begin a gate until the prior gate is reviewed. All Docker invocations
below deliberately use visible interactive `sudo`.

### Gate 1 — Shared-host and Development baseline

Prerequisites:

- Milestone 009 implementation is reviewed, committed, and pushed;
- no ingestion, maintenance, backup, or unrelated critical job is active;
- Development and Portainer are expected healthy.

Run read-only inventory:

```bash
cd /home/chuck/projects/photo-organizer-dev
gate1_preflight() {
  set -Eeuo pipefail
  trap 'printf "FAIL: Gate 1 evidence could not be gathered safely. Stop.\n" >&2' ERR

  local failed=0
  local path result
  local expected_branch='feature/deployment-linux-runtime'
  local branch status_output head_sha upstream_ref upstream_sha

  branch="$(git branch --show-current)"
  printf 'Repository branch: %s\n' "${branch:-<detached>}"
  if [[ "$branch" != "$expected_branch" ]]; then
    printf 'FAIL: expected branch %s, found %s.\n' "$expected_branch" "${branch:-<detached>}" >&2
    failed=1
  else
    printf 'PASS: repository branch is %s.\n' "$expected_branch"
  fi

  status_output="$(git status --short)"
  if [[ -n "$status_output" ]]; then
    printf 'FAIL: repository worktree is not clean:\n%s\n' "$status_output" >&2
    failed=1
  else
    printf 'PASS: repository worktree is clean.\n'
  fi

  head_sha=''
  if head_sha="$(git rev-parse --verify 'HEAD^{commit}' 2>/dev/null)" &&
     [[ "$head_sha" =~ ^[0-9a-f]{40}$ ]]; then
    printf 'Repository HEAD: %s\n' "$head_sha"
    printf 'PASS: HEAD resolves to a full committed SHA.\n'
  else
    printf 'FAIL: HEAD does not resolve to a full committed SHA.\n' >&2
    failed=1
  fi

  upstream_ref=''
  upstream_sha=''
  if upstream_ref="$(git rev-parse --abbrev-ref --symbolic-full-name '@{upstream}' 2>/dev/null)" &&
     upstream_sha="$(git rev-parse --verify "${upstream_ref}^{commit}" 2>/dev/null)" &&
     [[ "$upstream_sha" =~ ^[0-9a-f]{40}$ ]]; then
    printf 'Repository upstream: %s\n' "$upstream_ref"
    printf 'Upstream commit: %s\n' "$upstream_sha"
    if [[ "$head_sha" != "$upstream_sha" ]]; then
      printf 'FAIL: HEAD differs from its configured upstream.\n' >&2
      failed=1
    else
      printf 'PASS: HEAD matches its configured upstream.\n'
    fi
  else
    printf 'FAIL: no valid upstream is configured or its commit cannot be verified.\n' >&2
    failed=1
  fi

  if ((failed != 0)); then
    trap - ERR
    printf 'STOP: repository identity checks failed before Docker inventory.\n' >&2
    return 1
  fi

  gate1_expect_empty() {
    local description="$1"
    local evidence="$2"
    if [[ -n "${evidence}" ]]; then
      printf 'FAIL: %s:\n%s\n' "${description}" "${evidence}" >&2
      failed=1
    else
      printf 'PASS: %s is empty\n' "${description}"
    fi
  }

  for path in \
    /home/chuck/.config/photo-organizer/test.env \
    /home/chuck/.local/state/photo-organizer/test/release.json; do
    if [[ -e "${path}" || -L "${path}" ]]; then
      printf 'FAIL: expected-absent runtime artifact exists: %s\n' "${path}" >&2
      failed=1
    else
      printf 'PASS: expected-absent runtime artifact is absent: %s\n' "${path}"
    fi
  done

  sudo docker ps --all \
    --format 'table {{.ID}}\t{{.Names}}\t{{.Label "com.docker.compose.project"}}\t{{.Status}}'
  sudo docker network ls \
    --format 'table {{.ID}}\t{{.Name}}\t{{.Label "com.docker.compose.project"}}'
  sudo docker volume ls \
    --format 'table {{.Name}}\t{{.Label "com.docker.compose.project"}}'

  result="$(sudo docker ps --all \
    --filter 'label=com.docker.compose.project=photo-organizer-test' \
    --format '{{.ID}}|{{.Names}}|{{.Label "com.docker.compose.project"}}|{{.Label "com.docker.compose.service"}}')"
  gate1_expect_empty "Test containers found by Compose project label" "${result}"

  result="$(sudo docker ps --all \
    --format '{{.ID}}\t{{.Names}}\t{{.Label "com.docker.compose.project"}}' |
    awk -F '\t' 'index($2, "photo-organizer-test") > 0')"
  gate1_expect_empty "Test-like containers found by fixed name/prefix" "${result}"

  result="$(sudo docker network ls \
    --filter 'label=com.docker.compose.project=photo-organizer-test' \
    --format '{{.ID}}|{{.Name}}|{{.Label "com.docker.compose.project"}}|{{.Label "com.docker.compose.network"}}')"
  gate1_expect_empty "Test networks found by Compose project label" "${result}"

  result="$(sudo docker network ls \
    --format '{{.ID}}\t{{.Name}}\t{{.Label "com.docker.compose.project"}}' |
    awk -F '\t' 'index($2, "photo-organizer-test") > 0')"
  gate1_expect_empty "Test-like networks found by fixed name/prefix" "${result}"

  result="$(sudo docker volume ls \
    --filter 'label=com.docker.compose.project=photo-organizer-test' \
    --format '{{.Name}}|{{.Label "com.docker.compose.project"}}|{{.Label "com.docker.compose.volume"}}')"
  gate1_expect_empty "Test volumes found by Compose project label" "${result}"

  result="$(sudo docker volume ls \
    --format '{{.Name}}\t{{.Label "com.docker.compose.project"}}' |
    awk -F '\t' 'index($1, "photo-organizer-test") > 0')"
  gate1_expect_empty "Test-like volumes found by fixed name/prefix" "${result}"

  result="$(ss -H -ltn '( sport = :13001 or sport = :18002 )')"
  gate1_expect_empty "listeners on Test ports 13001 or 18002" "${result}"

  if ((failed != 0)); then
    unset -f gate1_expect_empty
    trap - ERR
    printf 'STOP: Gate 1 failed. Do not initialize or deploy Test.\n' >&2
    return 1
  fi

  unset -f gate1_expect_empty
  ./scripts/operator/development/photo_organizer_dev_operator.sh recovery-status
  trap - ERR
  printf 'PASS: Gate 1 expected-absence and shared-host checks completed.\n'
}

gate1_preflight
```

Expected:

- the branch is exactly `feature/deployment-linux-runtime`, Git is clean,
  HEAD is a full committed SHA, an upstream is configured, and HEAD equals it;
- the full shared-host inventory is understood;
- Development and Portainer are healthy;
- both fixed runtime artifacts report PASS as absent;
- every Test label and Test-like name/prefix inventory reports PASS as empty;
- the Test port inventory reports PASS as empty.

Stop if the branch is wrong, the worktree is dirty, HEAD is not a full
committed SHA, no upstream is configured, or HEAD differs from upstream. Also
stop if either fixed runtime artifact exists; if any Test resource is found by
label or name; if a Test-like resource has absent, malformed, or unexpected
labels; or if any listener, unknown shared workload, Development failure, or
Portainer change appears. The function completes these Git checks and fails
closed before beginning Docker inventory. Capture the complete nonsecret
output. Do not inspect configuration contents. Pause for Product Owner
approval.

### Gate 2 — Test configuration initialization

Run only:

```bash
./scripts/operator/test/photo_organizer_test_operator.sh self-test
./scripts/operator/test/photo_organizer_test_operator.sh init-config
stat -c '%a %U %G %n' /home/chuck/.config/photo-organizer/test.env

sudo env \
  TEST_BACKEND_IMAGE=photo-organizer-test-backend:0000000000000000000000000000000000000000 \
  TEST_FRONTEND_IMAGE=photo-organizer-test-frontend:0000000000000000000000000000000000000000 \
  TEST_RELEASE_SHA=0000000000000000000000000000000000000000 \
  docker compose \
    --project-name photo-organizer-test \
    --env-file /home/chuck/.config/photo-organizer/test.env \
    --file docker/compose.test.yml \
    --file docker/compose.test.gpu.yml \
    config --quiet

git status --short
```

Expected: config mode `600`, owner `chuck`, no secret printed, no tracked change,
no Test Docker resource, and the client-side Compose render exits zero without
printing the protected configuration. The all-zero SHA is a non-deployable
render placeholder only. Do not display the config. Stop if the file already
exists, mode/owner differs, Compose rendering fails, or any Docker resource appears. Pause.

### Gate 3 — Candidate preparation

Run:

```bash
./scripts/operator/test/photo_organizer_test_operator.sh prepare-candidate
./scripts/operator/test/photo_organizer_test_operator.sh candidate-status
python3 -m json.tool /home/chuck/.local/state/photo-organizer/test/release.json
git status --short
```

Expected: full SHA equals clean pushed HEAD; immutable backend/frontend tags and
exact image IDs are recorded; labels report environment `test` and the same
SHA; manifest contains no secret; no Test container, network, or volume exists;
Development and Portainer remain healthy. Stop on a tag collision, label/ID
mismatch, build failure, repository change, secret evidence, or live resource.
Retain images and logs; do not remove or rebuild them. Pause.

### Gate 4 — First Test deployment

Run once:

```bash
./scripts/operator/test/photo_organizer_test_operator.sh deploy-candidate
./scripts/operator/test/photo_organizer_test_operator.sh status
./scripts/operator/test/photo_organizer_test_operator.sh health
./scripts/operator/test/photo_organizer_test_operator.sh release-status
```

Expected: exactly four healthy Test services, two isolated Test networks, three
isolated Test volumes, frontend/backend on their exact loopback ports,
PostgreSQL/Redis unpublished, runtime profile `test`, and release-status PASS.
Development and Portainer remain healthy and unchanged.

Stop on any bootstrap ambiguity or failure. Preserve containers, volumes,
networks, logs, release manifest, and console output. Do not rerun deployment,
remove resources, reset data, or repair during this gate. Pause.

### Gate 5 — Data isolation

Run this complete Bash block from the authoritative repository. It prints only
nonsecret release identity, container identity, mounts, networks, row/key
counts, and storage path metadata. It never prints container environment values
or the protected Test configuration.

Retain and review the complete Gate 4 `deploy-candidate` output as the
authority that the exact Test Redis instance began empty before backend and
frontend application startup. Gate 5 records the current post-start Redis key
count only as nonsecret informational evidence; application startup may
legitimately create keys, so a nonzero current count alone is neither a failure
nor evidence of copied Development state.

```bash
cd /home/chuck/projects/photo-organizer-dev
./scripts/operator/test/photo_organizer_test_operator.sh release-status

gate5_read_only_isolation() {
  set -Eeuo pipefail
  trap 'printf "FAIL: Gate 5 evidence could not be gathered safely. Stop without changing either environment.\n" >&2' ERR

  local release_file=/home/chuck/.local/state/photo-organizer/test/release.json
  local service identity overlap test_counts development_count redis_count storage_inventory
  local -a release_fields ids test_volumes development_volumes
  local -a test_network_refs development_network_refs test_network_ids development_network_ids
  local -A test_containers development_containers

  [[ -f "${release_file}" && ! -L "${release_file}" ]] || {
    printf 'FAIL: exact Test release manifest is unavailable: %s\n' "${release_file}" >&2
    return 1
  }

  mapfile -t release_fields < <(python3 - "${release_file}" <<'PY'
import json
from pathlib import Path
import sys
document = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
for key in ("candidate_sha", "backend_image_id", "frontend_image_id", "compose_project"):
    print(document[key])
PY
  )
  ((${#release_fields[@]} == 4)) &&
    [[ "${release_fields[3]}" == "photo-organizer-test" ]] || {
      printf 'FAIL: release manifest identity is incomplete or unexpected.\n' >&2
      return 1
    }
  printf 'Release SHA: %s\nBackend image ID: %s\nFrontend image ID: %s\n' \
    "${release_fields[0]}" "${release_fields[1]}" "${release_fields[2]}"

  gate5_resolve_one() {
    local project="$1"
    local service_name="$2"
    local -a matches
    mapfile -t matches < <(sudo docker ps --all --quiet \
      --filter "label=com.docker.compose.project=${project}" \
      --filter "label=com.docker.compose.service=${service_name}")
    ((${#matches[@]} == 1)) || {
      printf 'FAIL: expected one %s %s container; found %d.\n' \
        "${project}" "${service_name}" "${#matches[@]}" >&2
      return 1
    }
    printf '%s\n' "${matches[0]}"
  }

  for service in backend frontend postgres redis; do
    test_containers["${service}"]="$(gate5_resolve_one photo-organizer-test "${service}")"
    development_containers["${service}"]="$(gate5_resolve_one photo-organizer-dev "${service}")"
  done

  identity="$(sudo docker inspect --type container \
    --format '{{.Image}}|{{index .Config.Labels "com.photoorganizer.release"}}|{{index .Config.Labels "com.docker.compose.project"}}|{{index .Config.Labels "com.docker.compose.service"}}' \
    -- "${test_containers[backend]}")"
  [[ "${identity}" == "${release_fields[1]}|${release_fields[0]}|photo-organizer-test|backend" ]]
  identity="$(sudo docker inspect --type container \
    --format '{{.Image}}|{{index .Config.Labels "com.photoorganizer.release"}}|{{index .Config.Labels "com.docker.compose.project"}}|{{index .Config.Labels "com.docker.compose.service"}}' \
    -- "${test_containers[frontend]}")"
  [[ "${identity}" == "${release_fields[2]}|${release_fields[0]}|photo-organizer-test|frontend" ]]
  printf 'PASS: exact Test backend/frontend identity matches release.json\n'

  for service in backend frontend postgres redis; do
    printf '\nTest %s mounts|container=%s\n' "${service}" "${test_containers[${service}]}"
    sudo docker inspect --type container \
      --format '{{range .Mounts}}{{printf "type=%s|name=%s|destination=%s\n" .Type .Name .Destination}}{{end}}' \
      -- "${test_containers[${service}]}"
    printf 'Development %s mounts|container=%s\n' "${service}" "${development_containers[${service}]}"
    sudo docker inspect --type container \
      --format '{{range .Mounts}}{{printf "type=%s|name=%s|destination=%s\n" .Type .Name .Destination}}{{end}}' \
      -- "${development_containers[${service}]}"
  done

  mapfile -t test_volumes < <(
    for service in backend frontend postgres redis; do
      sudo docker inspect --type container \
        --format '{{range .Mounts}}{{if eq .Type "volume"}}{{println .Name}}{{end}}{{end}}' \
        -- "${test_containers[${service}]}"
    done | sed '/^$/d' | sort -u
  )
  mapfile -t development_volumes < <(
    for service in backend frontend postgres redis; do
      sudo docker inspect --type container \
        --format '{{range .Mounts}}{{if eq .Type "volume"}}{{println .Name}}{{end}}{{end}}' \
        -- "${development_containers[${service}]}"
    done | sed '/^$/d' | sort -u
  )
  [[ "${test_volumes[*]}" == "photo-organizer-test_application_storage photo-organizer-test_postgres_data photo-organizer-test_redis_data" ]]
  [[ "${development_volumes[*]}" == "photo-organizer-dev_application_storage photo-organizer-dev_postgres_data photo-organizer-dev_redis_data" ]]
  overlap="$(comm -12 <(printf '%s\n' "${test_volumes[@]}") <(printf '%s\n' "${development_volumes[@]}"))"
  [[ -z "${overlap}" ]]
  sudo docker volume inspect \
    --format '{{.Name}}|project={{index .Labels "com.docker.compose.project"}}|volume={{index .Labels "com.docker.compose.volume"}}|mountpoint={{.Mountpoint}}' \
    -- "${test_volumes[@]}" "${development_volumes[@]}"
  printf 'PASS: Test and Development volume identities are exact and disjoint\n'

  mapfile -t test_network_refs < <(sudo docker network ls --quiet \
    --filter 'label=com.docker.compose.project=photo-organizer-test')
  mapfile -t development_network_refs < <(sudo docker network ls --quiet \
    --filter 'label=com.docker.compose.project=photo-organizer-dev')
  ((${#test_network_refs[@]} == 2 && ${#development_network_refs[@]} == 2))
  mapfile -t test_network_ids < <(sudo docker network inspect \
    --format '{{.Id}}' -- "${test_network_refs[@]}" | sort)
  mapfile -t development_network_ids < <(sudo docker network inspect \
    --format '{{.Id}}' -- "${development_network_refs[@]}" | sort)
  overlap="$(comm -12 <(printf '%s\n' "${test_network_ids[@]}") <(printf '%s\n' "${development_network_ids[@]}"))"
  [[ -z "${overlap}" ]]
  printf '\nTest network identities:\n'
  sudo docker network inspect \
    --format '{{.Id}}|{{.Name}}|internal={{.Internal}}|project={{index .Labels "com.docker.compose.project"}}|network={{index .Labels "com.docker.compose.network"}}' \
    -- "${test_network_refs[@]}"
  printf 'Development network identities:\n'
  sudo docker network inspect \
    --format '{{.Id}}|{{.Name}}|internal={{.Internal}}|project={{index .Labels "com.docker.compose.project"}}|network={{index .Labels "com.docker.compose.network"}}' \
    -- "${development_network_refs[@]}"
  printf 'PASS: Test and Development network IDs are disjoint\n'

  test_counts="$(sudo docker exec "${test_containers[postgres]}" sh -ec '
    psql --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
      --set=ON_ERROR_STOP=1 --tuples-only --no-align --command "
        BEGIN READ ONLY;
        SELECT '\''test_asset_count|'\'' || count(*) FROM assets;
        SELECT '\''test_source_profile_count|'\'' || count(*) FROM ingestion_sources;
        SELECT '\''test_provenance_count|'\'' || count(*) FROM provenance;
        COMMIT;
      "
  ')"
  printf '\nTest database read-only counts:\n%s\n' "${test_counts}"
  grep -Fqx 'test_asset_count|0' <<<"${test_counts}"
  grep -Fqx 'test_source_profile_count|0' <<<"${test_counts}"
  grep -Fqx 'test_provenance_count|0' <<<"${test_counts}"

  redis_count="$(sudo docker exec "${test_containers[redis]}" redis-cli --raw DBSIZE)"
  if [[ ! "${redis_count}" =~ ^[0-9]+$ ]]; then
    printf 'FAIL: Test Redis DBSIZE did not return a nonnegative integer. STOP.\n' >&2
    return 1
  fi
  printf 'INFO: current Test Redis key count after application startup: %s\n' "${redis_count}"
  printf 'PASS: Redis key count captured without printing key names or values.\n'

  storage_inventory="$(sudo docker exec "${test_containers[backend]}" \
    find /app/storage -xdev -mindepth 1 -printf '%y|%P|%s bytes\n' | sort)"
  printf '\nTest application-storage inventory (no file contents):\n%s\n' "${storage_inventory}"

  development_count="$(sudo docker exec "${development_containers[postgres]}" sh -ec '
    psql --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
      --set=ON_ERROR_STOP=1 --tuples-only --no-align --command "
        BEGIN READ ONLY;
        SELECT '\''development_controlled_fixture_asset_count|'\'' || count(*) FROM assets;
        COMMIT;
      "
  ')"
  printf '\nDevelopment controlled fixture evidence:\n%s\n' "${development_count}"
  grep -Fqx 'development_controlled_fixture_asset_count|3' <<<"${development_count}"

  unset -f gate5_resolve_one
  trap - ERR
  printf '\nPASS: Gate 5 evidence completed without printing configuration or container environment values.\n'
}

gate5_read_only_isolation
```

Expected: `release-status` passes; exactly one labeled container is resolved for
every Test and Development service; Test candidate identity matches
`release.json`; mounts, volumes, and network IDs are exact and disjoint; Test
database counts are zero; Test storage contains only the expected new Test
structure; and Development still reports the three controlled fixture Assets.
Retained Gate 4 output proves that the isolated Test Redis began empty before
application startup. Gate 5 identifies the exact Test Redis container and
volume, proves that no Development Redis volume is attached, and prints the
current post-start `DBSIZE` only as informational evidence. Redis key names and
values are never printed.

Do not ingest a fixture merely to prove isolation. Stop if any container
identity is absent or ambiguous, any mutable identity is shared, any Test
database row is present, storage suggests copied Development content, the
Development fixture count changes, retained Gate 4 output is missing or does
not prove that the exact Test Redis began empty before application startup, the
exact Test Redis container or volume cannot be verified, a Development Redis
volume is attached, `DBSIZE` cannot be gathered as a nonnegative aggregate
count, or evidence cannot be gathered without printing secrets or
password-bearing environment values. A nonzero post-start Redis count alone is
not a stop condition and must not be treated as proof of copied Development
state. Preserve evidence. Pause.

### Gate 6 — Browser and API access

Create the explicit Windows tunnel from Section 8. Verify:

- `http://localhost:13001` loads Test;
- `http://localhost:18002/health` reports runtime profile `test`;
- Test does not display the Development fixture Assets;
- same-origin API and managed-media requests do not reveal a private backend
  identity;
- `candidate-status` and `release-status` match the recorded SHA and image IDs;
- the Development tunnel/browser state is unchanged.

Press Ctrl+C to stop the temporary Test tunnel. Stop on data crossover, wrong
runtime profile, wrong image identity, non-loopback access, or private identity
leak. Capture screenshots and nonsecret status. Pause.

### Gate 7 — Test-only stop/start

Record Test container IDs, creation timestamps, image IDs, and release status,
then run:

```bash
./scripts/operator/test/photo_organizer_test_operator.sh stop
./scripts/operator/test/photo_organizer_test_operator.sh status
./scripts/operator/test/photo_organizer_test_operator.sh start
./scripts/operator/test/photo_organizer_test_operator.sh health
./scripts/operator/test/photo_organizer_test_operator.sh release-status
```

Expected: only Test containers stop and start; container IDs and creation ages
remain unchanged; release identity remains unchanged; Test volumes remain
attached; Development and Portainer are uninterrupted. Stop and preserve
evidence on any recreation, identity change, timeout, data issue, or unrelated
workload impact. Pause for final milestone review.

## 10. When to Stop and Escalate

Stop before further action if:

- either expected-absent Gate 1 path already exists;
- a Test-like container, network, or volume is found by name but not by the
  expected Test Compose labels;
- a Test resource exists before first deployment or has unclear ownership;
- either Test port is occupied;
- the branch is not `feature/deployment-linux-runtime`, Git is dirty, HEAD is
  not a full committed SHA, no upstream is configured, or HEAD differs from
  upstream;
- a candidate tag or image ID conflicts with its labels or manifest;
- config or manifest permissions differ from `0600`;
- retained Gate 4 evidence does not demonstrate that PostgreSQL, Redis, and
  application storage were new and empty before application startup;
- a Development volume, network, secret, database, Redis instance, or path is
  attached to Test;
- PostgreSQL or Redis is published;
- frontend or backend is not loopback-only;
- GPU validation fails;
- release-status returns FAILURE;
- Gate 5 cannot resolve exactly one container for every required Test and
  Development service;
- required isolation evidence cannot be gathered safely without exposing a
  secret, protected configuration, or password-bearing environment value;
- any action would require candidate replacement, reset, teardown, cleanup,
  Development recreation, Portainer change, Docker daemon change, NAS change,
  firewall change, or Production implementation.

Collect only nonsecret status, labels, IDs, timestamps, health, and bounded
logs. Never print the protected Test configuration or password-bearing
container environment.

## 11. Deferred Work

This milestone does not implement candidate replacement, rollback, registry
push, CI/CD, automatic deployment, Production, Production cutover,
backup/restore, NAS-backed Test storage, Test fixture ingestion, Windows Test
GUI controls, public access, TLS, Docker restart, or host reboot.

After all seven gates pass, create the single Milestone 009 closeout. The
recommended next deployment milestone is the controlled candidate promotion
and rollback workflow; it must retain exact image identity and separate mutable
state.
