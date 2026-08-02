#!/usr/bin/env python3
"""Non-root, allowlist-only Linux Source identity broker.

The broker speaks one bounded JSON object per line over an AF_UNIX socket. It
never mounts, writes Source data, calls Docker, or accepts a client path.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import posixpath
import secrets
import signal
import socket
import stat
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PROTOCOL_VERSION = 1
PROVIDER_NAME = "linux_stable_mount_v1"
PROVIDER_VERSION = "1"
MAX_MESSAGE_BYTES = 256 * 1024
COMMAND_TIMEOUT_SECONDS = 3.0
CANONICAL_NAS_SOURCE = "//192.168.1.171/PhotoOrganizer"
FINGERPRINT_PREFIX = "sha256:"
NAS_FINGERPRINT_VERSION = "source_endpoint_identity_v1"
LOCAL_FINGERPRINT_VERSION = "linux_filesystem_uuid_v1"
PATH_CHECK_PROGRAM = r"""
import json
import os
import posixpath
import sys

slot, selected = sys.argv[1:3]
normalized_slot = posixpath.normpath(slot)
real_slot = os.path.realpath(slot)
real_selected = os.path.realpath(selected)
try:
    contained = posixpath.commonpath([real_slot, real_selected]) == real_slot
except ValueError:
    contained = False
