#!/usr/bin/env bash
set -Eeuo pipefail

readonly EXPECTED_REPOSITORY="/home/chuck/projects/photo-organizer-dev"
readonly EXPECTED_USER="chuck"
readonly COMPOSE_PROJECT="photo-organizer-test"
readonly CONFIG_FILE="/home/chuck/.config/photo-organizer/test.env"
readonly RELEASE_FILE="/home/chuck/.local/state/photo-organizer/test/release.json"
readonly BACKEND_HEALTH_URL="http://127.0.0.1:18002/health"
readonly FRONTEND_HEALTH_URL="http://127.0.0.1:13001/"
readonly BACKEND_IMAGE_REPOSITORY="photo-organizer-test-backend"
readonly FRONTEND_IMAGE_REPOSITORY="photo-organizer-test-frontend"
readonly POSTGRES_IMAGE_REFERENCE="postgres:16.9-bookworm"
readonly REDIS_IMAGE_REFERENCE="redis:7.4.5-bookworm"
readonly TEST_BIND_ADDRESS="127.0.0.1"
readonly BACKEND_HOST_PORT="18002"
readonly FRONTEND_HOST_PORT="13001"
readonly TEST_DATABASE="photo_organizer_test"
readonly TEST_DATABASE_USER="photo_organizer_test"
readonly TEST_NETWORK_INTERNAL="photo-organizer-test_application_internal"
readonly TEST_NETWORK_BROWSER="photo-organizer-test_browser_edge"
readonly TEST_VOLUME_APPLICATION="photo-organizer-test_application_storage"
readonly TEST_VOLUME_POSTGRES="photo-organizer-test_postgres_data"
readonly TEST_VOLUME_REDIS="photo-organizer-test_redis_data"
readonly DEVELOPMENT_PROJECT="photo-organizer-dev"
readonly PORTAINER_PROJECT="portainer"

readonly -a EXPECTED_SERVICES=(backend frontend postgres redis)
readonly -a EXPECTED_VOLUMES=(application_storage postgres_data redis_data)
readonly -a EXPECTED_NETWORKS=(application_internal browser_edge)
readonly -a ALLOWED_ACTIONS=(
  candidate-status
  deploy-candidate
  follow-logs
  health
  init-config
  logs
  prepare-candidate
  release-status
  self-test
  start
  status
  stop
)

script_directory="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repository_root="$(cd -- "${script_directory}/../../.." && pwd)"
readonly script_directory repository_root
readonly compose_file="${repository_root}/docker/compose.test.yml"
readonly gpu_compose_file="${repository_root}/docker/compose.test.gpu.yml"
readonly config_template="${repository_root}/docker/.env.test.example"
readonly expected_script="${repository_root}/scripts/operator/test/photo_organizer_test_operator.sh"

DOCKER_BIN="$(command -v docker 2>/dev/null || true)"
readonly DOCKER_BIN

candidate_sha=""
backend_image_reference=""
backend_image_id=""
frontend_image_reference=""
frontend_image_id=""
postgres_image_reference=""
postgres_image_id=""
redis_image_reference=""
redis_image_id=""
prepared_at=""
deployed_at=""

usage() {
  cat >&2 <<'USAGE'
Usage: photo_organizer_test_operator.sh {self-test|init-config|prepare-candidate|candidate-status|deploy-candidate|start|stop|status|health|release-status|logs|follow-logs}
USAGE
}

fail() {
  printf 'FAIL: %s\n' "$*" >&2
  exit 1
}

pass() {
  printf 'PASS: %s\n' "$*"
}

warning() {
  printf 'WARNING: %s\n' "$*"
}

require_command() {
  command -v -- "$1" >/dev/null 2>&1 || fail "Required command is unavailable: $1"
}

verify_execution_identity() {
  [[ "${EUID}" -ne 0 ]] || fail "Run this script as ${EXPECTED_USER}, not as root."
  [[ "$(id -un)" == "${EXPECTED_USER}" ]] ||
    fail "Expected user ${EXPECTED_USER}; current user is $(id -un)."
}

