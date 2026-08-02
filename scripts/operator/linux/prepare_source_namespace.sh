#!/usr/bin/env bash
set -Eeuo pipefail

readonly CONFIG="/etc/photo-organizer/source-access.json"
readonly SOURCE_NAMESPACE="/mnt/photo-organizer-sources"
readonly LOCAL_SLOT="${SOURCE_NAMESPACE}/local/server-photos"
readonly NAS_SLOT="${SOURCE_NAMESPACE}/nas/photo-organizer"
readonly NAS_AUTHORITY="/mnt/nas/photo-organizer"
readonly NAS_SOURCE="//192.168.1.171/PhotoOrganizer"

fail() { printf 'FAIL: %s\n' "$*" >&2; exit 1; }
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

nas_row="$(findmnt -rn -T "${NAS_AUTHORITY}" -o TARGET,SOURCE,FSTYPE || true)"
if [[ -z "${nas_row}" ]]; then
  printf 'WARNING: authoritative NAS is unavailable; Local slot remains available and NAS will fail closed.\n'
  exit 0
fi
read -r nas_target nas_source nas_fstype <<<"${nas_row}"
if [[ "${nas_target}" != "${NAS_AUTHORITY}" || "${nas_source}" != "${NAS_SOURCE}" || "${nas_fstype}" != "cifs" ]]; then
  fail "Authoritative NAS active mount identity is unexpected."
fi
slot_row="$(findmnt -rn -M "${NAS_SLOT}" -o TARGET,SOURCE,FSTYPE || true)"
if [[ -z "${slot_row}" ]]; then
  mount --bind "${NAS_AUTHORITY}" "${NAS_SLOT}"
else
  read -r slot_target slot_source slot_fstype <<<"${slot_row}"
  [[ "${slot_target}" == "${NAS_SLOT}" && "${slot_source}" == "${NAS_SOURCE}" && "${slot_fstype}" == "cifs" ]] ||
    fail "Existing NAS slot mount has an unexpected identity."
fi
printf 'PASS: fixed Source namespace and currently available stable slots are prepared.\n'
