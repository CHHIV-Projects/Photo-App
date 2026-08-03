#!/usr/bin/env bash
set -Eeuo pipefail

readonly CONFIG="/etc/photo-organizer/source-access.json"
readonly SOURCE_NAMESPACE="/mnt/photo-organizer-sources"
readonly LOCAL_SLOT="${SOURCE_NAMESPACE}/local/server-photos"
readonly NAS_SLOT="${SOURCE_NAMESPACE}/nas/photo-organizer"
readonly NAS_AUTHORITY="/mnt/nas/photo-organizer"
readonly NAS_SOURCE="//192.168.1.171/PhotoOrganizer"
readonly MAX_INVOCATION_CLEANUP_ATTEMPTS=16

created_source_namespace_mount=0
created_nas_slot_mount=0
operation_succeeded=0
source_slot_diagnostic_output=""
source_slot_diagnostic_rc=0
source_slot_diagnostic_row_count=0
current_slot_rows=""
current_slot_query_rc=0

fail() { printf 'FAIL: %s\n' "$*" >&2; exit 1; }

reset_invocation_state() {
  created_source_namespace_mount=0
  created_nas_slot_mount=0
  operation_succeeded=0
  source_slot_diagnostic_output=""
  source_slot_diagnostic_rc=0
  source_slot_diagnostic_row_count=0
  current_slot_rows=""
  current_slot_query_rc=0
}

emit_source_slot_diagnostic() {
  local output="$1"
  local query_rc="$2"
  local row target source filesystem fsroot major_minor propagation extra
  local malformed=0
  local -a rows=()

  if [[ -n "${output}" ]]; then
    mapfile -t rows <<<"${output}"
  fi
  source_slot_diagnostic_row_count="${#rows[@]}"

  printf 'SOURCE_SLOT_DIAGNOSTIC_RC=%s\n' "${query_rc}"
  printf 'SOURCE_SLOT_DIAGNOSTIC_ROW_COUNT=%s\n' "${source_slot_diagnostic_row_count}"
  for row in "${rows[@]}"; do
    target=""
    source=""
    filesystem=""
    fsroot=""
    major_minor=""
    propagation=""
    extra=""
    read -r target source filesystem fsroot major_minor propagation extra <<<"${row}"
    if [[ -z "${target}" || -z "${source}" || -z "${filesystem}" ||
      -z "${fsroot}" || -z "${major_minor}" || -z "${propagation}" ||
      -n "${extra}" ]]; then
      malformed=1
      continue
    fi
    printf 'SOURCE_SLOT_DIAGNOSTIC_ROW=%s %s %s %s %s %s\n' \
      "${target}" \
      "${source}" \
      "${filesystem}" \
      "${fsroot}" \
      "${major_minor}" \
      "${propagation}"
  done

  ((malformed == 0))
}

capture_source_slot_diagnostic() {
  local emit_status=0

  source_slot_diagnostic_output=""
  source_slot_diagnostic_rc=0
  source_slot_diagnostic_row_count=0
  if source_slot_diagnostic_output="$({
    findmnt \
      --kernel \
      --raw \
      --noheadings \
      --nofsroot \
      --mountpoint "${NAS_SLOT}" \
      --output TARGET,SOURCE,FSTYPE,FSROOT,MAJ:MIN,PROPAGATION
  } 2>/dev/null)"; then
    source_slot_diagnostic_rc=0
  else
    source_slot_diagnostic_rc=$?
  fi

  emit_source_slot_diagnostic \
    "${source_slot_diagnostic_output}" \
    "${source_slot_diagnostic_rc}" || emit_status=$?

  ((source_slot_diagnostic_rc == 0)) || return 11
  ((source_slot_diagnostic_row_count > 0)) || return 12
  ((emit_status == 0)) || return 13
}

query_current_slot_rows() {
  current_slot_rows=""
  current_slot_query_rc=0
  if current_slot_rows="$({
    findmnt -rn -M "${NAS_SLOT}" -o TARGET,SOURCE,FSTYPE
  } 2>/dev/null)"; then
    current_slot_query_rc=0
  else
    current_slot_query_rc=$?
  fi

  ((current_slot_query_rc == 0)) || return 11
  [[ -n "${current_slot_rows}" ]] || return 12
}

exact_mountpoint_is_present() {
  local target="$1"
  local output=""
  local query_rc=0
  local row

  if output="$({
    findmnt \
      --kernel \
      --raw \
      --noheadings \
      --mountpoint "${target}" \
      --output TARGET
  } 2>&1)"; then
    query_rc=0
  else
    query_rc=$?
  fi

  if ((query_rc == 1)) && [[ -z "${output}" ]]; then
    return 1
  fi
  if ((query_rc != 0)) || [[ -z "${output}" ]]; then
    printf 'FAIL: Cleanup could not determine exact mount state for %s.\n' "${target}" >&2
    return 2
  fi
  while IFS= read -r row || [[ -n "${row}" ]]; do
    if [[ "${row}" != "${target}" ]]; then
      printf 'FAIL: Cleanup received conflicting exact mount evidence for %s.\n' "${target}" >&2
      return 2
    fi
  done <<<"${output}"
  return 0
}

