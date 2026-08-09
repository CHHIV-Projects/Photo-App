#!/usr/bin/env bash
set -Eeuo pipefail

readonly EXPECTED_REPOSITORY="/home/chuck/projects/photo-organizer-dev"
readonly BROKER_USER="photo-organizer-source-broker"
readonly SOCKET_GROUP="photo-organizer-source-access"
readonly PROGRAM_TARGET="/usr/local/lib/photo-organizer/source-identity-broker.py"
readonly NAMESPACE_PROGRAM_TARGET="/usr/local/lib/photo-organizer/prepare-source-namespace.sh"
readonly NAMESPACE_UNIT_TARGET="/etc/systemd/system/photo-organizer-source-namespace.service"
readonly CONFIG_TARGET="/etc/photo-organizer/source-access.json"
readonly UNIT_TARGET="/etc/systemd/system/photo-organizer-source-identity-broker.service"
readonly STATE_DIRECTORY="/var/lib/photo-organizer-source-access"
readonly ACCESS_NODE_ID_FILE="${STATE_DIRECTORY}/access-node-id"

script_directory="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repository_root="$(cd -- "${script_directory}/../../.." && pwd)"
readonly script_directory repository_root

fail() { printf 'FAIL: %s\n' "$*" >&2; exit 1; }
pass() { printf 'PASS: %s\n' "$*"; }

[[ "${repository_root}" == "${EXPECTED_REPOSITORY}" ]] || fail "Run the tracked installer from ${EXPECTED_REPOSITORY}."
[[ "${EUID}" -eq 0 ]] || fail "Product Owner must run this approved install action through interactive sudo."
[[ "${1:-}" == "install" && -n "${2:-}" ]] || fail "Usage: sudo $0 install EXISTING_SOURCE_DATA_READ_GROUP"
readonly DATA_READ_GROUP="$2"
getent group "${DATA_READ_GROUP}" >/dev/null || fail "The approved existing Source/NAS data-read group does not exist."
[[ -f "${CONFIG_TARGET}" ]] || fail "Protected configuration must be reviewed and installed at ${CONFIG_TARGET} first."
[[ ! -L "${CONFIG_TARGET}" ]] || fail "Protected configuration must not be a symbolic link."
for fixed_path in \
  /usr/local/lib/photo-organizer \
  /mnt/photo-organizer-sources \
  "${STATE_DIRECTORY}" \
  "${PROGRAM_TARGET}" \
  "${NAMESPACE_PROGRAM_TARGET}" \
  "${NAMESPACE_UNIT_TARGET}" \
  "${UNIT_TARGET}" \
  "${ACCESS_NODE_ID_FILE}"; do
  [[ ! -L "${fixed_path}" ]] || fail "Fixed installation target must not be a symbolic link: ${fixed_path}"
done
config_mode="$(stat -c '%a' -- "${CONFIG_TARGET}")"
(( (8#${config_mode} & 8#022) == 0 )) || fail "Protected configuration must not be group/world writable."
configured_data_group="$(python3 -c 'import json,sys; value=json.load(open(sys.argv[1], encoding="utf-8")).get("data_read_group"); print(value if isinstance(value,str) else "")' "${CONFIG_TARGET}")"
[[ "${configured_data_group}" == "${DATA_READ_GROUP}" ]] || fail "Installer data-read group does not match protected configuration."

getent group "${SOCKET_GROUP}" >/dev/null || groupadd --system "${SOCKET_GROUP}"
id -u "${BROKER_USER}" >/dev/null 2>&1 || useradd --system --no-create-home --home-dir "${STATE_DIRECTORY}" --shell /usr/sbin/nologin --gid "${SOCKET_GROUP}" "${BROKER_USER}"
[[ "$(id -gn "${BROKER_USER}")" == "${SOCKET_GROUP}" ]] ||
  fail "Existing broker user has an unexpected primary group."
usermod --append --groups "${DATA_READ_GROUP}" "${BROKER_USER}"
chown root:"${SOCKET_GROUP}" "${CONFIG_TARGET}"
chmod 0640 "${CONFIG_TARGET}"

install -d -o root -g root -m 0755 /usr/local/lib/photo-organizer
install -d -o root -g root -m 0755 /mnt/photo-organizer-sources
install -o root -g root -m 0755 "${script_directory}/source_identity_broker.py" "${PROGRAM_TARGET}"
install -o root -g root -m 0755 "${script_directory}/prepare_source_namespace.sh" "${NAMESPACE_PROGRAM_TARGET}"
install -o root -g root -m 0644 "${script_directory}/photo-organizer-source-namespace.service" "${NAMESPACE_UNIT_TARGET}"
install -o root -g root -m 0644 "${script_directory}/photo-organizer-source-identity-broker.service" "${UNIT_TARGET}"
install -d -o "${BROKER_USER}" -g "${SOCKET_GROUP}" -m 0750 "${STATE_DIRECTORY}"
if [[ ! -e "${ACCESS_NODE_ID_FILE}" ]]; then
  umask 0077
  tr -d '\n' < /proc/sys/kernel/random/uuid > "${ACCESS_NODE_ID_FILE}"
  printf '\n' >> "${ACCESS_NODE_ID_FILE}"
  chown "${BROKER_USER}:${SOCKET_GROUP}" "${ACCESS_NODE_ID_FILE}"
  chmod 0600 "${ACCESS_NODE_ID_FILE}"
fi
[[ -f "${ACCESS_NODE_ID_FILE}" && ! -L "${ACCESS_NODE_ID_FILE}" ]] || fail "Stable Access Node ID file is unsafe."
[[ "$(stat -c '%U|%G|%a' -- "${ACCESS_NODE_ID_FILE}")" == "${BROKER_USER}|${SOCKET_GROUP}|600" ]] ||
  fail "Stable Access Node ID ownership or permissions are unsafe."
systemctl daemon-reload

pass "additive broker files installed; service was not enabled or started"
printf 'NEXT: Record numeric GIDs without printing protected configuration: getent group %q; getent group %q\n' "${SOCKET_GROUP}" "${DATA_READ_GROUP}"
printf 'NEXT: Pause for Product Owner approval before enabling, starting, mounting, or recreating Development.\n'
