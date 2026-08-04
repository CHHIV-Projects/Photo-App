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
source_namespace_propagation_changed=0
source_namespace_original_propagation=""
source_namespace_expected_uuid=""
source_namespace_expected_fstype=""
operation_succeeded=0
current_namespace_rows=""
current_namespace_query_rc=0
current_namespace_row_count=0
current_slot_rows=""
current_slot_query_rc=0
current_slot_row_count=0
authority_major_minor=""

fail() { printf 'FAIL: %s\n' "$*" >&2; exit 1; }

reset_invocation_state() {
  created_source_namespace_mount=0
  created_nas_slot_mount=0
  source_namespace_propagation_changed=0
  source_namespace_original_propagation=""
  source_namespace_expected_uuid=""
  source_namespace_expected_fstype=""
  operation_succeeded=0
  current_namespace_rows=""
  current_namespace_query_rc=0
  current_namespace_row_count=0
  current_slot_rows=""
  current_slot_query_rc=0
  current_slot_row_count=0
  authority_major_minor=""
}

capture_source_namespace_rows() {
  local -a rows=()

  current_namespace_rows=""
  current_namespace_query_rc=0
  current_namespace_row_count=0
  if current_namespace_rows="$({
    findmnt \
      --kernel \
      --raw \
      --noheadings \
      --mountpoint "${SOURCE_NAMESPACE}" \
      --output TARGET,UUID,FSTYPE,PROPAGATION
  } 2>/dev/null)"; then
    current_namespace_query_rc=0
  else
    current_namespace_query_rc=$?
  fi

  if ((current_namespace_query_rc == 1)) &&
    [[ -z "${current_namespace_rows}" ]]; then
    return 10
  fi
  ((current_namespace_query_rc == 0)) || return 11
  [[ -n "${current_namespace_rows}" ]] || return 12
  mapfile -t rows <<<"${current_namespace_rows}"
  current_namespace_row_count="${#rows[@]}"
  return 0
}

validate_source_namespace_rows() {
  local expected_uuid="$1"
  local expected_fstype="$2"
  local expected_propagation="$3"
  local row target filesystem_uuid filesystem propagation extra
  local -a rows=()

  [[ -n "${current_namespace_rows}" ]] || return 20
  mapfile -t rows <<<"${current_namespace_rows}"
  (("${#rows[@]}" == 1)) || return 21

  row="${rows[0]}"
  target=""
  filesystem_uuid=""
  filesystem=""
  propagation=""
  extra=""
  read -r target filesystem_uuid filesystem propagation extra <<<"${row}"
  [[ -n "${target}" && -n "${filesystem_uuid}" &&
    -n "${filesystem}" && -n "${propagation}" &&
    -z "${extra}" ]] || return 20
  [[ "${target}" == "${SOURCE_NAMESPACE}" ]] || return 22
  [[ "${filesystem_uuid,,}" == "${expected_uuid,,}" &&
    "${filesystem,,}" == "${expected_fstype,,}" ]] || return 23
  if [[ "${expected_propagation}" != "any" ]]; then
    [[ "${propagation}" == "${expected_propagation}" ]] || return 24
  fi
  return 0
}

capture_nas_slot_rows() {
  local -a rows=()

  current_slot_rows=""
  current_slot_query_rc=0
  current_slot_row_count=0
  if current_slot_rows="$({
    findmnt \
      --kernel \
      --raw \
      --noheadings \
      --nofsroot \
      --mountpoint "${NAS_SLOT}" \
      --output TARGET,SOURCE,FSTYPE,FSROOT,MAJ:MIN,PROPAGATION
  } 2>/dev/null)"; then
    current_slot_query_rc=0
  else
    current_slot_query_rc=$?
  fi

  if ((current_slot_query_rc == 1)) && [[ -z "${current_slot_rows}" ]]; then
    return 10
  fi
  ((current_slot_query_rc == 0)) || return 11
  [[ -n "${current_slot_rows}" ]] || return 12
  mapfile -t rows <<<"${current_slot_rows}"
  current_slot_row_count="${#rows[@]}"
  return 0
}

