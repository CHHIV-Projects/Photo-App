#!/usr/bin/env bash
set -Eeuo pipefail

readonly EXPECTED_REPOSITORY="/home/chuck/projects/photo-organizer-dev"
readonly EXPECTED_USER="chuck"
readonly COMPOSE_PROJECT="photo-organizer-dev"
readonly BACKEND_HEALTH_URL="http://127.0.0.1:18001/health"
readonly FRONTEND_HEALTH_URL="http://127.0.0.1:13000/"

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

usage() {
  cat >&2 <<'USAGE'
Usage: photo_organizer_dev_operator.sh {self-test|start|stop|status|health|logs|follow-logs}
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
  require_command sort
  require_command sudo
}

self_test() {
  verify_execution_identity
  verify_required_tools
  verify_static_contract

  local -a actual_services=()
  local -a expected_services=(backend frontend postgres redis)
  local -a sorted_services=()
  local service

  mapfile -t actual_services < <("${compose_config[@]}" config --services)
  ((${#actual_services[@]} == 4)) ||
    fail "Expected exactly four Development services; found ${#actual_services[@]}."

  mapfile -t sorted_services < <(printf '%s\n' "${actual_services[@]}" | sort)
  for service in "${!expected_services[@]}"; do
    [[ "${sorted_services[service]}" == "${expected_services[service]}" ]] ||
      fail "Unexpected Development service set."
  done

  pass "script location is approved"
  pass "repository root is ${EXPECTED_REPOSITORY}"
  pass "protected environment file is present, ignored, and untracked"
  pass "only the approved Development Compose files are selected"
  pass "Compose project is ${COMPOSE_PROJECT}"
  pass "service allowlist is postgres, redis, backend, frontend"
  pass "required local tools are available"
  pass "self-test completed without Docker daemon or service mutation"
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
    *)
      usage
      exit 2
      ;;
  esac
}

main "$@"
