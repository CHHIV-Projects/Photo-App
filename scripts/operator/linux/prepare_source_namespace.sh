#!/usr/bin/env bash
set -Eeuo pipefail

readonly CONFIG="/etc/photo-organizer/source-access.json"
readonly SOURCE_NAMESPACE="/mnt/photo-organizer-sources"
readonly LOCAL_SLOT="${SOURCE_NAMESPACE}/local/server-photos"
readonly NAS_SLOT="${SOURCE_NAMESPACE}/nas/photo-organizer"
readonly NAS_AUTHORITY="/mnt/nas/photo-organizer"
readonly NAS_SOURCE="//192.168.1.171/PhotoOrganizer"
readonly MAX_CLEANUP_ATTEMPTS=16

created_namespace_mount=0
created_nas_slot_mount=0
changed_preexisting_propagation=0
operation_succeeded=0
authority_major_minor=""
expected_namespace_uuid=""
expected_namespace_fstype=""

fail() {
  printf 'FAIL: %s\n' "$*" >&2
  exit 1
}

query_mountpoint() {
  local target="$1"
  local fields="$2"
  local -n result_ref="$3"
  local output=""
  local status=0

  if output="$(findmnt --kernel --raw --noheadings --nofsroot --mountpoint "${target}" --output "${fields}" 2>/dev/null)"; then
    status=0
  else
    status=$?
  fi
  result_ref="${output}"
  if ((status == 0)) && [[ -n "${output}" ]]; then
    return 0
  fi
  if ((status == 1)) && [[ -z "${output}" ]]; then
    return 1
  fi
  return 2
}

validate_namespace_rows() {
  local rows_text="$1"
  local expected_uuid="$2"
  local expected_fstype="$3"
  local expected_propagation="$4"
  local row target filesystem_uuid filesystem propagation extra
  local -a rows=()

  [[ -n "${rows_text}" ]] || return 1
  mapfile -t rows <<<"${rows_text}"
  (("${#rows[@]}" == 1)) || return 1
  row="${rows[0]}"
  read -r target filesystem_uuid filesystem propagation extra <<<"${row}"
  [[ -n "${target:-}" && -n "${filesystem_uuid:-}" &&
    -n "${filesystem:-}" && -n "${propagation:-}" &&
    -z "${extra:-}" ]] || return 1
  [[ "${target}" == "${SOURCE_NAMESPACE}" ]] || return 1
  [[ "${filesystem_uuid,,}" == "${expected_uuid,,}" ]] || return 1
  [[ "${filesystem,,}" == "${expected_fstype,,}" ]] || return 1
  [[ "${expected_propagation}" == "any" ||
    "${propagation}" == "${expected_propagation}" ]] || return 1
}

validate_nas_slot_rows() {
  local rows_text="$1"
  local expected_major_minor="$2"
  local expected_propagation="$3"
  local allow_duplicates="${4:-0}"
  local row target source filesystem fsroot major_minor propagation extra
  local -a rows=()

  [[ -n "${rows_text}" ]] || return 1
  mapfile -t rows <<<"${rows_text}"
  if [[ "${allow_duplicates}" == "1" ]]; then
    (("${#rows[@]}" >= 1 && "${#rows[@]}" <= MAX_CLEANUP_ATTEMPTS)) || return 1
  else
    (("${#rows[@]}" == 1)) || return 1
  fi
  for row in "${rows[@]}"; do
    read -r target source filesystem fsroot major_minor propagation extra <<<"${row}"
    [[ -n "${target:-}" && -n "${source:-}" && -n "${filesystem:-}" &&
      -n "${fsroot:-}" && -n "${major_minor:-}" &&
      -n "${propagation:-}" && -z "${extra:-}" ]] || return 1
    [[ "${target}" == "${NAS_SLOT}" &&
      "${source}" == "${NAS_SOURCE}" &&
      "${filesystem}" == "cifs" &&
      "${fsroot}" == "/" &&
      "${major_minor}" == "${expected_major_minor}" ]] || return 1
    [[ "${expected_propagation}" == "any" ||
      "${propagation}" == "${expected_propagation}" ]] || return 1
  done
}

