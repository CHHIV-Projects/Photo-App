#!/usr/bin/env bash
set -Eeuo pipefail

readonly CONFIG="/etc/photo-organizer/source-access.json"
readonly SOURCE_NAMESPACE="/mnt/photo-organizer-sources"
readonly LOCAL_SLOT="${SOURCE_NAMESPACE}/local/server-photos"
readonly NAS_SLOT="${SOURCE_NAMESPACE}/nas/photo-organizer"
readonly NAS_AUTHORITY="/mnt/nas/photo-organizer"
readonly NAS_SOURCE="//192.168.1.171/PhotoOrganizer"

fail() { printf 'FAIL: %s\n' "$*" >&2; exit 1; }

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
  local nas_rows slot_rows
  local -a local_identity

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
    mount --bind "${SOURCE_NAMESPACE}" "${SOURCE_NAMESPACE}"
  fi
  namespace_rows="$(findmnt -rn -M "${SOURCE_NAMESPACE}" -o TARGET,UUID,FSTYPE)"
  [[ "$(wc -l <<<"${namespace_rows}")" -eq 1 ]] ||
    fail "Source namespace mount identity is ambiguous."
  read -r namespace_target namespace_uuid namespace_fstype <<<"${namespace_rows}"
  [[ "${namespace_target}" == "${SOURCE_NAMESPACE}" ]] ||
    fail "Source namespace mount target is unexpected."
  [[ "${namespace_uuid,,}" == "${local_identity[0],,}" &&
    "${namespace_fstype,,}" == "${local_identity[1],,}" ]] ||
    fail "Source namespace does not match the protected Local filesystem identity."
  mount --make-rshared "${SOURCE_NAMESPACE}"

  nas_rows="$(findmnt -rn -T "${NAS_AUTHORITY}" -o TARGET,SOURCE,FSTYPE || true)"
  validate_exact_cifs_mount_rows "${NAS_AUTHORITY}" 1 <<<"${nas_rows}" ||
    fail "Authoritative NAS active mount identity is missing, conflicting, or unexpected."

  slot_rows="$(findmnt -rn -M "${NAS_SLOT}" -o TARGET,SOURCE,FSTYPE || true)"
  if [[ -z "${slot_rows}" ]]; then
    mount --bind "${NAS_AUTHORITY}" "${NAS_SLOT}"
    slot_rows="$(findmnt -rn -M "${NAS_SLOT}" -o TARGET,SOURCE,FSTYPE || true)"
  fi
  validate_exact_cifs_mount_rows "${NAS_SLOT}" 0 <<<"${slot_rows}" ||
    fail "NAS slot mount identity is missing, conflicting, or unexpected."
  printf 'PASS: fixed Source namespace and currently available stable slots are prepared.\n'
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  main "$@"
fi