validate_nas_slot_rows() {
  local rows_text="$1"
  local expected_major_minor="$2"
  local expected_propagation="$3"
  local row target source filesystem fsroot major_minor propagation extra
  local -a rows=()

  [[ -n "${rows_text}" ]] || return 30
  mapfile -t rows <<<"${rows_text}"
  (("${#rows[@]}" == 1)) || return 31

  row="${rows[0]}"
  target=""
  source=""
  filesystem=""
  fsroot=""
  major_minor=""
  propagation=""
  extra=""
  read -r \
    target \
    source \
    filesystem \
    fsroot \
    major_minor \
    propagation \
    extra \
    <<<"${row}"

  [[ -n "${target}" && -n "${source}" && -n "${filesystem}" &&
    -n "${fsroot}" && -n "${major_minor}" &&
    -n "${propagation}" && -z "${extra}" ]] || return 30
  [[ "${target}" == "${NAS_SLOT}" ]] || return 32
  [[ "${source}" == "${NAS_SOURCE}" ]] || return 33
  [[ "${filesystem}" == "cifs" ]] || return 34
  [[ "${fsroot}" == "/" ]] || return 35
  [[ "${major_minor}" =~ ^[0-9]+:[0-9]+$ ]] || return 36
  [[ "${major_minor}" == "${expected_major_minor}" ]] || return 37
  if [[ "${expected_propagation}" != "any" ]]; then
    [[ "${propagation}" == "${expected_propagation}" ]] || return 38
  fi
  return 0
}

extract_authoritative_nas_major_minor() {
  local rows_text="$1"
  local row target source filesystem fsroot major_minor propagation extra
  local active_count=0
  local autofs_count=0
  local -a rows=()

  authority_major_minor=""
  [[ -n "${rows_text}" ]] || return 1
  mapfile -t rows <<<"${rows_text}"

  for row in "${rows[@]}"; do
    target=""
    source=""
    filesystem=""
    fsroot=""
    major_minor=""
    propagation=""
    extra=""
    read -r \
      target \
      source \
      filesystem \
      fsroot \
      major_minor \
      propagation \
      extra \
      <<<"${row}"
    [[ -n "${target}" && -n "${source}" && -n "${filesystem}" &&
      -n "${fsroot}" && -n "${major_minor}" &&
      -n "${propagation}" && -z "${extra}" ]] || return 1
    [[ "${target}" == "${NAS_AUTHORITY}" ]] || return 1
    [[ "${fsroot}" == "/" &&
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
      source_namespace_propagation_changed=0
    else
      cleanup_failed=1
    fi
  fi

  if ((source_namespace_propagation_changed == 1)); then
    if ((created_source_namespace_mount == 1)); then
      printf 'FAIL: Cleanup could not restore propagation while the invocation-created Source namespace root remains mounted.\n' >&2
      cleanup_failed=1
    elif [[ "${source_namespace_original_propagation}" != "shared" ]]; then
      printf 'FAIL: Cleanup has no approved prior Source namespace propagation state to restore.\n' >&2
      cleanup_failed=1
    elif ! mount --make-rshared "${SOURCE_NAMESPACE}"; then
      printf 'FAIL: Cleanup could not restore shared propagation on the preexisting Source namespace root.\n' >&2
      cleanup_failed=1
    elif ! capture_source_namespace_rows ||
      ! validate_source_namespace_rows \
        "${source_namespace_expected_uuid}" \
        "${source_namespace_expected_fstype}" \
        "shared"; then
      printf 'FAIL: Cleanup could not verify restored shared propagation on the preexisting Source namespace root.\n' >&2
      cleanup_failed=1
    else
      source_namespace_propagation_changed=0
    fi
  fi

  ((cleanup_failed == 0))
}

cleanup_on_exit() {
  local original_status="$1"

  trap - EXIT HUP INT TERM
  if ((operation_succeeded == 0)) &&
    ((created_nas_slot_mount == 1 ||
      created_source_namespace_mount == 1 ||
      source_namespace_propagation_changed == 1)); then
    if ! rollback_invocation_mounts; then
      printf 'FAIL: Invocation-owned Source mount cleanup is incomplete; propagation restoration may also be incomplete; manual review is required.\n' >&2
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

report_namespace_validation_failure() {
  local status="$1"

  case "${status}" in
    20) fail "Source namespace mount evidence is malformed." ;;
    21) fail "Source namespace mount identity is ambiguous." ;;
    22) fail "Source namespace mount target is unexpected." ;;
    23) fail "Source namespace does not match the protected Local filesystem identity." ;;
    24) fail "Source namespace propagation is unexpected." ;;
    *) fail "Source namespace validation failed unexpectedly." ;;
  esac
}

