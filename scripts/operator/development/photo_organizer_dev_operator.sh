#!/usr/bin/env bash
set -Eeuo pipefail

readonly EXPECTED_REPOSITORY="/home/chuck/projects/photo-organizer-dev"
readonly EXPECTED_USER="chuck"
readonly COMPOSE_PROJECT="photo-organizer-dev"
readonly BACKEND_HEALTH_URL="http://127.0.0.1:18001/health"
readonly FRONTEND_HEALTH_URL="http://127.0.0.1:13000/"
readonly EXPECTED_NAS_TARGET="/mnt/nas/photo-organizer"
readonly EXPECTED_NAS_SOURCE_IP="//192.168.1.171/PhotoOrganizer"
readonly EXPECTED_NAS_SOURCE_HOST="//HENDERSON-NAS/PhotoOrganizer"
readonly EXPECTED_NAS_FSTYPE="cifs"
readonly -a EXPECTED_SERVICES=(backend frontend postgres redis)
readonly -a EXPECTED_VOLUMES=(application_storage postgres_data redis_data)
readonly -a EXPECTED_STORAGE_CONFIG_LINES=(
  '      STORAGE_ROOT: /app/storage'
  '      DROP_ZONE_PATH: /app/storage/drop_zone'
  '      VAULT_PATH: /app/storage/vault'
  '      QUARANTINE_PATH: /app/storage/quarantine'
  '      INGEST_FAILURES_PATH: /app/storage/ingest_failures'
  '      PREVIEWS_PATH: /app/storage/previews'
  '      THUMBNAILS_PATH: /app/storage/thumbnails'
  '      REVIEW_PATH: /app/storage/review'
  '      LOGS_PATH: /app/storage/logs'
  '      REPORTS_PATH: /app/storage/logs'
  '      EXPORTS_ICLOUD_PATH: /app/storage/exports/icloud'
  '      MODEL_CACHE_PATH: /app/storage/models'
  '      DEEPFACE_HOME: /app/storage/models'
)

script_directory="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repository_root="$(cd -- "${script_directory}/../../.." && pwd)"
readonly script_directory
readonly repository_root
readonly environment_file="${repository_root}/docker/.env.development"
readonly compose_file="${repository_root}/docker/compose.development.yml"
readonly gpu_compose_file="${repository_root}/docker/compose.development.gpu.yml"
readonly expected_script="${repository_root}/scripts/operator/development/photo_organizer_dev_operator.sh"

readonly -a compose_config=(
  docker compose
  --project-name "${COMPOSE_PROJECT}"
  --env-file "${environment_file}"
  --file "${compose_file}"
  --file "${gpu_compose_file}"
)

readonly -a privileged_compose=(
  sudo -- docker compose
  --project-name "${COMPOSE_PROJECT}"
  --env-file "${environment_file}"
  --file "${compose_file}"
  --file "${gpu_compose_file}"
)

readonly -a recovery_compose=(timeout --foreground 60s "${privileged_compose[@]}")
readonly -a recovery_docker=(timeout --foreground 60s sudo -- docker)

usage() {
  cat >&2 <<'USAGE'
Usage: photo_organizer_dev_operator.sh {self-test|start|stop|status|health|logs|follow-logs|recovery-status}
USAGE
}

fail() {
  printf 'FAIL: %s\n' "$*" >&2
  exit 1
}

pass() {
  printf 'PASS: %s\n' "$*"
}

require_command() {
  local command_name="$1"
  command -v -- "${command_name}" >/dev/null 2>&1 || fail "Required command is unavailable: ${command_name}"
}

verify_execution_identity() {
  [[ "${EUID}" -ne 0 ]] || fail "Run this script as ${EXPECTED_USER}, not as root."
  [[ "$(id -un)" == "${EXPECTED_USER}" ]] || fail "Expected user ${EXPECTED_USER}; current user is $(id -un)."
}

verify_static_contract() {
  [[ "${repository_root}" == "${EXPECTED_REPOSITORY}" ]] ||
    fail "Expected repository ${EXPECTED_REPOSITORY}; resolved ${repository_root}."
  [[ "${script_directory}/photo_organizer_dev_operator.sh" == "${expected_script}" ]] ||
    fail "The operator script is not running from its approved tracked location."

  [[ -f "${environment_file}" ]] || fail "Protected Development environment file is missing."
  [[ -f "${compose_file}" ]] || fail "Development Compose file is missing."
  [[ -f "${gpu_compose_file}" ]] || fail "Development GPU overlay is missing."

  git -C "${repository_root}" check-ignore --quiet -- "${environment_file}" ||
    fail "Protected Development environment file is not ignored by Git."
  if git -C "${repository_root}" ls-files --error-unmatch -- "${environment_file}" >/dev/null 2>&1; then
    fail "Protected Development environment file is tracked by Git."
  fi
}