verify_static_contract() {
  [[ "${repository_root}" == "${EXPECTED_REPOSITORY}" ]] ||
    fail "Expected repository ${EXPECTED_REPOSITORY}; resolved ${repository_root}."
  [[ "${script_directory}/photo_organizer_test_operator.sh" == "${expected_script}" ]] ||
    fail "The operator is not running from its approved tracked location."
  [[ -f "${compose_file}" ]] || fail "Test Compose file is missing."
  [[ -f "${gpu_compose_file}" ]] || fail "Test GPU overlay is missing."
  [[ -f "${config_template}" ]] || fail "Tracked Test configuration template is missing."
  [[ "${DOCKER_BIN}" == /* ]] || fail "The Docker executable could not be resolved."
}

verify_required_tools() {
  local tool
  for tool in bash chmod curl date docker env git grep id install mktemp mv openssl python3 rm sleep sort ss stat sudo timeout wc; do
    require_command "${tool}"
  done
}

is_full_sha() {
  [[ "$1" =~ ^[0-9a-f]{40}$ ]]
}

arrays_match() {
  local -n expected_ref="$1"
  local -n actual_ref="$2"
  local index
  ((${#expected_ref[@]} == ${#actual_ref[@]})) || return 1
  for index in "${!expected_ref[@]}"; do
    [[ "${expected_ref[index]}" == "${actual_ref[index]}" ]] || return 1
  done
}

network_sets_match() {
  local expected_lines="$1"
  local actual_lines="$2"
  local network
  local -a expected_set=() actual_set=()

  while IFS= read -r network; do
    [[ -n "${network}" ]] || continue
    expected_set+=("${network}")
  done <<<"${expected_lines}"
  while IFS= read -r network; do
    [[ -n "${network}" ]] || continue
    actual_set+=("${network}")
  done <<<"${actual_lines}"

  if ((${#expected_set[@]} > 0)); then
    mapfile -t expected_set < <(printf '%s\n' "${expected_set[@]}" | LC_ALL=C sort)
  fi
  if ((${#actual_set[@]} > 0)); then
    mapfile -t actual_set < <(printf '%s\n' "${actual_set[@]}" | LC_ALL=C sort)
  fi
  arrays_match expected_set actual_set
}

candidate_inputs_are_eligible() {
  local clean_state="$1"
  local head_sha="$2"
  local upstream_sha="$3"
  [[ "${clean_state}" == "clean" ]] && is_full_sha "${head_sha}" && [[ "${head_sha}" == "${upstream_sha}" ]]
}

resource_inventory_is_empty() {
  [[ -z "$1" && -z "$2" && -z "$3" ]]
}

docker_cmd() {
  sudo -- "${DOCKER_BIN}" "$@"
}

compose_cmd() {
  [[ -n "${candidate_sha}" ]] || fail "Release manifest has not been loaded."
  sudo -- env \
    TEST_BACKEND_IMAGE="${backend_image_reference}" \
    TEST_FRONTEND_IMAGE="${frontend_image_reference}" \
    TEST_RELEASE_SHA="${candidate_sha}" \
    "${DOCKER_BIN}" compose \
      --project-name "${COMPOSE_PROJECT}" \
      --env-file "${CONFIG_FILE}" \
      --file "${compose_file}" \
      --file "${gpu_compose_file}" \
      "$@"
}

verify_config_file() {
  [[ -f "${CONFIG_FILE}" && ! -L "${CONFIG_FILE}" ]] ||
    fail "Protected Test configuration is missing or is not a regular file: ${CONFIG_FILE}"
  [[ "$(stat -c '%U' -- "${CONFIG_FILE}")" == "${EXPECTED_USER}" ]] ||
    fail "Protected Test configuration is not owned by ${EXPECTED_USER}."
  [[ "$(stat -c '%a' -- "${CONFIG_FILE}")" == "600" ]] ||
    fail "Protected Test configuration must have mode 0600."

  python3 - "${CONFIG_FILE}" <<'PY' || fail "Protected Test configuration failed fixed-value validation."
from pathlib import Path
import sys

path = Path(sys.argv[1])
values = {}
for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
    line = raw.strip()
    if not line or line.startswith("#"):
        continue
    if "=" not in line:
        raise SystemExit(f"invalid line {number}")
    key, value = line.split("=", 1)
    if key in values:
        raise SystemExit(f"duplicate key {key}")
    values[key] = value

expected = {
    "COMPOSE_PROJECT_NAME": "photo-organizer-test",
    "POSTGRES_DB": "photo_organizer_test",
    "POSTGRES_USER": "photo_organizer_test",
    "TEST_BIND_ADDRESS": "127.0.0.1",
    "BACKEND_HOST_PORT": "18002",
    "FRONTEND_HOST_PORT": "13001",
    "FRONTEND_ALLOWED_ORIGINS": "http://127.0.0.1:13001,http://localhost:13001",
}
allowed = set(expected) | {"POSTGRES_PASSWORD"}
if set(values) != allowed:
    raise SystemExit("unexpected or missing configuration keys")
for key, expected_value in expected.items():
    if values.get(key) != expected_value:
        raise SystemExit(f"unexpected fixed value for {key}")
password = values.get("POSTGRES_PASSWORD", "")
if len(password) < 32 or any(ch.isspace() for ch in password):
    raise SystemExit("PostgreSQL password is missing or too short")
PY

  git -C "${repository_root}" check-ignore --quiet -- "${CONFIG_FILE}" 2>/dev/null || true
}
prepare_release_directory() {
  local release_directory
  release_directory="$(dirname -- "${RELEASE_FILE}")"
  if [[ -e "${release_directory}" && (! -d "${release_directory}" || -L "${release_directory}") ]]; then
    fail "Test release-state directory is not a safe ordinary directory."
  fi
  install -d -m 700 -- "${release_directory}"
  [[ "$(stat -c '%U' -- "${release_directory}")" == "${EXPECTED_USER}" ]] ||
    fail "Test release-state directory is not owned by ${EXPECTED_USER}."
  [[ "$(stat -c '%a' -- "${release_directory}")" == "700" ]] ||
    fail "Test release-state directory must have mode 0700."
}

write_manifest_to_path() {
  local destination="$1"
  local deployment_timestamp="${2:-}"
  python3 - "${destination}" "${candidate_sha}" \
    "${backend_image_reference}" "${backend_image_id}" \
    "${frontend_image_reference}" "${frontend_image_id}" \
    "${postgres_image_reference}" "${postgres_image_id}" \
    "${redis_image_reference}" "${redis_image_id}" \
    "${prepared_at}" "${deployment_timestamp}" <<'PY'
import json
import os
from pathlib import Path
import sys
import tempfile

(
    destination,
    candidate_sha,
    backend_ref,
    backend_id,
    frontend_ref,
    frontend_id,
    postgres_ref,
    postgres_id,
    redis_ref,
    redis_id,
    prepared_at,
    deployed_at,
) = sys.argv[1:]

document = {
    "schema_version": 1,
    "environment": "test",
    "compose_project": "photo-organizer-test",
    "candidate_sha": candidate_sha,
    "backend_image_reference": backend_ref,
    "backend_image_id": backend_id,
    "frontend_image_reference": frontend_ref,
    "frontend_image_id": frontend_id,
    "postgres_image_reference": postgres_ref,
    "postgres_image_id": postgres_id,
    "redis_image_reference": redis_ref,
    "redis_image_id": redis_id,
    "frontend_host": "127.0.0.1",
    "frontend_host_port": 13001,
    "backend_host": "127.0.0.1",
    "backend_host_port": 18002,
    "prepared_at": prepared_at,
    "deployed_at": deployed_at or None,
}

target = Path(destination)
target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
fd, temporary = tempfile.mkstemp(prefix=".release.", suffix=".json", dir=target.parent)
try:
    os.fchmod(fd, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        json.dump(document, handle, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, target)
except BaseException:
    try:
        os.unlink(temporary)
    except FileNotFoundError:
        pass
    raise
PY
}

load_manifest() {
  [[ -f "${RELEASE_FILE}" && ! -L "${RELEASE_FILE}" ]] ||
    fail "Prepared Test release manifest is missing: ${RELEASE_FILE}"
  [[ "$(stat -c '%U' -- "${RELEASE_FILE}")" == "${EXPECTED_USER}" ]] ||
    fail "Test release manifest is not owned by ${EXPECTED_USER}."
  [[ "$(stat -c '%a' -- "${RELEASE_FILE}")" == "600" ]] ||
    fail "Test release manifest must have mode 0600."

  local -a values=()
  mapfile -d '' -t values < <(python3 - "${RELEASE_FILE}" <<'PY'
import json
from pathlib import Path
import re
import sys

document = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
required = {
    "schema_version", "environment", "compose_project", "candidate_sha",
    "backend_image_reference", "backend_image_id", "frontend_image_reference",
    "frontend_image_id", "postgres_image_reference", "postgres_image_id",
    "redis_image_reference", "redis_image_id", "frontend_host",
    "frontend_host_port", "backend_host", "backend_host_port", "prepared_at",
    "deployed_at",
}
if set(document) != required:
    raise SystemExit("manifest key set is invalid")
sha = document["candidate_sha"]
if not isinstance(sha, str) or not re.fullmatch(r"[0-9a-f]{40}", sha):
    raise SystemExit("candidate SHA is invalid")
expected = {
    "schema_version": 1,
    "environment": "test",
    "compose_project": "photo-organizer-test",
    "backend_image_reference": f"photo-organizer-test-backend:{sha}",
    "frontend_image_reference": f"photo-organizer-test-frontend:{sha}",
    "postgres_image_reference": "postgres:16.9-bookworm",
    "redis_image_reference": "redis:7.4.5-bookworm",
    "frontend_host": "127.0.0.1",
    "frontend_host_port": 13001,
    "backend_host": "127.0.0.1",
    "backend_host_port": 18002,
}
for key, value in expected.items():
    if document.get(key) != value:
        raise SystemExit(f"manifest field {key} is invalid")
for key in ("backend_image_id", "frontend_image_id", "postgres_image_id", "redis_image_id"):
    if not isinstance(document[key], str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", document[key]):
        raise SystemExit(f"manifest field {key} is invalid")
if not isinstance(document["prepared_at"], str) or not document["prepared_at"]:
    raise SystemExit("prepared timestamp is invalid")
if document["deployed_at"] is not None and not isinstance(document["deployed_at"], str):
    raise SystemExit("deployment timestamp is invalid")
keys = (
    "candidate_sha", "backend_image_reference", "backend_image_id",
    "frontend_image_reference", "frontend_image_id", "postgres_image_reference",
    "postgres_image_id", "redis_image_reference", "redis_image_id", "prepared_at",
    "deployed_at",
)
for key in keys:
    value = document[key]
    sys.stdout.write(("" if value is None else str(value)) + "\0")
PY
  ) || fail "Test release manifest is invalid."

  ((${#values[@]} == 11)) || fail "Test release manifest could not be loaded safely."
  candidate_sha="${values[0]}"
  backend_image_reference="${values[1]}"
  backend_image_id="${values[2]}"
  frontend_image_reference="${values[3]}"
  frontend_image_id="${values[4]}"
  postgres_image_reference="${values[5]}"
  postgres_image_id="${values[6]}"
  redis_image_reference="${values[7]}"
  redis_image_id="${values[8]}"
  prepared_at="${values[9]}"
  deployed_at="${values[10]}"
}

verify_repository_candidate() {
  local head_sha upstream_ref upstream_sha dirty_state="clean"
  [[ -d "${repository_root}/.git" ]] || fail "Authoritative Git repository is unavailable."
  head_sha="$(git -C "${repository_root}" rev-parse HEAD)"
  upstream_ref="$(git -C "${repository_root}" rev-parse --abbrev-ref --symbolic-full-name '@{upstream}')" ||
    fail "The current branch has no configured upstream."
  upstream_sha="$(git -C "${repository_root}" rev-parse "${upstream_ref}")"
  if [[ -n "$(git -C "${repository_root}" status --porcelain=v1 --untracked-files=all)" ]]; then
    dirty_state="dirty"
  fi
  candidate_inputs_are_eligible "${dirty_state}" "${head_sha}" "${upstream_sha}" ||
    fail "Candidate preparation requires a clean committed workspace whose HEAD exactly matches its upstream."
  printf '%s\n' "${head_sha}"
}

inspect_image_record() {
  local reference="$1"
  local expected_sha="$2"
  local expected_id="${3:-}"
  local metadata actual_id revision environment release
  metadata="$(docker_cmd image inspect --format '{{.Id}}|{{index .Config.Labels "org.opencontainers.image.revision"}}|{{index .Config.Labels "com.photoorganizer.environment"}}|{{index .Config.Labels "com.photoorganizer.release"}}' -- "${reference}")" ||
    fail "Required candidate image is unavailable: ${reference}"
  IFS='|' read -r actual_id revision environment release <<<"${metadata}"
  [[ "${actual_id}" =~ ^sha256:[0-9a-f]{64}$ ]] || fail "Image ID is invalid for ${reference}."
  [[ "${revision}" == "${expected_sha}" && "${environment}" == "test" && "${release}" == "${expected_sha}" ]] ||
    fail "Image labels do not match the exact Test candidate for ${reference}."
  [[ -z "${expected_id}" || "${actual_id}" == "${expected_id}" ]] ||
    fail "Image ID for ${reference} differs from the prepared release manifest."
  printf '%s\n' "${actual_id}"
}

inspect_base_image_id() {
  local reference="$1"
  local expected_id="${2:-}"
  local actual_id
  actual_id="$(docker_cmd image inspect --format '{{.Id}}' -- "${reference}")" ||
    fail "Required local base service image is unavailable: ${reference}"
  [[ "${actual_id}" =~ ^sha256:[0-9a-f]{64}$ ]] || fail "Image ID is invalid for ${reference}."
  [[ -z "${expected_id}" || "${actual_id}" == "${expected_id}" ]] ||
    fail "Local image ID for ${reference} differs from the prepared release manifest."
  printf '%s\n' "${actual_id}"
}

test_resource_inventory() {
  local kind="$1"
  case "${kind}" in
    containers)
      docker_cmd ps --all --filter "label=com.docker.compose.project=${COMPOSE_PROJECT}" --format '{{.ID}}|{{.Names}}|{{.Label "com.docker.compose.service"}}'
      ;;
    networks)
      docker_cmd network ls --filter "label=com.docker.compose.project=${COMPOSE_PROJECT}" --format '{{.ID}}|{{.Name}}|{{.Labels}}'
      ;;
    volumes)
      docker_cmd volume ls --filter "label=com.docker.compose.project=${COMPOSE_PROJECT}" --format '{{.Name}}|{{.Labels}}'
      ;;
    *) fail "Internal inventory kind is not allowlisted: ${kind}" ;;
  esac
}

assert_no_test_resources() {
  local containers networks volumes named
  containers="$(test_resource_inventory containers)"
  networks="$(test_resource_inventory networks)"
  volumes="$(test_resource_inventory volumes)"
  named="$({
    docker_cmd ps --all --format '{{.Names}}'
    docker_cmd network ls --format '{{.Name}}'
    docker_cmd volume ls --format '{{.Name}}'
  } | grep -E '^photo-organizer-test([_-]|$)' || true)"
  if ! resource_inventory_is_empty "${containers}" "${networks}" "${volumes}" || [[ -n "${named}" ]]; then
    printf 'FAIL: Existing or ambiguous %s resources were found. Preserve and review them before deployment.\n' "${COMPOSE_PROJECT}" >&2
    [[ -z "${containers}" ]] || printf 'Containers:\n%s\n' "${containers}" >&2
    [[ -z "${networks}" ]] || printf 'Networks:\n%s\n' "${networks}" >&2
    [[ -z "${volumes}" ]] || printf 'Volumes:\n%s\n' "${volumes}" >&2
    [[ -z "${named}" ]] || printf 'Project-like names requiring review:\n%s\n' "${named}" >&2
    return 1
  fi
  pass "no existing or ambiguous ${COMPOSE_PROJECT} container, network, or volume was found"
}

verify_ports_free() {
  local port
  for port in "${FRONTEND_HOST_PORT}" "${BACKEND_HOST_PORT}"; do
    if [[ -n "$(ss -H -ltn "sport = :${port}")" ]]; then
      fail "Required loopback port ${port} is already in use. Do not terminate the existing listener."
    fi
    pass "host port ${port} is available"
  done
}

service_container_id() {
  local service="$1"
  local output
  local -a ids=()
  output="$(compose_cmd ps --all --quiet "${service}")" || fail "Could not inspect Test service ${service}."
  [[ -z "${output}" ]] || mapfile -t ids <<<"${output}"
  ((${#ids[@]} == 1)) || fail "Expected exactly one Test ${service} container; found ${#ids[@]}."
  printf '%s\n' "${ids[0]}"
}

wait_for_health() {
  local service="$1"
  local maximum_seconds="$2"
  local container_id state health started_at="${SECONDS}"
  container_id="$(service_container_id "${service}")"
  while ((SECONDS - started_at < maximum_seconds)); do
    IFS='|' read -r state health < <(docker_cmd inspect --type container --format '{{.State.Status}}|{{if .State.Health}}{{.State.Health.Status}}{{else}}not-configured{{end}}' -- "${container_id}")
    if [[ "${state}" == "running" && ("${health}" == "healthy" || "${health}" == "not-configured") ]]; then
      pass "Test service ${service} is running with health ${health}"
      return 0
    fi
    if [[ "${state}" == "exited" || "${state}" == "dead" ]]; then
      fail "Test service ${service} entered container state ${state}; preserve logs and stop."
    fi
    sleep 2
  done
  fail "Timed out waiting for Test service ${service}; preserve status and logs."
}

verify_created_resource_allowlists() {
  local service volume network output metadata project_label resource_label
  local -a actual_services=() actual_volumes=() actual_networks=()

  mapfile -t actual_services < <(docker_cmd ps --all \
    --filter "label=com.docker.compose.project=${COMPOSE_PROJECT}" \
    --format '{{.Label "com.docker.compose.service"}}' | sort)
  arrays_match EXPECTED_SERVICES actual_services || fail "Test container service set is not exactly backend, frontend, postgres, redis."

  for volume in "${EXPECTED_VOLUMES[@]}"; do
    output="$(docker_cmd volume inspect --format '{{index .Labels "com.docker.compose.project"}}|{{index .Labels "com.docker.compose.volume"}}' -- "${COMPOSE_PROJECT}_${volume}")" ||
      fail "Expected Test volume ${COMPOSE_PROJECT}_${volume} is missing."
    IFS='|' read -r project_label resource_label <<<"${output}"
    [[ "${project_label}" == "${COMPOSE_PROJECT}" && "${resource_label}" == "${volume}" ]] ||
      fail "Test volume ${COMPOSE_PROJECT}_${volume} has unexpected ownership labels."
    actual_volumes+=("${volume}")
  done
  mapfile -t actual_volumes < <(printf '%s\n' "${actual_volumes[@]}" | sort)
  arrays_match EXPECTED_VOLUMES actual_volumes || fail "Test volume set is unexpected."

  for network in "${EXPECTED_NETWORKS[@]}"; do
    output="$(docker_cmd network inspect --format '{{index .Labels "com.docker.compose.project"}}|{{index .Labels "com.docker.compose.network"}}' -- "${COMPOSE_PROJECT}_${network}")" ||
      fail "Expected Test network ${COMPOSE_PROJECT}_${network} is missing."
    IFS='|' read -r project_label resource_label <<<"${output}"
    [[ "${project_label}" == "${COMPOSE_PROJECT}" && "${resource_label}" == "${network}" ]] ||
      fail "Test network ${COMPOSE_PROJECT}_${network} has unexpected ownership labels."
    actual_networks+=("${network}")
  done
  mapfile -t actual_networks < <(printf '%s\n' "${actual_networks[@]}" | sort)
  arrays_match EXPECTED_NETWORKS actual_networks || fail "Test network set is unexpected."

  pass "created Test services, volumes, and networks match the exact allowlists"
}

verify_empty_dependencies() {
  local table_count redis_keys
  table_count="$(compose_cmd exec -T postgres psql --username "${TEST_DATABASE_USER}" --dbname "${TEST_DATABASE}" --tuples-only --no-align --command "SELECT count(*) FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE';")"
  [[ "${table_count}" == "0" ]] || fail "Test PostgreSQL is not empty before first initialization."
  redis_keys="$(compose_cmd exec -T redis redis-cli DBSIZE)"
  [[ "${redis_keys}" == "0" ]] || fail "Test Redis contains preexisting keys."
  pass "Test PostgreSQL has no application tables and Test Redis has no keys"
}

bootstrap_application_storage() {
  compose_cmd run --rm --no-deps --pull never --user root --entrypoint /bin/sh backend -ec '
    set -eu
    if find /app/storage -mindepth 1 -print -quit | grep -q .; then
      echo "Test application storage is not empty before bootstrap." >&2
      exit 41
    fi
    install -d -o photo-organizer -g photo-organizer \
      /app/storage/drop_zone \
      /app/storage/vault \
      /app/storage/quarantine \
      /app/storage/ingest_failures \
      /app/storage/previews \
      /app/storage/thumbnails \
      /app/storage/review \
      /app/storage/staging \
      /app/storage/logs \
      /app/storage/exports \
      /app/storage/exports/icloud \
      /app/storage/models
    chown photo-organizer:photo-organizer /app/storage
  '
  pass "empty Test application storage received only the fixed directory structure and ownership"
}

initialize_test_database() {
  compose_cmd run --rm --no-deps --pull never --entrypoint python backend scripts/init_db.py
  local table_count asset_count source_count provenance_count
  table_count="$(compose_cmd exec -T postgres psql --username "${TEST_DATABASE_USER}" --dbname "${TEST_DATABASE}" --tuples-only --no-align --command "SELECT count(*) FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE';")"
  [[ "${table_count}" =~ ^[1-9][0-9]*$ ]] || fail "Test schema initialization did not create application tables."
  asset_count="$(compose_cmd exec -T postgres psql --username "${TEST_DATABASE_USER}" --dbname "${TEST_DATABASE}" --tuples-only --no-align --command 'SELECT count(*) FROM assets;')"
  source_count="$(compose_cmd exec -T postgres psql --username "${TEST_DATABASE_USER}" --dbname "${TEST_DATABASE}" --tuples-only --no-align --command 'SELECT count(*) FROM ingestion_sources;')"
  provenance_count="$(compose_cmd exec -T postgres psql --username "${TEST_DATABASE_USER}" --dbname "${TEST_DATABASE}" --tuples-only --no-align --command 'SELECT count(*) FROM provenance;')"
  [[ "${asset_count}" == "0" && "${source_count}" == "0" && "${provenance_count}" == "0" ]] ||
    fail "Initialized Test database contains copied Asset, Source Profile, or provenance rows."
  pass "Test schema initialized without reset and contains no Asset, Source Profile, or provenance rows"
}

init_config() {
  verify_execution_identity
  verify_required_tools
  verify_static_contract
  [[ ! -e "${CONFIG_FILE}" && ! -L "${CONFIG_FILE}" ]] ||
    fail "Test configuration already exists and will not be overwritten: ${CONFIG_FILE}"

  local config_directory temporary password
  config_directory="$(dirname -- "${CONFIG_FILE}")"
  install -d -m 700 -- "${config_directory}"
  [[ ! -L "${config_directory}" && "$(stat -c '%U' -- "${config_directory}")" == "${EXPECTED_USER}" ]] ||
    fail "Test configuration directory ownership is unsafe."
  password="$(openssl rand -hex 32)" || fail "Secure Test credential generation failed."
  umask 077
  temporary="$(mktemp "${config_directory}/.test.env.XXXXXX")"
  trap 'rm -f -- "${temporary:-}"' RETURN
  {
    printf 'COMPOSE_PROJECT_NAME=%s\n' "${COMPOSE_PROJECT}"
    printf 'POSTGRES_DB=%s\n' "${TEST_DATABASE}"
    printf 'POSTGRES_USER=%s\n' "${TEST_DATABASE_USER}"
    printf 'POSTGRES_PASSWORD=%s\n' "${password}"
    printf 'TEST_BIND_ADDRESS=%s\n' "${TEST_BIND_ADDRESS}"
    printf 'BACKEND_HOST_PORT=%s\n' "${BACKEND_HOST_PORT}"
    printf 'FRONTEND_HOST_PORT=%s\n' "${FRONTEND_HOST_PORT}"
    printf 'FRONTEND_ALLOWED_ORIGINS=http://127.0.0.1:13001,http://localhost:13001\n'
  } >"${temporary}"
  chmod 600 -- "${temporary}"
  mv -- "${temporary}" "${CONFIG_FILE}"
  trap - RETURN
  password=""
  verify_config_file
  pass "created separate Test-only configuration at ${CONFIG_FILE} with mode 0600"
  pass "generated credentials were not printed; no Docker resource was created"
}

prepare_candidate() {
  verify_execution_identity
  verify_required_tools
  verify_static_contract
  verify_config_file
  [[ ! -e "${RELEASE_FILE}" && ! -L "${RELEASE_FILE}" ]] ||
    fail "A prepared release manifest already exists. Candidate replacement is not implemented."

  candidate_sha="$(verify_repository_candidate)"
  backend_image_reference="${BACKEND_IMAGE_REPOSITORY}:${candidate_sha}"
  frontend_image_reference="${FRONTEND_IMAGE_REPOSITORY}:${candidate_sha}"
  postgres_image_reference="${POSTGRES_IMAGE_REFERENCE}"
  redis_image_reference="${REDIS_IMAGE_REFERENCE}"

  if docker_cmd image inspect -- "${backend_image_reference}" >/dev/null 2>&1; then
    backend_image_id="$(inspect_image_record "${backend_image_reference}" "${candidate_sha}")"
    pass "reused the existing immutable backend tag after exact label verification"
  else
    docker_cmd build --pull=false --target development-gpu \
      --label "org.opencontainers.image.revision=${candidate_sha}" \
      --label "com.photoorganizer.environment=test" \
      --label "com.photoorganizer.release=${candidate_sha}" \
      --tag "${backend_image_reference}" \
      -- "${repository_root}/backend"
    backend_image_id="$(inspect_image_record "${backend_image_reference}" "${candidate_sha}")"
  fi

  if docker_cmd image inspect -- "${frontend_image_reference}" >/dev/null 2>&1; then
    frontend_image_id="$(inspect_image_record "${frontend_image_reference}" "${candidate_sha}")"
    pass "reused the existing immutable frontend tag after exact label verification"
  else
    docker_cmd build --pull=false --target runtime \
      --label "org.opencontainers.image.revision=${candidate_sha}" \
      --label "com.photoorganizer.environment=test" \
      --label "com.photoorganizer.release=${candidate_sha}" \
      --tag "${frontend_image_reference}" \
      -- "${repository_root}/frontend"
    frontend_image_id="$(inspect_image_record "${frontend_image_reference}" "${candidate_sha}")"
  fi

  postgres_image_id="$(inspect_base_image_id "${postgres_image_reference}")"
  redis_image_id="$(inspect_base_image_id "${redis_image_reference}")"
  [[ "$(verify_repository_candidate)" == "${candidate_sha}" ]] ||
    fail "Repository state changed during candidate preparation; no manifest was written."
  prepared_at="$(date -u +'%Y-%m-%dT%H:%M:%SZ')"
  deployed_at=""
  prepare_release_directory
  write_manifest_to_path "${RELEASE_FILE}"
  load_manifest
  pass "prepared exact candidate ${candidate_sha}"
  printf 'Backend image: %s\nBackend image ID: %s\n' "${backend_image_reference}" "${backend_image_id}"
  printf 'Frontend image: %s\nFrontend image ID: %s\n' "${frontend_image_reference}" "${frontend_image_id}"
  pass "atomic nonsecret release manifest written to ${RELEASE_FILE}; no Test container was started"
}

candidate_status() {
  verify_execution_identity
  verify_required_tools
  verify_static_contract
  local head_sha upstream_sha dirty="yes" match="no"
  head_sha="$(git -C "${repository_root}" rev-parse HEAD)"
  upstream_sha="$(git -C "${repository_root}" rev-parse '@{upstream}')" || upstream_sha="unavailable"
  [[ -z "$(git -C "${repository_root}" status --porcelain=v1 --untracked-files=all)" ]] && dirty="no"
  [[ "${head_sha}" == "${upstream_sha}" ]] && match="yes"
  printf 'Repository HEAD: %s\nUpstream HEAD: %s\nWorkspace dirty: %s\nHEAD matches upstream: %s\n' \
    "${head_sha}" "${upstream_sha}" "${dirty}" "${match}"
  if [[ ! -e "${RELEASE_FILE}" ]]; then
    warning "no Test candidate has been prepared"
    return 0
  fi
  load_manifest
  inspect_image_record "${backend_image_reference}" "${candidate_sha}" "${backend_image_id}" >/dev/null
  inspect_image_record "${frontend_image_reference}" "${candidate_sha}" "${frontend_image_id}" >/dev/null
  inspect_base_image_id "${postgres_image_reference}" "${postgres_image_id}" >/dev/null
  inspect_base_image_id "${redis_image_reference}" "${redis_image_id}" >/dev/null
  printf 'Prepared candidate: %s\nBackend image: %s\nBackend image ID: %s\n' \
    "${candidate_sha}" "${backend_image_reference}" "${backend_image_id}"
  printf 'Frontend image: %s\nFrontend image ID: %s\nDeployed at: %s\n' \
    "${frontend_image_reference}" "${frontend_image_id}" "${deployed_at:-not deployed}"
  [[ "${candidate_sha}" == "${head_sha}" ]] && pass "prepared candidate matches repository HEAD" ||
    warning "prepared candidate does not match repository HEAD"
  if [[ -n "${deployed_at}" ]]; then
    local backend_id frontend_id backend_release frontend_release
    verify_config_file
    backend_id="$(service_container_id backend)"
    frontend_id="$(service_container_id frontend)"
    backend_release="$(docker_cmd inspect --type container --format '{{index .Config.Labels "com.photoorganizer.release"}}|{{.Image}}' -- "${backend_id}")"
    frontend_release="$(docker_cmd inspect --type container --format '{{index .Config.Labels "com.photoorganizer.release"}}|{{.Image}}' -- "${frontend_id}")"
    if [[ "${backend_release}" == "${candidate_sha}|${backend_image_id}" && "${frontend_release}" == "${candidate_sha}|${frontend_image_id}" ]]; then
      pass "deployed Test containers run the prepared candidate SHA and image IDs"
    else
      fail "Deployed Test container identity differs from the prepared candidate manifest."
    fi
  fi
}

deploy_candidate() {
  verify_execution_identity
  verify_required_tools
  verify_static_contract
  verify_config_file
  load_manifest
  [[ -z "${deployed_at}" ]] || fail "A Test candidate is already recorded as deployed. Candidate replacement is not implemented."
  [[ "$(verify_repository_candidate)" == "${candidate_sha}" ]] ||
    fail "Prepared candidate is not the exact current clean pushed commit."
  inspect_image_record "${backend_image_reference}" "${candidate_sha}" "${backend_image_id}" >/dev/null
  inspect_image_record "${frontend_image_reference}" "${candidate_sha}" "${frontend_image_id}" >/dev/null
  inspect_base_image_id "${postgres_image_reference}" "${postgres_image_id}" >/dev/null
  inspect_base_image_id "${redis_image_reference}" "${redis_image_id}" >/dev/null
  assert_no_test_resources
  verify_ports_free

  compose_cmd create --pull never --no-build
  verify_created_resource_allowlists
  compose_cmd start postgres redis
  wait_for_health postgres 120
  wait_for_health redis 120
  verify_empty_dependencies
  bootstrap_application_storage
  initialize_test_database
  compose_cmd start backend frontend
  wait_for_health backend 240
  wait_for_health frontend 180

  deployed_at="$(date -u +'%Y-%m-%dT%H:%M:%SZ')"
  write_manifest_to_path "${RELEASE_FILE}" "${deployed_at}"
  release_status
  health
  pass "first isolated Test candidate deployment completed without build, pull, reset, copy, or replacement"
}

release_pass_count=0
release_warning_count=0
release_failure_count=0

release_pass() {
  ((release_pass_count += 1))
  printf 'PASS: %s\n' "$*"
}

release_warning() {
  ((release_warning_count += 1))
  printf 'WARNING: %s\n' "$*"
}

release_failure() {
  ((release_failure_count += 1))
  printf 'FAILURE: %s\n' "$*" >&2
}

inspect_release_service() {
  local service="$1"
  local expected_image_id="$2"
  local expected_mount="${3:-}"
  local expected_networks="$4"
  local expected_binding="$5"
  local container_id metadata project_label service_label state health actual_image labels networks mounts bindings environment

  if ! container_id="$(service_container_id "${service}")"; then
    release_failure "Service ${service} does not have exactly one project-scoped container."
    return
  fi
  if ! metadata="$(docker_cmd inspect --type container --format '{{index .Config.Labels "com.docker.compose.project"}}|{{index .Config.Labels "com.docker.compose.service"}}|{{.State.Status}}|{{if .State.Health}}{{.State.Health.Status}}{{else}}not-configured{{end}}|{{.Image}}' -- "${container_id}")"; then
    release_failure "Could not inspect Test service ${service}."
    return
  fi
  IFS='|' read -r project_label service_label state health actual_image <<<"${metadata}"
  if [[ "${project_label}" == "${COMPOSE_PROJECT}" && "${service_label}" == "${service}" ]]; then
    release_pass "service ${service} has exact Compose project and service identity"
  else
    release_failure "Service ${service} labels are not the approved Test identity."
  fi
  [[ "${actual_image}" == "${expected_image_id}" ]] && release_pass "service ${service} uses the recorded image ID" ||
    release_failure "Service ${service} image ID differs from the release manifest."
  if [[ "${state}" == "running" && ("${health}" == "healthy" || "${health}" == "not-configured") ]]; then
    release_pass "service ${service} is running with health ${health}"
  elif [[ "${state}" == "created" || "${state}" == "exited" ]]; then
    release_warning "service ${service} is retained in state ${state}"
  else
    release_failure "Service ${service} has unexpected state ${state} and health ${health}."
  fi

  networks="$(docker_cmd inspect --type container --format '{{range $name, $_ := .NetworkSettings.Networks}}{{println $name}}{{end}}' -- "${container_id}")"
  network_sets_match "${expected_networks}" "${networks}" &&
    release_pass "service ${service} uses only its exact approved physical Test network set" ||
    release_failure "Service ${service} has a missing, additional, or unexpected physical network attachment."
  bindings="$(docker_cmd inspect --type container --format '{{range $port, $entries := .HostConfig.PortBindings}}{{range $entries}}{{printf "%s|%s|%s\n" $port .HostIp .HostPort}}{{end}}{{end}}' -- "${container_id}")"
  [[ "${bindings}" == "${expected_binding}" ]] && release_pass "service ${service} publication matches the Test contract" ||
    release_failure "Service ${service} has unexpected host publication."

  mounts="$(docker_cmd inspect --type container --format '{{range .Mounts}}{{printf "%s|%s|%s\n" .Type .Name .Destination}}{{end}}' -- "${container_id}")"
  if [[ -n "${expected_mount}" ]]; then
    [[ "${mounts}" == "${expected_mount}" ]] && release_pass "service ${service} uses only its isolated Test volume" ||
      release_failure "Service ${service} storage mapping is unexpected."
  elif [[ -z "${mounts}" ]]; then
    release_pass "service ${service} has no mutable volume attachment"
  else
    release_failure "Service ${service} has an unexpected mutable storage attachment."
  fi

  if [[ "${service}" == "backend" || "${service}" == "frontend" ]]; then
    labels="$(docker_cmd inspect --type container --format '{{index .Config.Labels "org.opencontainers.image.revision"}}|{{index .Config.Labels "com.photoorganizer.environment"}}|{{index .Config.Labels "com.photoorganizer.release"}}' -- "${container_id}")"
    [[ "${labels}" == "${candidate_sha}|test|${candidate_sha}" ]] && release_pass "service ${service} carries the exact candidate labels" ||
      release_failure "Service ${service} candidate labels are incorrect."
  fi

  environment="$(docker_cmd inspect --type container --format '{{range .Config.Env}}{{println .}}{{end}}' -- "${container_id}")"
  if [[ "${service}" == "backend" ]]; then
    if grep -Fqx 'APP_RUNTIME_PROFILE=test' <<<"${environment}" &&
      grep -Fqx 'POSTGRES_HOST=postgres' <<<"${environment}" &&
      grep -Fqx 'POSTGRES_DB=photo_organizer_test' <<<"${environment}" &&
      grep -Fqx 'REDIS_HOST=redis' <<<"${environment}"; then
      release_pass "backend runtime profile and private Test dependencies are exact"
    else
      release_failure "Backend runtime profile or private dependency configuration is incorrect."
    fi
    grep -Fqx 'STORAGE_MODE=local' <<<"${environment}" && release_pass "backend storage mode is local" ||
      release_failure "Backend storage mode is not local."
  elif [[ "${service}" == "frontend" ]]; then
    grep -Fqx 'BACKEND_INTERNAL_BASE_URL=http://backend:8001' <<<"${environment}" &&
      release_pass "frontend uses the private Test backend only through runtime configuration" ||
      release_failure "Frontend runtime backend destination is incorrect."
  fi
}

release_status() {
  verify_execution_identity
  verify_required_tools
  verify_static_contract
  verify_config_file
  load_manifest
  release_pass_count=0
  release_warning_count=0
  release_failure_count=0

  printf 'Photo Organizer Test Release Status\nCandidate: %s\nCompose project: %s\n' "${candidate_sha}" "${COMPOSE_PROJECT}"
  if inspect_image_record "${backend_image_reference}" "${candidate_sha}" "${backend_image_id}" >/dev/null; then
    release_pass "backend image reference, ID, and labels match the manifest"
  else
    release_failure "Backend image verification failed."
  fi
  if inspect_image_record "${frontend_image_reference}" "${candidate_sha}" "${frontend_image_id}" >/dev/null; then
    release_pass "frontend image reference, ID, and labels match the manifest"
  else
    release_failure "Frontend image verification failed."
  fi
  if inspect_base_image_id "${postgres_image_reference}" "${postgres_image_id}" >/dev/null; then
    release_pass "PostgreSQL image ID matches the manifest"
  else
    release_failure "PostgreSQL image verification failed."
  fi
  if inspect_base_image_id "${redis_image_reference}" "${redis_image_id}" >/dev/null; then
    release_pass "Redis image ID matches the manifest"
  else
    release_failure "Redis image verification failed."
  fi

  local container_count volume_count network_count internal_value network_metadata network_project_label network_label
  container_count="$(docker_cmd ps --all --filter "label=com.docker.compose.project=${COMPOSE_PROJECT}" --quiet | wc -l)"
  volume_count="$(docker_cmd volume ls --filter "label=com.docker.compose.project=${COMPOSE_PROJECT}" --quiet | wc -l)"
  network_count="$(docker_cmd network ls --filter "label=com.docker.compose.project=${COMPOSE_PROJECT}" --quiet | wc -l)"
  [[ "${container_count}" == "4" ]] && release_pass "exactly four Test service containers exist" ||
    release_failure "Expected four Test containers; found ${container_count}."
  [[ "${volume_count}" == "3" ]] && release_pass "exactly three isolated Test volumes exist" ||
    release_failure "Expected three Test volumes; found ${volume_count}."
  [[ "${network_count}" == "2" ]] && release_pass "exactly two isolated Test networks exist" ||
    release_failure "Expected two Test networks; found ${network_count}."

  local volume metadata project_label volume_label
  for volume in "${EXPECTED_VOLUMES[@]}"; do
    if metadata="$(docker_cmd volume inspect --format '{{index .Labels "com.docker.compose.project"}}|{{index .Labels "com.docker.compose.volume"}}' -- "${COMPOSE_PROJECT}_${volume}" 2>/dev/null)"; then
      IFS='|' read -r project_label volume_label <<<"${metadata}"
      if [[ "${project_label}" == "${COMPOSE_PROJECT}" && "${volume_label}" == "${volume}" ]]; then
        release_pass "volume ${COMPOSE_PROJECT}_${volume} has exact Test ownership"
      else
        release_failure "Volume ${COMPOSE_PROJECT}_${volume} labels are unexpected."
      fi
    else
      release_failure "Volume ${COMPOSE_PROJECT}_${volume} is missing."
    fi
  done

  network_metadata="$(docker_cmd network inspect --format '{{index .Labels "com.docker.compose.project"}}|{{index .Labels "com.docker.compose.network"}}|{{.Internal}}' -- "${TEST_NETWORK_INTERNAL}" 2>/dev/null || true)"
  IFS='|' read -r network_project_label network_label internal_value <<<"${network_metadata}"
  [[ "${network_project_label}" == "${COMPOSE_PROJECT}" && "${network_label}" == "application_internal" && "${internal_value}" == "true" ]] && release_pass "Test application dependency network has exact ownership and is internal" ||
    release_failure "Test application dependency network identity is unexpected."
  network_metadata="$(docker_cmd network inspect --format '{{index .Labels "com.docker.compose.project"}}|{{index .Labels "com.docker.compose.network"}}|{{.Internal}}' -- "${TEST_NETWORK_BROWSER}" 2>/dev/null || true)"
  IFS='|' read -r network_project_label network_label internal_value <<<"${network_metadata}"
  [[ "${network_project_label}" == "${COMPOSE_PROJECT}" && "${network_label}" == "browser_edge" && "${internal_value}" == "false" ]] && release_pass "Test browser-edge network has exact ownership and is non-internal" ||
    release_failure "Test browser-edge network identity is unexpected."

  inspect_release_service postgres "${postgres_image_id}" "volume|${TEST_VOLUME_POSTGRES}|/var/lib/postgresql/data" "${TEST_NETWORK_INTERNAL}" ""
  inspect_release_service redis "${redis_image_id}" "volume|${TEST_VOLUME_REDIS}|/data" "${TEST_NETWORK_INTERNAL}" ""
  inspect_release_service backend "${backend_image_id}" "volume|${TEST_VOLUME_APPLICATION}|/app/storage" "${TEST_NETWORK_INTERNAL}"$'\n'"${TEST_NETWORK_BROWSER}" "8001/tcp|127.0.0.1|18002"
  inspect_release_service frontend "${frontend_image_id}" "" "${TEST_NETWORK_BROWSER}" "3000/tcp|127.0.0.1|13001"

  printf '\nRelease summary: %d PASS, %d WARNING, %d FAILURE\n' \
    "${release_pass_count}" "${release_warning_count}" "${release_failure_count}"
  if ((release_failure_count > 0)); then
    printf 'FAILURE: Stop. Preserve Test resources and evidence; do not replace, recreate, reset, or clean up.\n' >&2
    return 1
  fi
  if ((release_warning_count > 0)); then
    printf 'WARNING: Release identity and isolation passed, but one or more retained Test services are stopped.\n'
    return 0
  fi
  printf 'PASS: Test release identity, isolation, storage, network, ports, and runtime configuration are verified.\n'
}

health() {
  verify_execution_identity
  verify_required_tools
  verify_static_contract
  local backend_payload failed=0
  if backend_payload="$(curl --fail --silent --show-error --max-time 10 -- "${BACKEND_HEALTH_URL}")"; then
    if python3 -c 'import json,sys; d=json.load(sys.stdin); raise SystemExit(0 if d.get("status")=="ok" and d.get("runtime_profile")=="test" and d.get("database")=="ok" and d.get("redis")=="ok" else 1)' <<<"${backend_payload}"; then
      pass "Test backend health reports runtime profile test with database and Redis available"
    else
      printf 'FAIL: Test backend health response did not match the approved Test contract.\n' >&2
      failed=1
    fi
  else
    printf 'FAIL: Test backend health is unavailable at %s\n' "${BACKEND_HEALTH_URL}" >&2
    failed=1
  fi
  if curl --fail --silent --show-error --max-time 10 --output /dev/null -- "${FRONTEND_HEALTH_URL}"; then
    pass "Test frontend is available at ${FRONTEND_HEALTH_URL}"
  else
    printf 'FAIL: Test frontend is unavailable at %s\n' "${FRONTEND_HEALTH_URL}" >&2
    failed=1
  fi
  ((failed == 0)) || return 1
  pass "Test application health checks completed"
}

run_existing_stack_action() {
  local action="$1"
  verify_execution_identity
  verify_required_tools
  verify_static_contract
  verify_config_file
  load_manifest
  [[ -n "${deployed_at}" ]] || fail "No completed first Test deployment is recorded."
  case "${action}" in
    start)
      release_status
      compose_cmd start postgres redis
      wait_for_health postgres 120
      wait_for_health redis 120
      compose_cmd start backend frontend
      wait_for_health backend 240
      wait_for_health frontend 180
      health
      ;;
    stop)
      release_status
      compose_cmd stop --timeout 30
      pass "stopped only existing ${COMPOSE_PROJECT} services; containers and data were retained"
      ;;
    status)
      compose_cmd ps --all
      ;;
    logs)
      compose_cmd logs --no-color --timestamps --tail 200
      ;;
    follow-logs)
      set +e
      compose_cmd logs --no-color --timestamps --tail 200 --follow
      local result=$?
      set -e
      if ((result == 130)); then
        printf 'Live Test log following stopped by user.\n'
        return 0
      fi
      return "${result}"
      ;;
    *) fail "Internal action is not allowlisted: ${action}" ;;
  esac
}

self_test() {
  verify_execution_identity
  verify_required_tools
  verify_static_contract

  is_full_sha "0123456789abcdef0123456789abcdef01234567" || fail "Valid full SHA was rejected."
  ! is_full_sha "0123456789abcdef" || fail "Short SHA was accepted."
  candidate_inputs_are_eligible clean "0123456789abcdef0123456789abcdef01234567" "0123456789abcdef0123456789abcdef01234567" ||
    fail "Valid clean/upstream candidate inputs were rejected."
  ! candidate_inputs_are_eligible dirty "0123456789abcdef0123456789abcdef01234567" "0123456789abcdef0123456789abcdef01234567" ||
    fail "Dirty candidate inputs were accepted."
  ! candidate_inputs_are_eligible clean "0123456789abcdef0123456789abcdef01234567" "1123456789abcdef0123456789abcdef01234567" ||
    fail "Upstream-mismatched candidate inputs were accepted."
  resource_inventory_is_empty "" "" "" || fail "Empty resource inventory was rejected."
  ! resource_inventory_is_empty "unexpected" "" "" || fail "Ambiguous resource inventory was accepted."

  local backend_networks reversed_backend_networks logical_backend_networks
  backend_networks="${TEST_NETWORK_INTERNAL}"$'\n'"${TEST_NETWORK_BROWSER}"
  reversed_backend_networks="${TEST_NETWORK_BROWSER}"$'\n'"${TEST_NETWORK_INTERNAL}"
  logical_backend_networks="application_internal"$'\n'"browser_edge"
  network_sets_match "${TEST_NETWORK_INTERNAL}" "${TEST_NETWORK_INTERNAL}" ||
    fail "Approved PostgreSQL physical network set was rejected."
  network_sets_match "${TEST_NETWORK_INTERNAL}" "${TEST_NETWORK_INTERNAL}" ||
    fail "Approved Redis physical network set was rejected."
  network_sets_match "${backend_networks}" "${backend_networks}" ||
    fail "Approved backend physical network set was rejected."
  network_sets_match "${TEST_NETWORK_BROWSER}" "${TEST_NETWORK_BROWSER}" ||
    fail "Approved frontend physical network set was rejected."
  network_sets_match "${backend_networks}" "${reversed_backend_networks}" ||
    fail "Backend physical network set incorrectly depends on inspection order."
  ! network_sets_match "${backend_networks}" "${TEST_NETWORK_INTERNAL}" ||
    fail "A backend network set missing browser-edge was accepted."
  ! network_sets_match "${TEST_NETWORK_BROWSER}" "${TEST_NETWORK_BROWSER}"$'\n'"bridge" ||
    fail "A frontend network set with an additional default bridge was accepted."
  ! network_sets_match "${TEST_NETWORK_INTERNAL}" "photo-organizer-dev_application_internal" ||
    fail "A Development network was accepted for a Test service."
  ! network_sets_match "${backend_networks}" "${logical_backend_networks}" ||
    fail "Logical Compose network names were accepted instead of physical Docker names."

  local temporary_directory temporary_manifest
  temporary_directory="$(mktemp -d)"
  trap 'rm -rf -- "${temporary_directory:-}"' RETURN
  temporary_manifest="${temporary_directory}/release.json"
  candidate_sha="0123456789abcdef0123456789abcdef01234567"
  backend_image_reference="${BACKEND_IMAGE_REPOSITORY}:${candidate_sha}"
  backend_image_id="sha256:$(printf 'a%.0s' {1..64})"
  frontend_image_reference="${FRONTEND_IMAGE_REPOSITORY}:${candidate_sha}"
  frontend_image_id="sha256:$(printf 'b%.0s' {1..64})"
  postgres_image_reference="${POSTGRES_IMAGE_REFERENCE}"
  postgres_image_id="sha256:$(printf 'c%.0s' {1..64})"
  redis_image_reference="${REDIS_IMAGE_REFERENCE}"
  redis_image_id="sha256:$(printf 'd%.0s' {1..64})"
  prepared_at="2026-01-01T00:00:00Z"
  write_manifest_to_path "${temporary_manifest}"
  [[ -s "${temporary_manifest}" && "$(stat -c '%a' -- "${temporary_manifest}")" == "600" ]] ||
    fail "Atomic release-manifest write self-test failed."
  python3 -m json.tool "${temporary_manifest}" >/dev/null || fail "Self-test manifest is not valid JSON."
  trap - RETURN
  rm -rf -- "${temporary_directory}"

  grep -Fq 'name: ${COMPOSE_PROJECT_NAME:' "${compose_file}" || fail "Compose project identity is not mandatory."
  grep -Fq 'APP_RUNTIME_PROFILE: test' "${compose_file}" || fail "Test runtime profile is absent."
  grep -Fq 'BACKEND_INTERNAL_BASE_URL: "http://backend:8001"' "${compose_file}" || fail "Runtime-neutral frontend destination is absent."
  grep -Fq '127.0.0.1' "${config_template}" || fail "Test template does not lock loopback publication."
  ! grep -Eq '^[[:space:]]*build:' "${compose_file}" || fail "Routine Test Compose unexpectedly contains a build directive."
  ! grep -Eq '^[[:space:]]*-[[:space:]]*(\.\.?/|/home/|/mnt/)' "${compose_file}" || fail "Test Compose contains a source or host-path bind mount."
  ! grep -Fq 'photo-organizer-dev_' "${compose_file}" || fail "Test Compose references a Development volume or network."
  ! grep -Fq 'latest' "${compose_file}" || fail "Test Compose references a latest tag."

  local action
  for action in "${ALLOWED_ACTIONS[@]}"; do
    grep -Fq "${action}" "${expected_script}" || fail "Required fixed action is absent: ${action}"
  done
  pass "script location, repository identity, and fixed action allowlist are valid"
  pass "candidate SHA, dirty-worktree, upstream-mismatch, and resource-ambiguity guards passed isolated tests"
  pass "exact physical Test network sets, order independence, and missing/additional/logical/Development rejection passed isolated tests"
  pass "atomic manifest write produced valid mode-0600 JSON"
  pass "Test Compose has fixed profile, runtime backend routing, loopback template, no build, no source bind, and no Development reference"
  pass "self-test completed without Docker daemon access or resource mutation"
}

main() {
  (($# == 1)) || {
    usage
    exit 2
  }
  case "$1" in
    self-test) self_test ;;
    init-config) init_config ;;
    prepare-candidate) prepare_candidate ;;
    candidate-status) candidate_status ;;
    deploy-candidate) deploy_candidate ;;
    start|stop|status|logs|follow-logs) run_existing_stack_action "$1" ;;
    health) health ;;
    release-status) release_status ;;
    *) usage; exit 2 ;;
  esac
}

main "$@"