require_source_namespace() {
  local expected_propagation="$1"
  local capture_status validation_status

  if capture_source_namespace_rows; then
    capture_status=0
  else
    capture_status=$?
  fi
  case "${capture_status}" in
    0) ;;
    10) fail "Source namespace mount is missing." ;;
    11) fail "Source namespace mount evidence query failed with return code ${current_namespace_query_rc}." ;;
    12) fail "Source namespace mount evidence query returned zero exact rows." ;;
    *) fail "Source namespace mount evidence query failed unexpectedly." ;;
  esac

  if validate_source_namespace_rows \
    "${source_namespace_expected_uuid}" \
    "${source_namespace_expected_fstype}" \
    "${expected_propagation}"; then
    validation_status=0
  else
    validation_status=$?
  fi
  ((validation_status == 0)) ||
    report_namespace_validation_failure "${validation_status}"
}

report_slot_validation_failure() {
  local stage="$1"
  local status="$2"

  case "${status}" in
    30) fail "NAS slot ${stage} evidence is malformed." ;;
    31)
      fail "NAS slot ${stage} evidence has duplicate or ambiguous exact rows (count=${current_slot_row_count})."
      ;;
    32) fail "NAS slot ${stage} target identity is unexpected." ;;
    33) fail "NAS slot ${stage} canonical source identity is unexpected." ;;
    34) fail "NAS slot ${stage} filesystem identity is unexpected." ;;
    35) fail "NAS slot ${stage} FSROOT identity is unexpected." ;;
    36) fail "NAS slot ${stage} MAJ:MIN evidence is empty or malformed." ;;
    37) fail "NAS slot ${stage} MAJ:MIN does not match the authoritative active CIFS mount." ;;
    38) fail "NAS slot ${stage} propagation is unexpected." ;;
    *) fail "NAS slot ${stage} validation failed unexpectedly." ;;
  esac
}

require_nas_slot() {
  local stage="$1"
  local expected_propagation="$2"
  local capture_status validation_status

  if capture_nas_slot_rows; then
    capture_status=0
  else
    capture_status=$?
  fi
  case "${capture_status}" in
    0) ;;
    10) fail "NAS slot ${stage} evidence is missing." ;;
    11) fail "NAS slot ${stage} evidence query failed with return code ${current_slot_query_rc}." ;;
    12) fail "NAS slot ${stage} evidence query returned zero exact rows." ;;
    *) fail "NAS slot ${stage} evidence query failed unexpectedly." ;;
  esac

  if validate_nas_slot_rows \
    "${current_slot_rows}" \
    "${authority_major_minor}" \
    "${expected_propagation}"; then
    validation_status=0
  else
    validation_status=$?
  fi
  ((validation_status == 0)) ||
    report_slot_validation_failure "${stage}" "${validation_status}"
}