verify_required_tools() {
  require_command bash
  require_command curl
  require_command docker
  require_command git
  require_command id
  require_command findmnt
  require_command grep
  require_command readlink
  require_command sort
  require_command sudo
  require_command timeout
}

classify_nas_identity() {
  local source="${1,,}"
  local filesystem_type="${2,,}"

  if [[ "${filesystem_type}" != "${EXPECTED_NAS_FSTYPE}" ]]; then
    printf 'FAILURE\n'
    return
  fi

  case "${source}" in
    "${EXPECTED_NAS_SOURCE_IP,,}"|"${EXPECTED_NAS_SOURCE_HOST,,}")
      printf 'PASS\n'
      ;;
    *)
      printf 'FAILURE\n'
      ;;
  esac
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

self_test_nas_identity() {
  [[ "$(classify_nas_identity "${EXPECTED_NAS_SOURCE_IP}" "${EXPECTED_NAS_FSTYPE}")" == "PASS" ]] ||
    fail "The validated IP-form NAS identity was rejected."
  [[ "$(classify_nas_identity "${EXPECTED_NAS_SOURCE_HOST}" "${EXPECTED_NAS_FSTYPE}")" == "PASS" ]] ||
    fail "The documented hostname-form NAS identity was rejected."
  [[ "$(classify_nas_identity "//unexpected.example/PhotoOrganizer" "${EXPECTED_NAS_FSTYPE}")" == "FAILURE" ]] ||
    fail "An unexpected NAS source was not rejected."
  [[ "$(classify_nas_identity "${EXPECTED_NAS_SOURCE_IP}" "ext4")" == "FAILURE" ]] ||
    fail "An unexpected NAS filesystem type was not rejected."
}

self_test() {
  verify_execution_identity
  verify_required_tools
  verify_static_contract

  local -a actual_services=()
  local -a actual_volumes=()
  local -a sorted_services=()
  local -a sorted_volumes=()

  mapfile -t actual_services < <("${compose_config[@]}" config --services)
  mapfile -t sorted_services < <(printf '%s\n' "${actual_services[@]}" | sort)
  arrays_match EXPECTED_SERVICES sorted_services || fail "Unexpected Development service set."

  mapfile -t actual_volumes < <("${compose_config[@]}" config --volumes)
  mapfile -t sorted_volumes < <(printf '%s\n' "${actual_volumes[@]}" | sort)
  arrays_match EXPECTED_VOLUMES sorted_volumes || fail "Unexpected Development volume set."

  self_test_nas_identity

  pass "script location is approved"
  pass "repository root is ${EXPECTED_REPOSITORY}"
  pass "protected environment file is present, ignored, and untracked"
  pass "only the approved Development Compose files are selected"
  pass "Compose project is ${COMPOSE_PROJECT}"
  pass "service allowlist is postgres, redis, backend, frontend"
  pass "volume allowlist is postgres_data, redis_data, application_storage"
  pass "NAS identity checks accept only the validated CIFS sources"
  pass "required local tools are available"
  pass "self-test completed without Docker daemon or service mutation"
}


recovery_pass_count=0
recovery_warning_count=0
recovery_failure_count=0
recovery_stack_attention=0

recovery_pass() {
  ((recovery_pass_count += 1))
  printf 'PASS: %s\n' "$*"
}

recovery_warning() {
  ((recovery_warning_count += 1))
  printf 'WARNING: %s\n' "$*"
}

recovery_failure() {
  ((recovery_failure_count += 1))
  printf 'FAILURE: %s\n' "$*" >&2
}

verify_recovery_static_contract() {
  local config_output
  local -a actual_services=()
  local -a actual_volumes=()
  local -a sorted_services=()
  local -a sorted_volumes=()
  local storage_config_line
  local storage_config_valid=1

  if [[ "${repository_root}" != "${EXPECTED_REPOSITORY}" ]] ||
    [[ "${script_directory}/photo_organizer_dev_operator.sh" != "${expected_script}" ]]; then
    recovery_failure "The operator is not running from the approved repository and tracked script path."
    return
  fi
  recovery_pass "server operator is running from the approved repository"

  if [[ ! -f "${environment_file}" ]] || [[ ! -f "${compose_file}" ]] || [[ ! -f "${gpu_compose_file}" ]]; then
    recovery_failure "One or more required Development environment or Compose files are missing."
    return
  fi
  recovery_pass "required Development environment and Compose files are present"

  if ! git -C "${repository_root}" check-ignore --quiet -- "${environment_file}" ||
    git -C "${repository_root}" ls-files --error-unmatch -- "${environment_file}" >/dev/null 2>&1; then
    recovery_failure "The protected Development environment file is not safely ignored and untracked."
  else
    recovery_pass "protected Development environment file is ignored and untracked"
  fi

  if ! config_output="$("${compose_config[@]}" config --services)"; then
    recovery_failure "The Development Compose service configuration could not be read."
  else
    mapfile -t actual_services <<<"${config_output}"
    mapfile -t sorted_services < <(printf '%s\n' "${actual_services[@]}" | sort)
    if arrays_match EXPECTED_SERVICES sorted_services; then
      recovery_pass "Compose project ${COMPOSE_PROJECT} has the exact expected service configuration"
    else
      recovery_failure "The Compose service set is not exactly backend, frontend, postgres, redis."
    fi
  fi

  if ! config_output="$("${compose_config[@]}" config --volumes)"; then
    recovery_failure "The Development Compose volume configuration could not be read."
  else
    mapfile -t actual_volumes <<<"${config_output}"
    mapfile -t sorted_volumes < <(printf '%s\n' "${actual_volumes[@]}" | sort)
    if arrays_match EXPECTED_VOLUMES sorted_volumes; then
      recovery_pass "Compose project declares only the three expected local named volumes"
    else
      recovery_failure "The Compose volume set is not exactly application_storage, postgres_data, redis_data."
    fi
  fi

  for storage_config_line in "${EXPECTED_STORAGE_CONFIG_LINES[@]}"; do
    if ! grep -Fqx "${storage_config_line}" "${compose_file}"; then
      storage_config_valid=0
    fi
  done

  if grep -Fqx 'STORAGE_MODE=local' "${environment_file}" &&
    grep -Fqx '      STORAGE_MODE: local' "${compose_file}" &&
    grep -Fqx '      - application_storage:/app/storage' "${compose_file}" &&
    ((storage_config_valid != 0)); then
    recovery_pass "configured application storage authority is local named volume application_storage"
    recovery_pass "configured Vault, preview, staging, log, export, and model-cache paths remain under /app/storage"
  else
    recovery_failure "Configured Development application storage paths do not match the approved local /app/storage named-volume topology."
  fi
}

inspect_recovery_containers() {
  local -n container_ids_ref="$1"
  local -n container_states_ref="$2"
  local service
  local service_output metadata project_label service_label state health
  local -a service_ids=()

  for service in "${EXPECTED_SERVICES[@]}"; do
    if ! service_output="$("${recovery_compose[@]}" ps --all --quiet "${service}")"; then
      recovery_failure "Could not inspect Compose service ${service} in project ${COMPOSE_PROJECT}."
      continue
    fi
    service_ids=()
    if [[ -n "${service_output}" ]]; then
      mapfile -t service_ids <<<"${service_output}"
    fi

    if ((${#service_ids[@]} != 1)); then
      recovery_failure "Expected one container for Compose service ${service}; found ${#service_ids[@]}."
      continue
    fi

    container_ids_ref["${service}"]="${service_ids[0]}"
    if ! metadata="$("${recovery_docker[@]}" inspect \
      --type container \
      --format '{{index .Config.Labels "com.docker.compose.project"}}|{{index .Config.Labels "com.docker.compose.service"}}|{{.State.Status}}|{{if .State.Health}}{{.State.Health.Status}}{{else}}not-configured{{end}}' \
      -- "${service_ids[0]}")"; then
      recovery_failure "Could not inspect the project-scoped ${service} container."
      continue
    fi

    IFS='|' read -r project_label service_label state health <<<"${metadata}"
    if [[ "${project_label}" != "${COMPOSE_PROJECT}" ]] || [[ "${service_label}" != "${service}" ]]; then
      recovery_failure "Container returned for ${service} does not have the exact Compose project and service labels."
      continue
    fi
    container_states_ref["${service}"]="${state}"
    recovery_pass "service ${service} has one correctly labeled ${COMPOSE_PROJECT} container"

    if [[ "${state}" == "running" ]]; then
      recovery_pass "service ${service} container state is running"
      case "${health}" in
        healthy)
          recovery_pass "service ${service} container health is healthy"
          ;;
        not-configured)
          recovery_pass "service ${service} has no Docker health status; running state was checked"
          ;;
        *)
          recovery_warning "service ${service} container health is ${health}"
          recovery_stack_attention=1
          ;;
      esac
    else
      recovery_warning "service ${service} container state is ${state}; use stack status before deciding whether to start the Development stack"
      recovery_warning "service ${service} health is not current while the container is ${state}"
      recovery_stack_attention=1
    fi
  done
}

verify_service_volume_mount() {
  local service="$1"
  local container_id="$2"
  local volume_name="$3"
  local destination="$4"
  local mounts

  if [[ -z "${container_id}" ]]; then
    recovery_failure "Cannot verify ${service} storage because its project-scoped container is unavailable."
    return
  fi

  if ! mounts="$("${recovery_docker[@]}" inspect \
    --type container \
    --format '{{range .Mounts}}{{printf "%s|%s|%s\n" .Type .Name .Destination}}{{end}}' \
    -- "${container_id}")"; then
    recovery_failure "Could not inspect the ${service} container storage mounts."
    return
  fi

  if grep -Fqx "volume|${COMPOSE_PROJECT}_${volume_name}|${destination}" <<<"${mounts}"; then
    recovery_pass "service ${service} uses ${COMPOSE_PROJECT}_${volume_name} at ${destination}"
  else
    recovery_failure "Service ${service} does not use the expected project named volume at ${destination}."
  fi
}

verify_recovery_volumes() {
  local -n container_ids_ref="$1"
  local -n container_states_ref="$2"
  local volume_name full_name metadata project_label volume_label mountpoint_path

  for volume_name in "${EXPECTED_VOLUMES[@]}"; do
    full_name="${COMPOSE_PROJECT}_${volume_name}"
    if ! metadata="$("${recovery_docker[@]}" volume inspect \
      --format '{{index .Labels "com.docker.compose.project"}}|{{index .Labels "com.docker.compose.volume"}}|{{.Mountpoint}}' \
      -- "${full_name}" 2>/dev/null)"; then
      recovery_failure "Required local Docker volume ${full_name} is unavailable."
      continue
    fi

    IFS='|' read -r project_label volume_label mountpoint_path <<<"${metadata}"
    if [[ "${project_label}" != "${COMPOSE_PROJECT}" ]] || [[ "${volume_label}" != "${volume_name}" ]] ||
      [[ -z "${mountpoint_path}" ]]; then
      recovery_failure "Volume ${full_name} does not have the expected Compose project/volume identity and mountpoint."
      continue
    fi
    recovery_pass "local Docker volume ${full_name} has the expected Compose identity"
  done

  verify_service_volume_mount "postgres" "${container_ids_ref[postgres]:-}" "postgres_data" "/var/lib/postgresql/data"
  verify_service_volume_mount "redis" "${container_ids_ref[redis]:-}" "redis_data" "/data"
  verify_service_volume_mount "backend" "${container_ids_ref[backend]:-}" "application_storage" "/app/storage"

  if [[ -z "${container_ids_ref[backend]:-}" ]]; then
    return
  fi
  if [[ "${container_states_ref[backend]:-}" != "running" ]]; then
    recovery_warning "backend is not running, so in-container /app/storage reachability was not checked"
    recovery_stack_attention=1
  elif "${recovery_docker[@]}" exec -- "${container_ids_ref[backend]}" test -d /app/storage >/dev/null 2>&1; then
    recovery_pass "backend can reach the configured /app/storage directory"
  else
    recovery_failure "Backend cannot verify the configured /app/storage directory."
  fi
}

get_port_bindings() {
  local container_id="$1"
  "${recovery_docker[@]}" inspect \
    --type container \
    --format '{{range $port, $entries := .HostConfig.PortBindings}}{{range $entries}}{{printf "%s|%s|%s\n" $port .HostIp .HostPort}}{{end}}{{end}}' \
    -- "${container_id}"
}

verify_exact_port_bindings() {
  local service="$1"
  local container_id="$2"
  local expected_binding="$3"
  local bindings

  if [[ -z "${container_id}" ]]; then
    recovery_failure "Cannot verify ${service} publication because its project-scoped container is unavailable."
    return
  fi

  if ! bindings="$(get_port_bindings "${container_id}")"; then
    recovery_failure "Could not inspect ${service} host publication."
  elif [[ "${bindings}" == "${expected_binding}" ]]; then
    recovery_pass "service ${service} publication is exactly ${expected_binding}"
  else
    recovery_failure "Service ${service} host publication differs from the approved loopback-only binding."
  fi
}

verify_no_port_bindings() {
  local service="$1"
  local container_id="$2"
  local bindings

  if [[ -z "${container_id}" ]]; then
    recovery_failure "Cannot verify ${service} publication because its project-scoped container is unavailable."
    return
  fi

  if ! bindings="$(get_port_bindings "${container_id}")"; then
    recovery_failure "Could not inspect ${service} host publication."
  elif [[ -z "${bindings}" ]]; then
    recovery_pass "service ${service} is not published to the host"
  else
    recovery_failure "Service ${service} has an unexpected host publication."
  fi
}

verify_nas_status() {
  local resolved_target row source target filesystem_type
  local cifs_output mount_output
  local -a cifs_rows=()
  local -a mount_rows=()

  if ! timeout --foreground 12s test -e "${EXPECTED_NAS_TARGET}"; then
    recovery_warning "NAS target ${EXPECTED_NAS_TARGET} is unavailable; the local-volume Development stack remains authoritative"
    return
  fi

  if [[ -L "${EXPECTED_NAS_TARGET}" ]]; then
    recovery_failure "NAS target ${EXPECTED_NAS_TARGET} is a symbolic link; stop and inspect storage authority."
    return
  fi

  if ! resolved_target="$(timeout --foreground 12s readlink -f -- "${EXPECTED_NAS_TARGET}")" ||
    [[ "${resolved_target}" != "${EXPECTED_NAS_TARGET}" ]]; then
    recovery_failure "NAS target does not resolve to the exact expected path; stop and inspect storage authority."
    return
  fi
  recovery_pass "NAS target exists at the exact expected path"

  cifs_output="$(timeout --foreground 12s findmnt -rn -t cifs -T "${EXPECTED_NAS_TARGET}" -o SOURCE,TARGET,FSTYPE || true)"
  if [[ -n "${cifs_output}" ]]; then
    mapfile -t cifs_rows <<<"${cifs_output}"
  fi
  if ((${#cifs_rows[@]} == 0)); then
    mount_output="$(timeout --foreground 12s findmnt -rn -M "${EXPECTED_NAS_TARGET}" -o SOURCE,TARGET,FSTYPE || true)"
    if [[ -n "${mount_output}" ]]; then
      mapfile -t mount_rows <<<"${mount_output}"
    fi
    for row in "${mount_rows[@]}"; do
      if [[ "${row}" != *" autofs" ]]; then
        recovery_failure "NAS target has an unexpected mounted filesystem identity: ${row}"
        return
      fi
    done
    recovery_warning "NAS is not currently mounted as CIFS at ${EXPECTED_NAS_TARGET}; this does not block the local-volume Development stack"
    return
  fi

  if ((${#cifs_rows[@]} != 1)); then
    recovery_failure "Expected one active CIFS row for ${EXPECTED_NAS_TARGET}; found ${#cifs_rows[@]}."
    return
  fi

  read -r source target filesystem_type <<<"${cifs_rows[0]}"
  if [[ "${target}" != "${EXPECTED_NAS_TARGET}" ]] ||
    [[ "$(classify_nas_identity "${source}" "${filesystem_type}")" != "PASS" ]]; then
    recovery_failure "NAS mount source/type is unexpected: source=${source}, target=${target}, type=${filesystem_type}."
    return
  fi

  recovery_pass "NAS is independently mounted with the validated source ${source} and filesystem type ${filesystem_type}"
}

print_recovery_summary() {
  printf '\nRecovery summary: %d PASS, %d WARNING, %d FAILURE\n' \
    "${recovery_pass_count}" "${recovery_warning_count}" "${recovery_failure_count}"

  if ((recovery_failure_count > 0)); then
    printf 'FAILURE: Stop. Do not start or restart the Development stack until the failed identity, storage, or publication checks are reviewed.\n'
    printf 'NEXT ACTION: Save this output, then use Show Stack Status and Show Recent Logs without deleting or recreating anything.\n'
    return 1
  fi

  if ((recovery_warning_count > 0)); then
    printf 'WARNING: The verified local Docker volumes remain the current Development storage authority; warnings require review but do not make NAS a startup prerequisite.\n'
    if ((recovery_stack_attention != 0)); then
      printf 'NEXT ACTION: Use Show Stack Status, Check Application Health, and Show Recent Logs before deciding whether Start Development Stack is appropriate.\n'
    else
      printf 'NEXT ACTION: The local-volume Development stack may be used; address the independent NAS warning separately.\n'
    fi
    return 0
  fi

  printf 'PASS: Current Development restart and recovery status is healthy.\n'
  printf 'NEXT ACTION: No recovery action is required.\n'
}

recovery_status() {
  verify_execution_identity

  recovery_pass_count=0
  recovery_warning_count=0
  recovery_failure_count=0
  recovery_stack_attention=0

  printf 'Photo Organizer Development Restart and Recovery Status\n'
  printf 'Compose project: %s\n' "${COMPOSE_PROJECT}"
  printf 'Storage mode: local\n\n'

  local command_name
  for command_name in docker findmnt git grep id readlink sort sudo timeout; do
    if command -v -- "${command_name}" >/dev/null 2>&1; then
      recovery_pass "required command is available: ${command_name}"
    else
      recovery_failure "Required command is unavailable: ${command_name}"
    fi
  done

  verify_recovery_static_contract

  if ((recovery_failure_count > 0)); then
    verify_nas_status
    print_recovery_summary
    return
  fi

  if ! "${recovery_docker[@]}" info --format '{{.ServerVersion}}' >/dev/null; then
    recovery_failure "Docker daemon is unavailable through the approved interactive-sudo path."
    verify_nas_status
    print_recovery_summary
    return
  fi
  recovery_pass "Docker daemon is available; no global Docker action was performed"

  local -A container_ids=()
  local -A container_states=()
  inspect_recovery_containers container_ids container_states
  verify_recovery_volumes container_ids container_states
  verify_exact_port_bindings "backend" "${container_ids[backend]:-}" "8001/tcp|127.0.0.1|18001"
  verify_exact_port_bindings "frontend" "${container_ids[frontend]:-}" "3000/tcp|127.0.0.1|13000"
  verify_no_port_bindings "postgres" "${container_ids[postgres]:-}"
  verify_no_port_bindings "redis" "${container_ids[redis]:-}"
  verify_nas_status
  print_recovery_summary
}

check_http_endpoint() {
  local label="$1"
  local url="$2"

  if curl \
    --fail \
    --silent \
    --show-error \
    --max-time 10 \
    --output /dev/null \
    -- "${url}"; then
    pass "${label} is available at ${url}"
    return 0
  fi

  printf 'FAIL: %s is unavailable at %s\n' "${label}" "${url}" >&2
  return 1
}

health() {
  verify_execution_identity
  require_command curl
  verify_static_contract

  local failed=0
  check_http_endpoint "backend health" "${BACKEND_HEALTH_URL}" || failed=1
  check_http_endpoint "frontend" "${FRONTEND_HEALTH_URL}" || failed=1

  if ((failed != 0)); then
    printf 'FAIL: one or more application health checks failed.\n' >&2
    return 1
  fi

  pass "Development application health checks completed"
}

run_privileged_action() {
  local action="$1"
  verify_execution_identity
  verify_required_tools
  verify_static_contract

  case "${action}" in
    start)
      "${privileged_compose[@]}" up \
        --detach \
        --wait \
        --wait-timeout 180 \
        --no-build \
        --pull never \
        --no-recreate
      ;;
    stop)
      "${privileged_compose[@]}" stop --timeout 30
      ;;
    status)
      "${privileged_compose[@]}" ps --all
      ;;
    logs)
      "${privileged_compose[@]}" logs \
        --no-color \
        --timestamps \
        --tail 200
      ;;
    follow-logs)
      "${privileged_compose[@]}" logs \
        --no-color \
        --timestamps \
        --tail 200 \
        --follow
      ;;
    *)
      fail "Internal action is not allowlisted: ${action}"
      ;;
  esac
}

main() {
  (($# == 1)) || {
    usage
    exit 2
  }

  case "$1" in
    self-test)
      self_test
      ;;
    start|stop|status|logs|follow-logs)
      run_privileged_action "$1"
      ;;
    health)
      health
      ;;
    recovery-status)
      recovery_status
      ;;
    *)
      usage
      exit 2
      ;;
  esac
}

main "$@"
