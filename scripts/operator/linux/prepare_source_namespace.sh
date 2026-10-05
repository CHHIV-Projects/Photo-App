#!/usr/bin/env bash
set -Eeuo pipefail

readonly CONFIG="/etc/photo-organizer/source-access.json"
readonly SOURCE_NAMESPACE="/mnt/photo-organizer-sources"
readonly LOCAL_SLOT="${SOURCE_NAMESPACE}/local/server-photos"

fail() { printf 'FAIL: %s\n' "$*" >&2; exit 1; }
transient_fail() { printf 'RETRY: %s\n' "$*" >&2; exit 75; }

query_mountpoint() {
  local target="$1" fields="$2"
  local -n result_ref="$3"
  local output status=0
  output="$(findmnt --kernel --raw --noheadings --nofsroot --mountpoint "${target}" --output "${fields}" 2>/dev/null)" || status=$?
  result_ref="${output}"
  if ((status == 0)) && [[ -n "${output}" ]]; then return 0; fi
  if ((status == 1)) && [[ -z "${output}" ]]; then return 1; fi
  return 2
}

query_mountinfo_record() {
  local target="$1"
  local -n result_ref="$2"
  local output status=0
  output="$(python3 - "${target}" <<'PY'
import re
import sys

target = sys.argv[1]


def decode_mountinfo_path(value: str) -> str:
    return re.sub(
        r"\\([0-7]{3})",
        lambda match: chr(int(match.group(1), 8)),
        value,
    )


with open("/proc/self/mountinfo", encoding="utf-8") as handle:
    for raw_line in handle:
        left, separator, _right = raw_line.rstrip("\n").partition(" - ")
        if not separator:
            raise SystemExit(2)
        fields = left.split()
        if len(fields) < 6 or decode_mountinfo_path(fields[4]) != target:
            continue
        propagation = [
            value
            for value in fields[6:]
            if value == "unbindable"
            or value.startswith(("shared:", "master:", "propagate_from:"))
        ]
        shared = [value.split(":", 1)[1] for value in propagation if value.startswith("shared:")]
        if len(shared) == 1 and len(propagation) == 1:
            mode = "shared"
            peer_group = shared[0]
        elif not propagation:
            mode = "private"
            peer_group = "-"
        else:
            mode = "other"
            peer_group = shared[0] if len(shared) == 1 else "-"
        print(fields[0], fields[1], peer_group, mode)
PY
  )" || status=$?
  result_ref="${output}"
  ((status == 0)) || return 2
  [[ -n "${output}" ]] || return 1
}

source_namespace_child_mount_count() {
  local -n result_ref="$1"
  local output status=0
  output="$(python3 - "${SOURCE_NAMESPACE}" <<'PY'
import re
import sys

namespace = sys.argv[1].rstrip("/")
prefix = namespace + "/"


def decode_mountinfo_path(value: str) -> str:
    return re.sub(
        r"\\([0-7]{3})",
        lambda match: chr(int(match.group(1), 8)),
        value,
    )


count = 0
with open("/proc/self/mountinfo", encoding="utf-8") as handle:
    for raw_line in handle:
        left, separator, _right = raw_line.rstrip("\n").partition(" - ")
        if not separator:
            raise SystemExit(2)
        fields = left.split()
        if len(fields) < 6:
            raise SystemExit(2)
        if decode_mountinfo_path(fields[4]).startswith(prefix):
            count += 1
print(count)
PY
  )" || status=$?
  ((status == 0)) || return 1
  [[ "${output}" =~ ^[0-9]+$ ]] || return 1
  result_ref="${output}"
}