validate_authority_rows() {
  local rows_text="$1"
  local row target source filesystem fsroot major_minor propagation extra
  local active_count=0
  local autofs_count=0
  local -a rows=()

  authority_major_minor=""
  [[ -n "${rows_text}" ]] || return 1
  mapfile -t rows <<<"${rows_text}"
  for row in "${rows[@]}"; do
    read -r target source filesystem fsroot major_minor propagation extra <<<"${row}"
    [[ -n "${target:-}" && -n "${source:-}" && -n "${filesystem:-}" &&
      -n "${fsroot:-}" && -n "${major_minor:-}" &&
      -n "${propagation:-}" && -z "${extra:-}" ]] || return 1
    [[ "${target}" == "${NAS_AUTHORITY}" && "${fsroot}" == "/" &&
      "${major_minor}" =~ ^[0-9]+:[0-9]+$ ]] || return 1
    if [[ "${filesystem}" == "autofs" ]]; then
      [[ "${source}" == "systemd-1" ]] || return 1
      ((autofs_count += 1))
      ((autofs_count == 1)) || return 1
    elif [[ "${filesystem}" == "cifs" ]]; then
      [[ "${source}" == "${NAS_SOURCE}" ]] || return 1
      ((active_count += 1))
      ((active_count == 1)) || return 1
      authority_major_minor="${major_minor}"
    else
      return 1
    fi
  done
  ((active_count == 1)) && [[ -n "${authority_major_minor}" ]]
}

validate_local_backing() {
  local output status=0
  local uuid filesystem extra
  if output="$(findmnt --kernel --raw --noheadings --target "${LOCAL_SLOT}" --output UUID,FSTYPE 2>/dev/null)"; then
    status=0
  else
    status=$?
  fi
  ((status == 0)) || return 1
  [[ "$(wc -l <<<"${output}")" == "1" ]] || return 1
  read -r uuid filesystem extra <<<"${output}"
  [[ -n "${uuid:-}" && -n "${filesystem:-}" && -z "${extra:-}" ]] || return 1
  [[ "${uuid,,}" == "${expected_namespace_uuid,,}" &&
    "${filesystem,,}" == "${expected_namespace_fstype,,}" ]]
}

load_config_identity() {
  local identity
  identity="$(python3 -c '
import json, sys
path, namespace, local_slot, nas_slot, nas_source, nas_authority = sys.argv[1:]
data = json.load(open(path, encoding="utf-8"))
locations = data.get("locations")
local = [x for x in locations if x.get("location_id") == "linux-local-server-photos"] if isinstance(locations, list) else []
nas = [x for x in locations if x.get("location_id") == "linux-nas-photo-organizer"] if isinstance(locations, list) else []
assert data.get("source_namespace") == namespace and len(local) == 1 and len(nas) == 1
assert local[0].get("host_slot") == local_slot and local[0].get("source_type") == "local"
assert nas[0].get("host_slot") == nas_slot and nas[0].get("source_type") == "nas"
assert nas[0].get("canonical_source") == nas_source and nas[0].get("authoritative_target") == nas_authority
values = (local[0].get("filesystem_uuid"), local[0].get("filesystem_type"), data.get("data_read_group"))
assert all(isinstance(value, str) and value and not value.startswith("REPLACE_") for value in values)
print("|".join(values))
' "${CONFIG}" "${SOURCE_NAMESPACE}" "${LOCAL_SLOT}" "${NAS_SLOT}" "${NAS_SOURCE}" "${NAS_AUTHORITY}")" ||
    fail "Protected Source-access configuration does not match the fixed Mounted Source contract."
  local data_read_group
  IFS='|' read -r expected_namespace_uuid expected_namespace_fstype data_read_group <<<"${identity}"
  getent group "${data_read_group}" >/dev/null ||
    fail "Approved Source data-read group does not exist."
  install -d -o root -g root -m 0755     "${SOURCE_NAMESPACE}" "${SOURCE_NAMESPACE}/local" "${SOURCE_NAMESPACE}/nas"
  install -d -o root -g "${data_read_group}" -m 0750 "${LOCAL_SLOT}"
  install -d -o root -g root -m 0755 "${NAS_SLOT}"
}