cleanup_created_mount() {
  local target="$1"
  local description="$2"
  local attempt presence_status

  for ((attempt = 1; attempt <= MAX_INVOCATION_CLEANUP_ATTEMPTS; attempt += 1)); do
    if exact_mountpoint_is_present "${target}"; then
      if ! umount -- "${target}"; then
        printf 'FAIL: Cleanup could not unmount invocation-created %s at %s.\n' \
          "${description}" "${target}" >&2
        return 1
      fi
    else
      presence_status=$?
      if ((presence_status == 1)); then
        printf 'CLEANUP: invocation-created %s is absent: %s\n' \
          "${description}" "${target}"
        return 0
      fi
      return 1
    fi
  done

  if exact_mountpoint_is_present "${target}"; then
    printf 'FAIL: Cleanup reached its bounded unmount limit for %s at %s.\n' \
      "${description}" "${target}" >&2
    return 1
  else
    presence_status=$?
    if ((presence_status == 1)); then
      printf 'CLEANUP: invocation-created %s is absent: %s\n' \
        "${description}" "${target}"
      return 0
    fi
  fi
  return 1
}

rollback_invocation_mounts() {
  local cleanup_failed=0

  if ((created_nas_slot_mount == 1)); then
    if cleanup_created_mount "${NAS_SLOT}" "NAS slot mount"; then
      created_nas_slot_mount=0
    else
      cleanup_failed=1
    fi
  fi

  if ((created_source_namespace_mount == 1)); then
    if ((created_nas_slot_mount == 1)); then
      printf 'FAIL: Cleanup retained the invocation-created Source namespace root because the NAS slot remains mounted.\n' >&2
      cleanup_failed=1
    elif cleanup_created_mount "${SOURCE_NAMESPACE}" "Source namespace root mount"; then
      created_source_namespace_mount=0
    else
      cleanup_failed=1
    fi
  fi

  ((cleanup_failed == 0))
}

cleanup_on_exit() {
  local original_status="$1"

  trap - EXIT HUP INT TERM
  if ((operation_succeeded == 0)) &&
    ((created_nas_slot_mount == 1 || created_source_namespace_mount == 1)); then
    if ! rollback_invocation_mounts; then
      printf 'FAIL: Invocation-owned Source mount cleanup is incomplete; manual review is required.\n' >&2
      ((original_status != 0)) || original_status=1
    fi
  fi
  exit "${original_status}"
}

on_signal() {
  local signal_name="$1"
  fail "Source namespace preparation was interrupted by ${signal_name}."
}

validate_exact_cifs_mount_rows() {
  local expected_target="$1"
  local allow_systemd_autofs="$2"
  local row target source filesystem extra
  local active_count=0
  local autofs_count=0
  local row_count=0

  while IFS= read -r row || [[ -n "${row}" ]]; do
    [[ -n "${row}" ]] || return 1
    target=""
    source=""
    filesystem=""
    extra=""
    read -r target source filesystem extra <<<"${row}"
    [[ -n "${target}" && -n "${source}" && -n "${filesystem}" && -z "${extra}" ]] || return 1
    [[ "${target}" == "${expected_target}" ]] || return 1
    ((row_count += 1))

    if [[ "${filesystem}" == "autofs" ]]; then
      [[ "${allow_systemd_autofs}" == "1" && "${source}" == "systemd-1" ]] || return 1
      ((autofs_count += 1))
      ((autofs_count == 1)) || return 1
    elif [[ "${filesystem}" == "cifs" ]]; then
      [[ "${source}" == "${NAS_SOURCE}" ]] || return 1
      ((active_count += 1))
      ((active_count == 1)) || return 1
    else
      return 1
    fi
  done

  ((row_count >= 1 && active_count == 1))
}