load_base_identity() {
  local -a values=()
  mapfile -t values < <(python3 - "${CONFIG}" "${SOURCE_NAMESPACE}" "${LOCAL_SLOT}" <<'PY'
import json, sys
path, namespace, local_slot = sys.argv[1:]
data = json.load(open(path, encoding="utf-8"))
assert data.get("protocol_version") in {1, 2}
assert data.get("source_namespace") == namespace
locations = data.get("locations")
assert isinstance(locations, list) and 1 <= len(locations) <= 64
local = [item for item in locations if item.get("location_id") == "linux-local-server-photos"]
assert len(local) == 1 and local[0].get("source_type") == "local"
assert local[0].get("host_slot") == local_slot
for value in (local[0].get("filesystem_uuid"), local[0].get("filesystem_type"), data.get("data_read_group")):
    assert isinstance(value, str) and value and not value.startswith("REPLACE_")
print(local[0]["filesystem_uuid"])
print(local[0]["filesystem_type"])
print(data["data_read_group"])
PY
  ) || fail "Protected Source-access configuration is invalid."
  ((${#values[@]} == 3)) || fail "Protected Source-access base identity is incomplete."
  EXPECTED_NAMESPACE_UUID="${values[0]}"
  EXPECTED_NAMESPACE_FSTYPE="${values[1]}"
  DATA_READ_GROUP="${values[2]}"
  getent group "${DATA_READ_GROUP}" >/dev/null || fail "Approved Source data-read group does not exist."
}

load_nas_location() {
  local location_id="$1"
  local -a values=()
  [[ "${location_id}" =~ ^linux-nas-[a-z0-9-]{1,80}$ ]] || fail "NAS location ID is invalid."
  mapfile -t values < <(python3 - "${CONFIG}" "${location_id}" <<'PY'
import json, posixpath, re, sys
path, location_id = sys.argv[1:]
data = json.load(open(path, encoding="utf-8"))
locations = data.get("locations")
matches = [item for item in locations if item.get("location_id") == location_id] if isinstance(locations, list) else []
assert len(matches) == 1
item = matches[0]
assert item.get("source_type") == "nas" and item.get("filesystem_type") == "cifs"
host_slot = item.get("host_slot")
runtime_slot = item.get("runtime_slot")
authority = item.get("authoritative_target")
source = item.get("canonical_source")
assert isinstance(host_slot, str) and host_slot.startswith("/mnt/photo-organizer-sources/nas/")
assert isinstance(runtime_slot, str) and runtime_slot.startswith("/app/sources/nas/")
assert isinstance(authority, str) and (authority == "/mnt/nas/photo-organizer" or authority.startswith("/mnt/nas/photo-organizer-"))
assert all(posixpath.normpath(value) == value for value in (host_slot, runtime_slot, authority))
assert isinstance(source, str) and re.fullmatch(r"//[^/\\]+/[^/\\]+", source)
for value in (host_slot, runtime_slot, authority, source):
    print(value)
PY
  ) || fail "Protected NAS location configuration is invalid."
  ((${#values[@]} == 4)) || fail "Protected NAS location identity is incomplete."
  NAS_SLOT="${values[0]}"
  NAS_RUNTIME_SLOT="${values[1]}"
  NAS_AUTHORITY="${values[2]}"
  NAS_SOURCE="${values[3]}"
}

require_namespace_identity() {
  local rows row target uuid filesystem extra
  query_mountpoint "${SOURCE_NAMESPACE}" "TARGET,UUID,FSTYPE" rows || return 1
  [[ "$(wc -l <<<"${rows}")" == 1 ]] || return 1
  read -r target uuid filesystem extra <<<"${rows}"
  [[ "${target}" == "${SOURCE_NAMESPACE}" && -z "${extra:-}" ]] || return 1
  [[ "${uuid,,}" == "${EXPECTED_NAMESPACE_UUID,,}" ]] || return 1
  [[ "${filesystem,,}" == "${EXPECTED_NAMESPACE_FSTYPE,,}" ]]
}

classify_namespace_topology() {
  local root_rows namespace_rows
  local root_mount_id root_parent_id root_peer_group root_mode root_extra
  local namespace_mount_id namespace_parent_id namespace_peer_group namespace_mode namespace_extra
  query_mountinfo_record "/" root_rows || return 1
  query_mountinfo_record "${SOURCE_NAMESPACE}" namespace_rows || return 1
  [[ "$(wc -l <<<"${root_rows}")" == 1 && "$(wc -l <<<"${namespace_rows}")" == 1 ]] || return 1
  read -r root_mount_id root_parent_id root_peer_group root_mode root_extra <<<"${root_rows}"
  read -r namespace_mount_id namespace_parent_id namespace_peer_group namespace_mode namespace_extra <<<"${namespace_rows}"
  [[ -z "${root_extra:-}" && -z "${namespace_extra:-}" ]] || return 1
  [[ "${root_mount_id}" =~ ^[0-9]+$ && "${root_parent_id}" =~ ^[0-9]+$ ]] || return 1
  [[ "${namespace_mount_id}" =~ ^[0-9]+$ && "${namespace_parent_id}" =~ ^[0-9]+$ ]] || return 1
  [[ "${root_mode}" == "shared" && "${root_peer_group}" =~ ^[0-9]+$ ]] || return 1

  ROOT_MOUNT_ID="${root_mount_id}"
  ROOT_PEER_GROUP="${root_peer_group}"
  SOURCE_NAMESPACE_MOUNT_ID="${namespace_mount_id}"
  SOURCE_NAMESPACE_PEER_GROUP="${namespace_peer_group}"
  case "${namespace_mode}" in
    shared)
      [[ "${namespace_peer_group}" =~ ^[0-9]+$ ]] || return 1
      if [[ "${namespace_peer_group}" == "${root_peer_group}" ]]; then
        SOURCE_NAMESPACE_TOPOLOGY="inherited_shared"
      else
        SOURCE_NAMESPACE_TOPOLOGY="independent_shared"
      fi
      ;;
    private)
      [[ "${namespace_peer_group}" == "-" ]] || return 1
      SOURCE_NAMESPACE_TOPOLOGY="private"
      ;;
    *) return 1 ;;
  esac
}

require_namespace() {
  require_namespace_identity || return 1
  classify_namespace_topology || return 1
  [[ "${SOURCE_NAMESPACE_TOPOLOGY}" == "independent_shared" ]]
}

establish_independent_namespace_topology() {
  local child_mount_count
  NAMESPACE_TRANSITION_ERROR=""
  source_namespace_child_mount_count child_mount_count || {
    NAMESPACE_TRANSITION_ERROR="Source namespace child mount evidence is unavailable."
    return 1
  }
  if ((child_mount_count != 0)); then
    NAMESPACE_TRANSITION_ERROR="Source namespace propagation conversion is unsafe while child Source mounts are active."
    return 1
  fi
  mount --make-private "${SOURCE_NAMESPACE}" || {
    NAMESPACE_TRANSITION_ERROR="Source namespace detachment from inherited propagation failed."
    return 1
  }
  mount --make-shared "${SOURCE_NAMESPACE}" || {
    NAMESPACE_TRANSITION_ERROR="Source namespace independent shared propagation setup failed."
    return 1
  }
}

validate_local_backing() {
  local output uuid filesystem extra status=0
  output="$(findmnt --kernel --raw --noheadings --target "${LOCAL_SLOT}" --output UUID,FSTYPE 2>/dev/null)" || status=$?
  ((status == 0)) || return 1
  [[ "$(wc -l <<<"${output}")" == 1 ]] || return 1
  read -r uuid filesystem extra <<<"${output}"
  [[ -z "${extra:-}" && "${uuid,,}" == "${EXPECTED_NAMESPACE_UUID,,}" && "${filesystem,,}" == "${EXPECTED_NAMESPACE_FSTYPE,,}" ]]
}

prepare_base() {
  local rows status fixed_path created_namespace=false
  for fixed_path in "${SOURCE_NAMESPACE}" "${SOURCE_NAMESPACE}/local" "${SOURCE_NAMESPACE}/nas" "${LOCAL_SLOT}"; do
    [[ ! -L "${fixed_path}" ]] || fail "Fixed Source namespace path is a symbolic link."
  done
  install -d -o root -g root -m 0755 "${SOURCE_NAMESPACE}" "${SOURCE_NAMESPACE}/local" "${SOURCE_NAMESPACE}/nas"
  install -d -o root -g "${DATA_READ_GROUP}" -m 0750 "${LOCAL_SLOT}"
  if query_mountpoint "${SOURCE_NAMESPACE}" "TARGET,UUID,FSTYPE" rows; then
    require_namespace_identity || fail "Pre-existing Source namespace identity is invalid."
    classify_namespace_topology || fail "Pre-existing Source namespace propagation evidence is invalid."
  else
    status=$?
    ((status == 1)) || fail "Source namespace mount evidence is unavailable."
    mount --bind "${SOURCE_NAMESPACE}" "${SOURCE_NAMESPACE}" || fail "Source namespace self-bind failed."
    created_namespace=true
    require_namespace_identity || {
      umount -- "${SOURCE_NAMESPACE}" || true
      fail "Created Source namespace identity failed validation."
    }
    classify_namespace_topology || {
      umount -- "${SOURCE_NAMESPACE}" || true
      fail "Created Source namespace propagation evidence is invalid."
    }
  fi
  if [[ "${SOURCE_NAMESPACE_TOPOLOGY}" != "independent_shared" ]]; then
    establish_independent_namespace_topology || {
      if [[ "${created_namespace}" == "true" ]]; then
        umount -- "${SOURCE_NAMESPACE}" || true
      fi
      fail "${NAMESPACE_TRANSITION_ERROR}"
    }
  fi
  require_namespace || {
    if [[ "${created_namespace}" == "true" ]]; then
      umount -- "${SOURCE_NAMESPACE}" || true
    fi
    fail "Source namespace independent propagation validation failed."
  }
  validate_local_backing || fail "Local Source namespace identity is invalid."
  printf 'PASS: base Source namespace is exact and independently shared (root peer %s; Source peer %s).\n' \
    "${ROOT_PEER_GROUP}" "${SOURCE_NAMESPACE_PEER_GROUP}"
}

require_authority() {
  local allow_activation="${1:-yes}"
  local rows row target source filesystem fsroot major_minor propagation extra
  local active_count=0 autofs_count=0
  AUTHORITY_MAJOR_MINOR=""
  query_mountpoint "${NAS_AUTHORITY}" "TARGET,SOURCE,FSTYPE,FSROOT,MAJ:MIN,PROPAGATION" rows || transient_fail "NAS authority is unavailable."
  while IFS= read -r row; do
    [[ -n "${row}" ]] || continue
    read -r target source filesystem fsroot major_minor propagation extra <<<"${row}"
    [[ "${target}" == "${NAS_AUTHORITY}" && "${fsroot}" == "/" && -z "${extra:-}" ]] || fail "NAS authority evidence is malformed."
    if [[ "${filesystem}" == "autofs" && "${source}" == "systemd-1" ]]; then
      ((autofs_count += 1))
    elif [[ "${filesystem}" == "cifs" && "${source,,}" == "${NAS_SOURCE,,}" ]]; then
      ((active_count += 1))
      AUTHORITY_MAJOR_MINOR="${major_minor}"
    else
      fail "NAS authority identity conflicts with protected registration."
    fi
  done <<<"${rows}"
  ((active_count <= 1 && autofs_count <= 1)) || fail "NAS authority mount evidence is duplicated."
  if ((active_count == 0)); then
    ((autofs_count == 1)) || transient_fail "NAS authority is not configured."
    [[ "${allow_activation}" == "yes" ]] || transient_fail "NAS authority did not become active after the bounded automount attempt."
    timeout --foreground 30 find "${NAS_AUTHORITY}" -mindepth 1 -maxdepth 1 -print -quit >/dev/null 2>&1 || transient_fail "NAS automount did not become ready."
    require_authority no
    return
  fi
  [[ -n "${AUTHORITY_MAJOR_MINOR}" ]] || fail "NAS authority major/minor evidence is missing."
}

require_slot() {
  local rows row target source filesystem fsroot major_minor propagation extra
  query_mountpoint "${NAS_SLOT}" "TARGET,SOURCE,FSTYPE,FSROOT,MAJ:MIN,PROPAGATION" rows || return 1
  [[ "$(wc -l <<<"${rows}")" == 1 ]] || return 1
  read -r target source filesystem fsroot major_minor propagation extra <<<"${rows}"
  [[ "${target}" == "${NAS_SLOT}" && "${source,,}" == "${NAS_SOURCE,,}" && "${filesystem}" == "cifs" ]] || return 1
  [[ "${fsroot}" == "/" && "${major_minor}" == "${AUTHORITY_MAJOR_MINOR}" && "${propagation}" == "shared" && -z "${extra:-}" ]]
}

prepare_location() {
  local rows status
  require_namespace || fail "Base Source namespace is unavailable."
  require_authority
  if query_mountpoint "${NAS_SLOT}" "TARGET,SOURCE,FSTYPE,FSROOT,MAJ:MIN,PROPAGATION" rows; then
    require_slot || fail "Existing NAS namespace slot conflicts with protected registration."
    printf 'PASS: registered NAS location %s is already exact.\n' "${LOCATION_ID}"
    return
  else
    status=$?
    ((status == 1)) || fail "NAS namespace slot evidence is unavailable."
  fi
  [[ ! -L "${NAS_SLOT}" ]] || fail "NAS namespace slot is a symbolic link."
  install -d -o root -g root -m 0755 "${NAS_SLOT}"
  if query_mountpoint "${NAS_SLOT}" "TARGET,SOURCE,FSTYPE,FSROOT,MAJ:MIN,PROPAGATION" rows; then
    fail "NAS namespace slot appeared during preparation."
  else
    status=$?
    ((status == 1)) || fail "NAS namespace slot post-preparation evidence is unavailable."
  fi
  mount --bind "${NAS_AUTHORITY}" "${NAS_SLOT}" || fail "NAS namespace bind failed."
  mount --make-rshared "${SOURCE_NAMESPACE}" || {
    umount -- "${NAS_SLOT}" || true
    fail "NAS namespace propagation failed."
  }
  require_slot || {
    umount -- "${NAS_SLOT}" || true
    fail "Created NAS namespace slot failed exact validation."
  }
  printf 'PASS: registered NAS location %s is mounted and exact.\n' "${LOCATION_ID}"
}

main() {
  [[ "${EUID}" -eq 0 ]] || fail "Source namespace preparation requires the approved root systemd unit."
  [[ -f "${CONFIG}" && ! -L "${CONFIG}" ]] || fail "Protected Source-access configuration is missing or unsafe."
  load_base_identity
  case "${1:-}" in
    --base)
      [[ "$#" -eq 1 ]] || fail "Unexpected base namespace arguments."
      prepare_base
      ;;
    --location)
      [[ "$#" -eq 2 ]] || fail "Usage: prepare-source-namespace.sh --location LOCATION_ID"
      LOCATION_ID="$2"
      load_nas_location "${LOCATION_ID}"
      prepare_location
      ;;
    *) fail "Use --base or --location LOCATION_ID." ;;
  esac
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  main "$@"
fi