require_namespace() {
  local expected_propagation="$1"
  local rows=""
  query_mountpoint "${SOURCE_NAMESPACE}" "TARGET,UUID,FSTYPE,PROPAGATION" rows ||
    fail "Exact Source namespace mount evidence is missing or unavailable."
  validate_namespace_rows     "${rows}" "${expected_namespace_uuid}" "${expected_namespace_fstype}" "${expected_propagation}" ||
    fail "Exact Source namespace identity or propagation is invalid."
}

require_nas_slot() {
  local expected_propagation="$1"
  local rows=""
  query_mountpoint "${NAS_SLOT}" "TARGET,SOURCE,FSTYPE,FSROOT,MAJ:MIN,PROPAGATION" rows ||
    fail "Exact NAS slot mount evidence is missing or unavailable."
  validate_nas_slot_rows "${rows}" "${authority_major_minor}" "${expected_propagation}" ||
    fail "Exact NAS slot identity, uniqueness, or propagation is invalid."
}

cleanup_nas_slot() {
  local rows=""
  local status attempt
  for ((attempt = 1; attempt <= MAX_CLEANUP_ATTEMPTS; attempt += 1)); do
    if query_mountpoint "${NAS_SLOT}" "TARGET,SOURCE,FSTYPE,FSROOT,MAJ:MIN,PROPAGATION" rows; then
      validate_nas_slot_rows "${rows}" "${authority_major_minor}" "any" 1 ||
        return 1
      umount -- "${NAS_SLOT}" || return 1
    else
      status=$?
      ((status == 1)) && return 0
      return 1
    fi
  done
  return 1
}

cleanup_namespace() {
  local rows=""
  local status
  if query_mountpoint "${SOURCE_NAMESPACE}" "TARGET,UUID,FSTYPE,PROPAGATION" rows; then
    validate_namespace_rows "${rows}" "${expected_namespace_uuid}" "${expected_namespace_fstype}" "any" ||
      return 1
    umount -- "${SOURCE_NAMESPACE}" || return 1
    if query_mountpoint "${SOURCE_NAMESPACE}" "TARGET,UUID,FSTYPE,PROPAGATION" rows; then
      return 1
    else
      status=$?
      ((status == 1))
    fi
  else
    status=$?
    ((status == 1))
  fi
}

rollback_invocation() {
  local failed=0
  if ((created_nas_slot_mount == 1)); then
    cleanup_nas_slot || failed=1
  fi
  if ((created_namespace_mount == 1)); then
    ((failed == 0)) && cleanup_namespace || failed=1
  elif ((changed_preexisting_propagation == 1)); then
    if mount --make-rshared "${SOURCE_NAMESPACE}"; then
      require_namespace "shared"
    else
      failed=1
    fi
  fi
  ((failed == 0))
}

cleanup_on_exit() {
  local status="$1"
  trap - EXIT HUP INT TERM
  if ((operation_succeeded == 0)) &&
    ((created_namespace_mount == 1 || created_nas_slot_mount == 1 ||
      changed_preexisting_propagation == 1)); then
    rollback_invocation ||
      printf 'FAIL: Invocation-owned Mounted Source rollback is incomplete; manual review is required.\n' >&2
  fi
  exit "${status}"
}

