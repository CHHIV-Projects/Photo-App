#!/usr/bin/env bash
set -euo pipefail

expected_repo="/home/chuck/projects/photo-organizer-dev"
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd -- "${script_dir}/../.." && pwd)"
compose_file="${repo_root}/docker/compose.development.yml"
gpu_file="${repo_root}/docker/compose.development.gpu.yml"
env_file="${repo_root}/docker/.env.development"

if [[ "${repo_root}" != "${expected_repo}" ]]; then
  echo "Expected the editable Linux Development checkout at ${expected_repo}." >&2
  echo "Current checkout: ${repo_root}" >&2
  exit 2
fi

if [[ ! -f "${env_file}" ]]; then
  echo "Create ${env_file} from docker/.env.development.example first." >&2
  exit 2
fi

compose=(docker compose --env-file "${env_file}" --file "${compose_file}")

case "${1:-}" in
  config)
    "${compose[@]}" config
    ;;
  build)
    "${compose[@]}" build
    ;;
  build-gpu)
    "${compose[@]}" --file "${gpu_file}" build backend
    ;;
  up)
    "${compose[@]}" up --detach
    ;;
  up-gpu)
    "${compose[@]}" --file "${gpu_file}" up --detach
    ;;
  health)
    "${compose[@]}" ps
    ;;
  logs)
    if [[ -n "${2:-}" ]]; then
      "${compose[@]}" logs --tail 200 --follow "$2"
    else
      "${compose[@]}" logs --tail 200 --follow
    fi
    ;;
  down)
    "${compose[@]}" down
    ;;
  *)
    echo "Usage: $0 {config|build|build-gpu|up|up-gpu|health|logs [service]|down}" >&2
    exit 2
    ;;
esac