main() {
  local fixed_path data_read_group namespace_rows namespace_target namespace_uuid namespace_fstype
  local nas_rows slot_query_status diagnostic_status
  local -a local_identity

  reset_invocation_state
  trap 'cleanup_on_exit "$?"' EXIT
  trap 'on_signal HUP' HUP
  trap 'on_signal INT' INT
  trap 'on_signal TERM' TERM

  [[ "${EUID}" -eq 0 ]] || fail "Source namespace preparation requires the approved root systemd unit."
  [[ -f "${CONFIG}" && ! -L "${CONFIG}" ]] || fail "Protected Source-access configuration is missing or unsafe."
  for fixed_path in \
    "${SOURCE_NAMESPACE}" \
    "${SOURCE_NAMESPACE}/local" \
    "${SOURCE_NAMESPACE}/nas" \
    "${LOCAL_SLOT}" \
    "${NAS_SLOT}" \
    "${NAS_AUTHORITY}"; do
    [[ ! -L "${fixed_path}" ]] || fail "Fixed Source path must not be a symbolic link: ${fixed_path}"
  done

  data_read_group="$(python3 -c 'import json,sys; value=json.load(open(sys.argv[1], encoding="utf-8")).get("data_read_group"); print(value if isinstance(value,str) else "")' "${CONFIG}")"
  [[ -n "${data_read_group}" ]] || fail "Approved Source data-read group is missing from protected configuration."
  getent group "${data_read_group}" >/dev/null || fail "Approved Source data-read group does not exist."
  mapfile -t local_identity < <(
    python3 -c 'import json,sys; locations=json.load(open(sys.argv[1], encoding="utf-8")).get("locations", []); local=[item for item in locations if item.get("location_id") == "linux-local-server-photos"]; print(local[0].get("filesystem_uuid", "")); print(local[0].get("filesystem_type", ""))' "${CONFIG}"
  )
  [[ "${#local_identity[@]}" -eq 2 && -n "${local_identity[0]}" && -n "${local_identity[1]}" ]] ||
    fail "Protected Local filesystem identity is missing or ambiguous."

  install -d -o root -g root -m 0755 "${SOURCE_NAMESPACE}" "${SOURCE_NAMESPACE}/local" "${SOURCE_NAMESPACE}/nas"
  install -d -o root -g "${data_read_group}" -m 0750 "${LOCAL_SLOT}"
  install -d -o root -g root -m 0755 "${NAS_SLOT}"

  if ! mountpoint --quiet "${SOURCE_NAMESPACE}"; then
    if ! mount --bind "${SOURCE_NAMESPACE}" "${SOURCE_NAMESPACE}"; then
      fail "Source namespace self-bind could not be created."
    fi
    created_source_namespace_mount=1
  fi
  if ! namespace_rows="$(findmnt -rn -M "${SOURCE_NAMESPACE}" -o TARGET,UUID,FSTYPE 2>/dev/null)"; then
    fail "Source namespace mount evidence query failed."
  fi
  [[ "$(wc -l <<<"${namespace_rows}")" -eq 1 ]] ||
    fail "Source namespace mount identity is ambiguous."
  read -r namespace_target namespace_uuid namespace_fstype <<<"${namespace_rows}"
  [[ "${namespace_target}" == "${SOURCE_NAMESPACE}" ]] ||
    fail "Source namespace mount target is unexpected."
  [[ "${namespace_uuid,,}" == "${local_identity[0],,}" &&
    "${namespace_fstype,,}" == "${local_identity[1],,}" ]] ||
    fail "Source namespace does not match the protected Local filesystem identity."
  if ! mount --make-rshared "${SOURCE_NAMESPACE}"; then
    fail "Source namespace shared propagation could not be established."
  fi

  nas_rows="$(findmnt -rn -T "${NAS_AUTHORITY}" -o TARGET,SOURCE,FSTYPE || true)"
  validate_exact_cifs_mount_rows "${NAS_AUTHORITY}" 1 <<<"${nas_rows}" ||
    fail "Authoritative NAS active mount identity is missing, conflicting, or unexpected."

  if ! mountpoint --quiet "${NAS_SLOT}"; then
    if ! mount --bind "${NAS_AUTHORITY}" "${NAS_SLOT}"; then
      fail "NAS slot bind could not be created."
    fi
    created_nas_slot_mount=1

    if capture_source_slot_diagnostic; then
      diagnostic_status=0
    else
      diagnostic_status=$?
    fi
    case "${diagnostic_status}" in
      0) ;;
      11) fail "NAS slot diagnostic query failed with return code ${source_slot_diagnostic_rc}." ;;
      12) fail "NAS slot diagnostic query returned zero exact mount rows." ;;
      13) fail "NAS slot diagnostic query returned malformed sanitized evidence." ;;
      *) fail "NAS slot diagnostic query failed unexpectedly." ;;
    esac
  fi

  if query_current_slot_rows; then
    slot_query_status=0
  else
    slot_query_status=$?
  fi
  case "${slot_query_status}" in
    0) ;;
    11) fail "NAS slot mount evidence query failed with return code ${current_slot_query_rc}." ;;
    12) fail "NAS slot mount evidence query returned zero exact mount rows." ;;
    *) fail "NAS slot mount evidence query failed unexpectedly." ;;
  esac
  validate_exact_cifs_mount_rows "${NAS_SLOT}" 0 <<<"${current_slot_rows}" ||
    fail "NAS slot mount identity is missing, conflicting, or unexpected."
  printf 'PASS: fixed Source namespace and currently available stable slots are prepared.\n'
  operation_succeeded=1
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  main "$@"
fi