prepare_mount_topology() {
  local namespace_rows=""
  local slot_rows=""
  local namespace_status slot_status
  local namespace_present=0
  local slot_present=0

  if query_mountpoint "${SOURCE_NAMESPACE}" "TARGET,UUID,FSTYPE,PROPAGATION" namespace_rows; then
    namespace_present=1
  else
    namespace_status=$?
    ((namespace_status == 1)) || fail "Source namespace mount evidence is unavailable."
  fi
  if query_mountpoint "${NAS_SLOT}" "TARGET,SOURCE,FSTYPE,FSROOT,MAJ:MIN,PROPAGATION" slot_rows; then
    slot_present=1
  else
    slot_status=$?
    ((slot_status == 1)) || fail "NAS slot mount evidence is unavailable."
  fi

  ((namespace_present == 1 || slot_present == 0)) ||
    fail "NAS slot exists without the exact Source namespace root."
  if ((namespace_present == 1)); then
    validate_namespace_rows       "${namespace_rows}" "${expected_namespace_uuid}" "${expected_namespace_fstype}" "shared" ||
      fail "Pre-existing Source namespace is not one exact shared mount."
  fi
  if ((slot_present == 1)); then
    validate_nas_slot_rows "${slot_rows}" "${authority_major_minor}" "shared" ||
      fail "Pre-existing NAS slot is not one exact shared mount."
    return 0
  fi

  if ((namespace_present == 0)); then
    mount --bind "${SOURCE_NAMESPACE}" "${SOURCE_NAMESPACE}" ||
      fail "Source namespace self-bind could not be created."
    created_namespace_mount=1
    require_namespace "any"
  fi

  mount --make-rprivate "${SOURCE_NAMESPACE}" ||
    fail "Source namespace could not be made private before slot creation."
  ((created_namespace_mount == 0)) && changed_preexisting_propagation=1
  require_namespace "private"

  if query_mountpoint "${NAS_SLOT}" "TARGET,SOURCE,FSTYPE,FSROOT,MAJ:MIN,PROPAGATION" slot_rows; then
    fail "NAS slot appeared before the controlled bind."
  else
    slot_status=$?
    ((slot_status == 1)) || fail "NAS slot pre-bind evidence is unavailable."
  fi

  mount --bind "${NAS_AUTHORITY}" "${NAS_SLOT}" ||
    fail "Exact NAS slot bind could not be created."
  created_nas_slot_mount=1
  require_nas_slot "any"

  mount --make-rshared "${SOURCE_NAMESPACE}" ||
    fail "Source namespace could not be made shared after slot validation."
  changed_preexisting_propagation=0
  require_namespace "shared"
  require_nas_slot "shared"
}

main() {
  local fixed_path authority_rows=""

  [[ "${EUID}" -eq 0 ]] ||
    fail "Source namespace preparation requires the approved root systemd unit."
  [[ -f "${CONFIG}" && ! -L "${CONFIG}" ]] ||
    fail "Protected Source-access configuration is missing or unsafe."
  for fixed_path in     "${SOURCE_NAMESPACE}" "${SOURCE_NAMESPACE}/local" "${SOURCE_NAMESPACE}/nas"     "${LOCAL_SLOT}" "${NAS_SLOT}" "${NAS_AUTHORITY}"; do
    [[ ! -L "${fixed_path}" ]] ||
      fail "Fixed Mounted Source path must not be a symbolic link: ${fixed_path}"
  done

  load_config_identity
  validate_local_backing ||
    fail "Local Mounted Source namespace does not match its configured filesystem identity."
  query_mountpoint "${NAS_AUTHORITY}" "TARGET,SOURCE,FSTYPE,FSROOT,MAJ:MIN,PROPAGATION" authority_rows ||
    fail "Authoritative NAS mount evidence is unavailable."
  validate_authority_rows "${authority_rows}" ||
    fail "Authoritative NAS identity is missing, duplicated, or conflicting."

  trap 'cleanup_on_exit "$?"' EXIT
  trap 'fail "Source namespace preparation was interrupted."' HUP INT TERM
  prepare_mount_topology
  operation_succeeded=1
  printf 'PASS: exact Mounted Source namespace and stable NAS slot are prepared.\n'
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  main "$@"
fi