prepare_mount_topology() {
  local expected_uuid="$1"
  local expected_fstype="$2"
  local expected_authority_major_minor="$3"
  local namespace_capture_status slot_capture_status
  local namespace_present=0
  local slot_present=0
  local validation_status

  source_namespace_expected_uuid="${expected_uuid}"
  source_namespace_expected_fstype="${expected_fstype}"
  authority_major_minor="${expected_authority_major_minor}"

  if capture_source_namespace_rows; then
    namespace_capture_status=0
  else
    namespace_capture_status=$?
  fi
  case "${namespace_capture_status}" in
    0) namespace_present=1 ;;
    10) namespace_present=0 ;;
    11) fail "Source namespace mount evidence query failed with return code ${current_namespace_query_rc}." ;;
    12) fail "Source namespace mount evidence query returned zero exact rows." ;;
    *) fail "Source namespace mount evidence query failed unexpectedly." ;;
  esac

  if capture_nas_slot_rows; then
    slot_capture_status=0
  else
    slot_capture_status=$?
  fi
  case "${slot_capture_status}" in
    0) slot_present=1 ;;
    10) slot_present=0 ;;
    11) fail "NAS slot initial evidence query failed with return code ${current_slot_query_rc}." ;;
    12) fail "NAS slot initial evidence query returned zero exact rows." ;;
    *) fail "NAS slot initial evidence query failed unexpectedly." ;;
  esac

  if ((namespace_present == 0 && slot_present == 1)); then
    fail "NAS slot exists without the exact Source namespace root mount."
  fi

  if ((namespace_present == 1)); then
    if validate_source_namespace_rows \
      "${expected_uuid}" \
      "${expected_fstype}" \
      "shared"; then
      validation_status=0
    else
      validation_status=$?
    fi
    ((validation_status == 0)) ||
      report_namespace_validation_failure "${validation_status}"
  fi

  if ((slot_present == 1)); then
    if validate_nas_slot_rows \
      "${current_slot_rows}" \
      "${authority_major_minor}" \
      "shared"; then
      validation_status=0
    else
      validation_status=$?
    fi
    ((validation_status == 0)) ||
      report_slot_validation_failure "existing" "${validation_status}"
    return 0
  fi

  if ((namespace_present == 0)); then
    created_source_namespace_mount=1
    if ! mount --bind "${SOURCE_NAMESPACE}" "${SOURCE_NAMESPACE}"; then
      fail "Source namespace self-bind could not be created."
    fi
    require_source_namespace "any"
  fi

  source_namespace_original_propagation=""
  if ((created_source_namespace_mount == 0)); then
    source_namespace_original_propagation="shared"
  fi
  source_namespace_propagation_changed=1
  if ! mount --make-rprivate "${SOURCE_NAMESPACE}"; then
    fail "Source namespace private propagation could not be established."
  fi
  require_source_namespace "private"

  if capture_nas_slot_rows; then
    fail "NAS slot appeared before the controlled bind operation."
  else
    slot_capture_status=$?
  fi
  case "${slot_capture_status}" in
    10) ;;
    11) fail "NAS slot pre-bind evidence query failed with return code ${current_slot_query_rc}." ;;
    12) fail "NAS slot pre-bind evidence query returned zero exact rows." ;;
    *) fail "NAS slot pre-bind state is ambiguous." ;;
  esac

  created_nas_slot_mount=1
  if ! mount --bind "${NAS_AUTHORITY}" "${NAS_SLOT}"; then
    fail "NAS slot bind could not be created."
  fi
  require_nas_slot "pre-share" "any"

  if ! mount --make-rshared "${SOURCE_NAMESPACE}"; then
    fail "Completed Source namespace shared propagation could not be established."
  fi
  source_namespace_propagation_changed=0

  require_source_namespace "shared"
  require_nas_slot "post-share" "shared"
  return 0
}

main() {
  local fixed_path data_read_group nas_rows authority_full_rows
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

  if ! nas_rows="$(findmnt -rn -T "${NAS_AUTHORITY}" -o TARGET,SOURCE,FSTYPE 2>/dev/null)"; then
    fail "Authoritative NAS mount evidence query failed."
  fi
  validate_exact_cifs_mount_rows "${NAS_AUTHORITY}" 1 <<<"${nas_rows}" ||
    fail "Authoritative NAS active mount identity is missing, conflicting, or unexpected."

  if ! authority_full_rows="$({
    findmnt \
      --kernel \
      --raw \
      --noheadings \
      --nofsroot \
      --mountpoint "${NAS_AUTHORITY}" \
      --output TARGET,SOURCE,FSTYPE,FSROOT,MAJ:MIN,PROPAGATION
  } 2>/dev/null)"; then
    fail "Authoritative NAS full mount evidence query failed."
  fi
  extract_authoritative_nas_major_minor "${authority_full_rows}" ||
    fail "Authoritative NAS full mount identity is missing, conflicting, or unexpected."

  prepare_mount_topology \
    "${local_identity[0]}" \
    "${local_identity[1]}" \
    "${authority_major_minor}"

  operation_succeeded=1
  printf 'PASS: fixed Source namespace and currently available stable slots are prepared.\n'
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  main "$@"
fi