slot_stat = os.stat(slot)
print(json.dumps({
    "slot_is_exact": real_slot == normalized_slot,
    "selected_is_contained": contained,
    "selected_is_directory": os.path.isdir(selected),
    "selected_is_readable": os.access(selected, os.R_OK | os.X_OK),
    "slot_device": slot_stat.st_dev,
    "slot_inode": slot_stat.st_ino,
}, sort_keys=True, separators=(",", ":")))
"""


class BrokerError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: str


class CommandRunner:
    """Bounded, no-shell host command seam."""

    def run(self, argv: list[str]) -> CommandResult:
        try:
            completed = subprocess.run(
                argv,
                check=False,
                capture_output=True,
                text=True,
                timeout=COMMAND_TIMEOUT_SECONDS,
                env={"PATH": "/usr/sbin:/usr/bin:/sbin:/bin", "LC_ALL": "C"},
            )
        except subprocess.TimeoutExpired as exc:
            raise BrokerError("host_evidence_timeout", "Bounded host identity inspection timed out.") from exc
        except OSError as exc:
            raise BrokerError("host_evidence_unavailable", "Bounded host identity inspection is unavailable.") from exc
        return CommandResult(completed.returncode, completed.stdout)


class LinuxSourceIdentityBroker:
    def __init__(self, config: dict[str, Any], *, runner: CommandRunner | None = None) -> None:
        self._config = _validate_config(config)
        self._runner = runner or CommandRunner()
        self._locations = {item["location_id"]: item for item in self._config["locations"]}
        self._access_node = _access_node_evidence(self._config)

    def handle(self, request: dict[str, Any]) -> dict[str, Any]:
        if set(request) - {"protocol_version", "action", "location_id", "source_type", "relative_root"}:
            raise BrokerError("malformed_request", "Request contains unsupported fields.")
        if request.get("protocol_version") != PROTOCOL_VERSION:
            raise BrokerError("protocol_version_mismatch", "Unsupported broker protocol version.")
        action = request.get("action")
        if action == "list_locations":
            if set(request) != {"protocol_version", "action"}:
                raise BrokerError("malformed_request", "Location listing does not accept path input.")
            locations = [self._safe_listing(item) for item in self._locations.values()]
        elif action == "probe":
            location_id = request.get("location_id")
            if not isinstance(location_id, str) or location_id not in self._locations:
                raise BrokerError("location_not_allowlisted", "Linux Source location is not allowlisted.")
            source_type = request.get("source_type")
            location = self._locations[location_id]
            if source_type != location["source_type"]:
                raise BrokerError("source_type_mismatch", "Linux Source location type does not match.")
            relative_root = normalize_relative_root(request.get("relative_root"))
            locations = [self._probe_location(location, relative_root)]
        else:
            raise BrokerError("malformed_request", "Unsupported broker action.")
        return {
            "protocol_version": PROTOCOL_VERSION,
            "action": action,
            "provider_name": PROVIDER_NAME,
            "provider_version": PROVIDER_VERSION,
            "locations": locations,
            "blockers": [],
        }

    def _safe_listing(self, location: dict[str, Any]) -> dict[str, Any]:
        try:
            return self._probe_location(location, "", listing=True)
        except BrokerError as exc:
            return _location_response(
                location,
                self._access_node,
                status="blocked",
                status_message=exc.message,
                relative_root="",
                blockers=[{"code": exc.code, "message": exc.message}],
            )

    def _probe_location(
        self,
        location: dict[str, Any],
        relative_root: str,
        *,
        listing: bool = False,
    ) -> dict[str, Any]:
        mapping = derive_mapping(location, relative_root)
        self._verify_bounded_path(location, mapping["host_observed_path"])
        rows = self._findmnt_rows(mapping["host_observed_path"])
        row = _select_active_row(rows, mapping["host_observed_path"])
        if location["source_type"] == "local":
            mount = self._verify_local(location, row)
            boundary = "local_folder" if relative_root else "local_volume_root"
        else:
            mount = self._verify_nas(location, row)
            boundary = "nas_share_folder" if relative_root else "nas_share_root"
        self._verify_bounded_path(location, mapping["host_observed_path"])
        confirmed_row = _select_active_row(
            self._findmnt_rows(mapping["host_observed_path"]),
            mapping["host_observed_path"],
        )
        if confirmed_row != row:
            raise BrokerError("mount_evidence_changed", "Active mount evidence changed during verification.")
        if listing:
            mapping["host_observed_path"] = location["host_slot"]
            mapping["runtime_root"] = location["runtime_slot"]
        return _location_response(
            location,
            self._access_node,
            status="available",
            status_message="Configured Linux Source location is available and verified.",
            relative_root=relative_root,
            mapping=mapping,
            mount=mount,
            filesystem_boundary_type=boundary,
        )

    def _verify_bounded_path(self, location: dict[str, Any], selected: str) -> None:
        result = self._runner.run([
            "/usr/bin/python3",
            "-I",
            "-c",
            PATH_CHECK_PROGRAM,
            location["host_slot"],
            selected,
        ])
        if result.returncode != 0:
            raise BrokerError("source_path_unavailable", "Bounded Source path verification failed.")
        try:
            evidence = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise BrokerError("source_path_evidence_malformed", "Bounded Source path evidence is malformed.") from exc
        expected_fields = {
            "slot_is_exact",
            "selected_is_contained",
            "selected_is_directory",
            "selected_is_readable",
            "slot_device",
            "slot_inode",
        }
        if not isinstance(evidence, dict) or set(evidence) != expected_fields:
            raise BrokerError("source_path_evidence_malformed", "Bounded Source path evidence is malformed.")
        bool_fields = {
            "slot_is_exact",
            "selected_is_contained",
            "selected_is_directory",
            "selected_is_readable",
        }
        if any(not isinstance(evidence[field], bool) for field in bool_fields):
            raise BrokerError("source_path_evidence_malformed", "Bounded Source path evidence is malformed.")
        if not evidence["slot_is_exact"]:
            raise BrokerError(
                "slot_symlink_substitution",
                "Configured Linux Source slot is a symbolic-link substitution.",
            )
        if not evidence["selected_is_contained"]:
            raise BrokerError("symlink_escape", "Linux Source folder escapes through a symbolic link.")
        if not evidence["selected_is_directory"]:
            raise BrokerError("source_path_missing", "Configured Linux Source folder is unavailable.")
        if not evidence["selected_is_readable"]:
            raise BrokerError("source_path_unreadable", "Configured Linux Source folder is not readable.")
        if location["source_type"] == "local" and (
            evidence["slot_device"] != location["slot_device"]
            or evidence["slot_inode"] != location["slot_inode"]
        ):
            raise BrokerError("local_slot_root_substitution", "Configured Local slot root identity changed.")

    def _findmnt_rows(self, target: str) -> list[dict[str, str]]:
        result = self._runner.run(["findmnt", "--json", "--target", target, "--output", "TARGET,SOURCE,FSTYPE,MAJ:MIN"])
        if result.returncode != 0:
            raise BrokerError("mount_evidence_unavailable", "Active mount evidence is unavailable.")
        try:
            payload = json.loads(result.stdout)
            filesystems = payload.get("filesystems")
        except (json.JSONDecodeError, AttributeError) as exc:
            raise BrokerError("mount_evidence_malformed", "Active mount evidence is malformed.") from exc
        if not isinstance(filesystems, list) or not filesystems:
            raise BrokerError("mount_evidence_missing", "No active filesystem row covers the configured location.")
        rows: list[dict[str, str]] = []
        for item in filesystems:
            if not isinstance(item, dict):
                raise BrokerError("mount_evidence_malformed", "Active mount evidence is malformed.")
            rows.append({key: str(item.get(key, "")) for key in ("target", "source", "fstype", "maj:min")})
        return rows

    def _verify_local(self, location: dict[str, Any], row: dict[str, str]) -> dict[str, Any]:
        if row["fstype"].lower() != location["filesystem_type"].lower():
            raise BrokerError("local_filesystem_type_mismatch", "Configured Local filesystem type changed.")
        device = row["source"].split("[", 1)[0]
        result = self._runner.run(["lsblk", "--noheadings", "--output", "UUID", device])
        uuids = [line.strip() for line in result.stdout.splitlines() if line.strip()]
        if result.returncode != 0 or len(set(uuids)) != 1:
            raise BrokerError(
                "local_filesystem_uuid_ambiguous",
                "Strong Local filesystem UUID is missing or ambiguous.",
            )
        actual_uuid = uuids[0].casefold()
        if actual_uuid != location["filesystem_uuid"].casefold():
            raise BrokerError("local_filesystem_uuid_mismatch", "Configured Local filesystem identity changed.")
        duplicate_slots = [
            item["location_id"]
            for item in self._locations.values()
            if item["source_type"] == "local"
            and item["filesystem_uuid"].casefold() == actual_uuid
        ]
        if len(duplicate_slots) != 1:
            raise BrokerError(
                "local_filesystem_uuid_duplicate",
                "Strong Local filesystem identity is assigned to multiple slots.",
            )
        fingerprint = versioned_hash(LOCAL_FINGERPRINT_VERSION, ["filesystem_uuid", actual_uuid])
        return {
            "filesystem_type": row["fstype"].lower(),
            "mount_source_masked": _mask_mount_source(row["source"]),
            "major_minor": row["maj:min"],
            "filesystem_uuid_hash": fingerprint,
            "filesystem_uuid_masked": _mask_identifier(actual_uuid),
            "canonical_nas_source": None,
            "authoritative_mount_verified": True,
            "namespace_mapping_verified": True,
            "readable": True,
        }

    def _verify_nas(self, location: dict[str, Any], row: dict[str, str]) -> dict[str, Any]:
        if row["fstype"].lower() != "cifs":
            raise BrokerError("nas_filesystem_type_mismatch", "Configured NAS filesystem is not active CIFS.")
        canonical = _canonical_cifs_source(row["source"])
        if canonical != location["canonical_source"] or canonical != CANONICAL_NAS_SOURCE:
            raise BrokerError(
                "nas_source_mismatch",
                "Configured NAS source does not match the approved canonical share.",
            )
        authoritative_rows = self._findmnt_rows(location["authoritative_target"])
        authoritative = _select_active_row(authoritative_rows, location["authoritative_target"])
        if authoritative["fstype"].lower() != "cifs" or _canonical_cifs_source(authoritative["source"]) != canonical:
            raise BrokerError(
                "nas_authoritative_mount_mismatch",
                "NAS stable slot does not match its authoritative active mount.",
            )
        if authoritative["maj:min"] != row["maj:min"]:
            raise BrokerError(
                "nas_mount_identity_mismatch",
                "NAS stable slot and authoritative mount identities differ.",
            )
        fingerprint = versioned_hash(NAS_FINGERPRINT_VERSION, ["nas", "192.168.1.171", "photoorganizer"])
        return {
            "filesystem_type": "cifs",
            "mount_source_masked": canonical,
            "major_minor": row["maj:min"],
            "filesystem_uuid_hash": None,
            "filesystem_uuid_masked": None,
            "canonical_nas_source": canonical,
            "authoritative_mount_verified": True,
            "namespace_mapping_verified": True,
            "readable": True,
            "_identity_fingerprint_hash": fingerprint,
        }


def normalize_relative_root(value: Any) -> str:
    if value is None or value == "":
        return ""
    if not isinstance(value, str) or "\x00" in value:
        raise BrokerError("relative_root_invalid", "Relative Source folder is invalid.")
    raw = value.strip().replace("\\", "/")
    if not raw or raw == ".":
        return ""
    if raw.startswith("/") or any(part in {"", ".", ".."} for part in raw.split("/")):
        raise BrokerError("relative_root_traversal", "Relative Source folder is not safely contained.")
    normalized = posixpath.normpath(raw)
    if normalized == ".." or normalized.startswith("../"):
        raise BrokerError("relative_root_traversal", "Relative Source folder is not safely contained.")
    return normalized


def derive_mapping(location: dict[str, Any], relative_root: str) -> dict[str, str]:
    host_slot = posixpath.normpath(location["host_slot"])
    runtime_slot = posixpath.normpath(location["runtime_slot"])
    host_path = posixpath.join(host_slot, relative_root) if relative_root else host_slot
    runtime_root = posixpath.join(runtime_slot, relative_root) if relative_root else runtime_slot
    if posixpath.commonpath([host_slot, host_path]) != host_slot:
        raise BrokerError("host_path_escape", "Host Source folder escapes its configured slot.")
    if posixpath.commonpath([runtime_slot, runtime_root]) != runtime_slot:
        raise BrokerError("runtime_path_escape", "Runtime Source folder escapes its configured slot.")
    return {"host_observed_path": host_path, "runtime_root": runtime_root}


def versioned_hash(version: str, parts: list[str]) -> str:
    payload = json.dumps({"version": version, "parts": parts}, sort_keys=True, separators=(",", ":"))
    return FINGERPRINT_PREFIX + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _access_node_evidence(config: dict[str, Any]) -> dict[str, Any]:
    stable_id = Path(config["access_node_id_file"]).read_text(encoding="utf-8").strip()
    if not stable_id or len(stable_id) > 256:
        raise BrokerError("access_node_identity_invalid", "Stable Linux Access Node identity is unavailable.")
    digest = FINGERPRINT_PREFIX + hashlib.sha256(("linux-access-node-v1:" + stable_id).encode()).hexdigest()
    return {
        "access_node_id": "linux-access-node:" + digest.removeprefix(FINGERPRINT_PREFIX)[:44],
        "label": config["access_node_label"],
        "os_family": "linux",
        "host_fingerprint_hash": digest,
        "host_fingerprint_masked": "sha256:…" + digest[-12:],
        "capabilities": {"stable_mount_local": True, "stable_mount_nas": True},
    }


def _validate_config(config: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(config, dict) or config.get("protocol_version") != PROTOCOL_VERSION:
        raise BrokerError("configuration_invalid", "Broker configuration version is invalid.")
    allowed = {
        "protocol_version",
        "access_node_label",
        "access_node_id_file",
        "source_namespace",
        "data_read_group",
        "locations",
    }
    if set(config) != allowed or config.get("access_node_label") != "henderson-server1":
        raise BrokerError("configuration_invalid", "Broker configuration fields are invalid.")
    if not isinstance(config.get("data_read_group"), str) or not config["data_read_group"].strip():
        raise BrokerError("configuration_invalid", "Approved Source data-read group is missing.")
    if config.get("source_namespace") != "/mnt/photo-organizer-sources":
        raise BrokerError("configuration_invalid", "Broker Source namespace is not approved.")
    locations = config.get("locations")
    if not isinstance(locations, list) or not locations or len(locations) > 64:
        raise BrokerError("configuration_invalid", "Broker location allowlist is missing or exceeds its safe bound.")
    ids: set[str] = set()
    for item in locations:
        common = {"location_id", "source_type", "display_name", "host_slot", "runtime_slot", "filesystem_type"}
        if not isinstance(item, dict) or not common.issubset(item):
            raise BrokerError("configuration_invalid", "Broker location configuration is invalid.")
        if item["location_id"] in ids:
            raise BrokerError("configuration_invalid", "Broker location identity is duplicated.")
        ids.add(item["location_id"])
        expected_host_prefix = "/mnt/photo-organizer-sources/" + item["source_type"] + "/"
        expected_runtime_prefix = "/app/sources/" + item["source_type"] + "/"
        host_slot = str(item["host_slot"])
        runtime_slot = str(item["runtime_slot"])
        if (
            not host_slot.startswith(expected_host_prefix)
            or not runtime_slot.startswith(expected_runtime_prefix)
            or posixpath.normpath(host_slot) != host_slot
            or posixpath.normpath(runtime_slot) != runtime_slot
        ):
            raise BrokerError("configuration_invalid", "Broker location is outside the fixed Source namespace.")
        if item["source_type"] == "local":
            if (
                set(item) != common | {"filesystem_uuid", "slot_device", "slot_inode"}
                or not item["filesystem_uuid"]
                or not isinstance(item["slot_device"], int)
                or not isinstance(item["slot_inode"], int)
                or item["slot_device"] <= 0
                or item["slot_inode"] <= 0
            ):
                raise BrokerError("configuration_invalid", "Local location requires one strong filesystem UUID.")
        elif item["source_type"] == "nas":
            if set(item) != common | {"canonical_source", "authoritative_target"}:
                raise BrokerError("configuration_invalid", "NAS location configuration is invalid.")
            if item["canonical_source"] != CANONICAL_NAS_SOURCE or item["filesystem_type"] != "cifs":
                raise BrokerError("configuration_invalid", "NAS location is not the approved canonical CIFS share.")
        else:
            raise BrokerError("configuration_invalid", "Only Local and NAS locations are implemented.")
    return config


def _select_active_row(rows: list[dict[str, str]], target: str) -> dict[str, str]:
    active = [row for row in rows if row["fstype"].lower() not in {"autofs", "systemd-1"}]
    if len(active) != 1:
        raise BrokerError("mount_evidence_ambiguous", "Active mount evidence is missing or conflicting.")
    if not target.startswith(active[0]["target"].rstrip("/") + "/") and target != active[0]["target"]:
        raise BrokerError("mount_target_mismatch", "Active mount target does not contain the configured location.")
    return active[0]


def _canonical_cifs_source(source: str) -> str:
    return source.split("[", 1)[0].rstrip("/")


def _mask_mount_source(source: str) -> str:
    if source.startswith("//"):
        return _canonical_cifs_source(source)
    return "/dev/…/" + Path(source.split("[", 1)[0]).name


def _mask_identifier(value: str) -> str:
    compact = value.replace("-", "")
    return "…" + compact[-8:] if compact else "unavailable"


def _location_response(
    location: dict[str, Any],
    access_node: dict[str, Any],
    *,
    status: str,
    status_message: str,
    relative_root: str,
    mapping: dict[str, str] | None = None,
    mount: dict[str, Any] | None = None,
    filesystem_boundary_type: str | None = None,
    blockers: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    mapping = mapping or {}
    fingerprint = None
    fingerprint_version = None
    identifier_type = None
    identifier_masked = None
    if mount and location["source_type"] == "local":
        fingerprint = mount["filesystem_uuid_hash"]
        fingerprint_version = LOCAL_FINGERPRINT_VERSION
        identifier_type = "linux_filesystem_uuid"
        identifier_masked = mount["filesystem_uuid_masked"]
    elif mount and location["source_type"] == "nas":
        fingerprint = mount.pop("_identity_fingerprint_hash")
        fingerprint_version = NAS_FINGERPRINT_VERSION
        identifier_type = "nas_server_share"
        identifier_masked = CANONICAL_NAS_SOURCE
    return {
        "location_id": location["location_id"],
        "source_type": location["source_type"],
        "display_name": location["display_name"],
        "status": status,
        "status_message": status_message,
        "host_slot": location["host_slot"],
        "host_observed_path": mapping.get("host_observed_path"),
        "runtime_slot": location["runtime_slot"],
        "runtime_root": mapping.get("runtime_root"),
        "relative_root": relative_root,
        "filesystem_boundary_type": filesystem_boundary_type
        or ("local_volume_root" if location["source_type"] == "local" else "nas_share_root"),
        "identity_fingerprint_hash": fingerprint,
        "identity_fingerprint_version": fingerprint_version,
        "identity_identifier_type": identifier_type,
        "identity_identifier_masked": identifier_masked,
        "access_node": access_node,
        "mount": mount,
        "blockers": blockers or [],
        "warnings": [],
    }


def _read_request(connection: socket.socket) -> dict[str, Any]:
    raw = b""
    while b"\n" not in raw:
        chunk = connection.recv(min(65536, MAX_MESSAGE_BYTES + 1 - len(raw)))
        if not chunk:
            break
        raw += chunk
        if len(raw) > MAX_MESSAGE_BYTES:
            raise BrokerError("request_too_large", "Broker request exceeds the safe size limit.")
    line = raw.split(b"\n", 1)[0]
    try:
        value = json.loads(line.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BrokerError("malformed_request", "Broker request is not valid JSON.") from exc
    if not isinstance(value, dict):
        raise BrokerError("malformed_request", "Broker request must be a JSON object.")
    return value


def serve(config_path: Path, socket_path: Path) -> None:
    if os.geteuid() == 0:
        raise SystemExit("Refusing to run Linux Source identity broker as root.")
    config = json.loads(config_path.read_text(encoding="utf-8"))
    broker = LinuxSourceIdentityBroker(config)
    socket_path.parent.mkdir(mode=0o750, parents=True, exist_ok=True)
    if socket_path.exists():
        if not stat.S_ISSOCK(socket_path.lstat().st_mode):
            raise SystemExit("Refusing to replace a non-socket broker path.")
        socket_path.unlink()
    stop = False

    def request_stop(_signum: int, _frame: Any) -> None:
        nonlocal stop
        stop = True

    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as listener:
        listener.bind(str(socket_path))
        os.chmod(socket_path, 0o660)
        listener.listen(8)
        listener.settimeout(1.0)
        while not stop:
            try:
                connection, _ = listener.accept()
            except socket.timeout:
                continue
            with connection:
                connection.settimeout(5.0)
                try:
                    response = broker.handle(_read_request(connection))
                except BrokerError as exc:
                    response = {
                        "protocol_version": PROTOCOL_VERSION,
                        "action": "probe",
                        "provider_name": PROVIDER_NAME,
                        "provider_version": PROVIDER_VERSION,
                        "locations": [],
                        "blockers": [{"code": exc.code, "message": exc.message}],
                    }
                except Exception:
                    response = {
                        "protocol_version": PROTOCOL_VERSION,
                        "action": "probe",
                        "provider_name": PROVIDER_NAME,
                        "provider_version": PROVIDER_VERSION,
                        "locations": [],
                        "blockers": [{
                            "code": "broker_internal_error",
                            "message": "Linux Source identity verification failed safely.",
                        }],
                    }
                encoded = json.dumps(response, sort_keys=True, separators=(",", ":")).encode() + b"\n"
                if len(encoded) > MAX_MESSAGE_BYTES:
                    encoded = json.dumps({
                        "protocol_version": PROTOCOL_VERSION,
                        "action": "probe",
                        "provider_name": PROVIDER_NAME,
                        "provider_version": PROVIDER_VERSION,
                        "locations": [],
                        "blockers": [{
                            "code": "response_too_large",
                            "message": "Broker response exceeded its safe size limit.",
                        }],
                    }, sort_keys=True, separators=(",", ":")).encode() + b"\n"
                try:
                    connection.sendall(encoded)
                except OSError:
                    continue
    socket_path.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Photo Organizer Linux Source identity broker")
    parser.add_argument("--config", default="/etc/photo-organizer/source-access.json")
    parser.add_argument("--socket", default="/run/photo-organizer-source-access/broker.sock")
    args = parser.parse_args()
    serve(Path(args.config), Path(args.socket))


if __name__ == "__main__":
    main()
