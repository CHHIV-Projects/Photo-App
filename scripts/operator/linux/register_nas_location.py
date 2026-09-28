#!/usr/bin/env python3
"""Root-owned operator tool for bounded generalized NAS registration."""

from __future__ import annotations

import argparse
import getpass
import grp
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import socket
import stat
import struct
import subprocess
import tempfile
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import UUID, NAMESPACE_URL, uuid5


API_BASE = "http://127.0.0.1:18001"
SOURCE_CONFIG = Path("/etc/photo-organizer/source-access.json")
NAS_REGISTRY = Path("/etc/photo-organizer/nas-registrations.json")
CREDENTIAL_DIRECTORY = Path("/etc/samba/credentials")
UNIT_DIRECTORY = Path("/etc/systemd/system")
NAMESPACE_UNIT = "photo-organizer-source-namespace.service"
BROKER_UNIT = "photo-organizer-source-identity-broker.service"
NAS_TEMPLATE_UNIT = "photo-organizer-source-nas@.service"
LEGACY_LOCATION_ID = "linux-nas-photo-organizer"
LEGACY_APPLIANCE_ID = str(uuid5(NAMESPACE_URL, "photo-organizer:nas-appliance:linux-nas-photo-organizer"))
LEGACY_SHARE_ID = str(uuid5(NAMESPACE_URL, "photo-organizer:nas-share:linux-nas-photo-organizer"))
LEGACY_FINGERPRINT = "sha256:39da4b1667b654e2e3f7efd6ce59a319b29e23c9814871f67747249181505cb3"
HASH_RE = re.compile(r"sha256:[0-9a-f]{64}")
LOCATION_RE = re.compile(r"linux-nas-[a-z0-9-]{1,80}")
SHARE_RE = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9._-]{0,126}[A-Za-z0-9._-])?")


class InstallFailure(RuntimeError):
    pass


def fail(message: str) -> None:
    raise InstallFailure(message)


def run(argv: list[str], *, timeout: int = 30, check: bool = True) -> subprocess.CompletedProcess[str]:
    try:
        result = subprocess.run(
            argv,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
            env={"PATH": "/usr/sbin:/usr/bin:/sbin:/bin", "LC_ALL": "C"},
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        fail("A bounded host command was unavailable or timed out.")
    if check and result.returncode != 0:
        fail("A bounded host command failed.")
    return result


def require_root() -> None:
    if os.geteuid() != 0:
        fail("Product Owner must run this tool through interactive sudo.")


def require_safe_file(path: Path, *, mode: int, group: int = 0) -> None:
    item = os.lstat(path)
    if (
        not stat.S_ISREG(item.st_mode)
        or stat.S_ISLNK(item.st_mode)
        or item.st_uid != 0
        or item.st_gid != group
        or stat.S_IMODE(item.st_mode) != mode
    ):
        fail("Protected host file metadata is unsafe.")


def atomic_json(path: Path, value: dict[str, Any], *, mode: int, gid: int) -> None:
    path.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent, text=True)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(value, stream, sort_keys=True, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.chown(temporary, 0, gid)
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def atomic_text(path: Path, value: str, *, mode: int, gid: int = 0) -> None:
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent, text=True)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(value)
            stream.flush()
            os.fsync(stream.fileno())
        os.chown(temporary, 0, gid)
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def recv_exact(connection: socket.socket, size: int) -> bytes:
    value = b""
    while len(value) < size:
        chunk = connection.recv(size - len(value))
        if not chunk:
            fail("SMB peer closed the identity response.")
        value += chunk
    return value


def smb_server_guid_hash(host: str) -> tuple[str, str]:
    results: list[bytes] = []
    for _attempt in range(2):
        dialects = (0x0202, 0x0210, 0x0300, 0x0302)
        client_guid = secrets.token_bytes(16)
        header = struct.pack(
            "<4sHHIHHIIQIIQ16s",
            b"\xfeSMB", 64, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, b"\x00" * 16,
        )
        body = struct.pack("<HHHHI16sQ", 36, len(dialects), 1, 0, 0, client_guid, 0)
        body += b"".join(struct.pack("<H", value) for value in dialects)
        request = header + body
        try:
            with socket.create_connection((host, 445), timeout=3) as connection:
                connection.settimeout(3)
                connection.sendall(bytes((0,)) + len(request).to_bytes(3, "big") + request)
                prefix = recv_exact(connection, 4)
                size = int.from_bytes(prefix[1:], "big")
                if prefix[0] != 0 or size < 128 or size > 1024 * 1024:
                    fail("SMB identity response framing is invalid.")
                response = recv_exact(connection, size)
        except (OSError, TimeoutError) as exc:
            raise InstallFailure("NAS SMB identity is unavailable.") from exc
        if (
            response[:4] != b"\xfeSMB"
            or struct.unpack_from("<I", response, 8)[0] != 0
            or struct.unpack_from("<H", response, 12)[0] != 0
            or not struct.unpack_from("<I", response, 16)[0] & 1
            or struct.unpack_from("<H", response, 64)[0] != 65
        ):
            fail("NAS SMB identity response is invalid.")
        guid = response[72:88]
        if len(guid) != 16 or guid == b"\x00" * 16:
            fail("NAS SMB ServerGuid is missing.")
        results.append(guid)
    if results[0] != results[1]:
        fail("NAS SMB identity is inconsistent.")
    digest = hashlib.sha256(results[0]).hexdigest()
    return "sha256:" + digest, "sha256:…" + digest[-12:]


def fetch_json(path: str, *, method: str = "GET") -> dict[str, Any]:
    request = Request(API_BASE + path, method=method, headers={"Accept": "application/json"})
    try:
        with urlopen(request, timeout=10) as response:
            payload = json.load(response)
    except (HTTPError, URLError, TimeoutError, ValueError) as exc:
        raise InstallFailure("Photo Organizer registration API request failed.") from exc
    if not isinstance(payload, dict):
        fail("Photo Organizer registration API response is malformed.")
    return payload


def complete_registration_with_retry(registration_id: UUID) -> None:
    """Allow the restarted broker a bounded interval to publish its socket."""

    for attempt in range(10):
        try:
            fetch_json(f"/api/admin/nas-registrations/pending/{registration_id}/complete", method="POST")
            return
        except InstallFailure:
            if attempt == 9:
                raise
            time.sleep(1)


def require_namespace_instance_ready(instance: str) -> None:
    """Require one namespace instance to have completed before API finalization."""

    result = run(
        [
            "systemctl",
            "show",
            instance,
            "--property=ActiveState",
            "--property=SubState",
            "--property=Result",
            "--property=ExecMainStatus",
        ],
        check=False,
    )
    properties: dict[str, str] = {}
    for line in result.stdout.splitlines():
        key, separator, value = line.partition("=")
        if separator:
            properties[key] = value
    expected = {
        "ActiveState": "active",
        "SubState": "exited",
        "Result": "success",
        "ExecMainStatus": "0",
    }
    if result.returncode != 0 or properties != expected:
        fail("NAS namespace location did not activate safely.")


def load_source_config() -> tuple[dict[str, Any], int]:
    group_id = grp.getgrnam("photo-organizer-source-access").gr_gid
    require_safe_file(SOURCE_CONFIG, mode=0o640, group=group_id)
    value = json.loads(SOURCE_CONFIG.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or not isinstance(value.get("locations"), list):
        fail("Protected Source-access configuration is malformed.")
    return value, group_id


def load_registry() -> dict[str, Any]:
    if not NAS_REGISTRY.exists():
        return {"schema_version": 1, "appliances": []}
    require_safe_file(NAS_REGISTRY, mode=0o600)
    value = json.loads(NAS_REGISTRY.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("schema_version") != 1 or not isinstance(value.get("appliances"), list):
        fail("Protected NAS registry is malformed.")
    return value


def validate_manifest(value: dict[str, Any], registration_id: UUID) -> dict[str, str]:
    required = {
        "schema_version", "registration_id", "proposed_appliance_id", "proposed_share_id",
        "operation",
        "requested_host", "appliance_name", "share_name", "location_name", "location_id",
        "server_guid_hash", "server_guid_masked", "identity_fingerprint_hash",
        "identity_fingerprint_version", "request_digest", "expires_at",
    }
    if set(value) != required or value.get("schema_version") != 1:
        fail("Installer manifest fields are invalid.")
    if UUID(str(value["registration_id"])) != registration_id:
        fail("Installer manifest registration identity changed.")
    if value.get("operation") not in {"create_share", "update_network_host"}:
        fail("Installer manifest operation is invalid.")
    appliance_id = UUID(str(value["proposed_appliance_id"]))
    share_id = UUID(str(value["proposed_share_id"]))
    location_id = str(value["location_id"])
    if location_id != "linux-nas-" + share_id.hex[:16] or not LOCATION_RE.fullmatch(location_id):
        fail("Installer manifest location identity is invalid.")
    host = str(value["requested_host"])
    share = str(value["share_name"])
    if not re.fullmatch(r"[a-z0-9.-]{1,253}", host) or not SHARE_RE.fullmatch(share):
        fail("Installer manifest network identity is invalid.")
    for key in ("server_guid_hash", "identity_fingerprint_hash", "request_digest"):
        if not HASH_RE.fullmatch(str(value[key])):
            fail("Installer manifest digest is invalid.")
    return {key: str(item) for key, item in value.items()}


def registered_location(manifest: dict[str, str], credential_path: Path, mount_unit: str, automount_unit: str) -> dict[str, Any]:
    token = UUID(manifest["proposed_share_id"]).hex[:16]
    host_slot = f"/mnt/photo-organizer-sources/nas/{token}"
    authority = f"/mnt/nas/photo-organizer-{token}"
    return {
        "registration_id": manifest["proposed_share_id"],
        "location_id": manifest["location_id"],
        "display_name": manifest["location_name"],
        "share_name": manifest["share_name"],
        "canonical_source": f"//{manifest['requested_host']}/{manifest['share_name']}",
        "credential_reference": str(credential_path),
        "authoritative_target": authority,
        "host_slot": host_slot,
        "runtime_slot": f"/app/sources/nas/{token}",
        "mount_unit": mount_unit,
        "automount_unit": automount_unit,
        "identity_fingerprint_hash": manifest["identity_fingerprint_hash"],
        "identity_fingerprint_version": manifest["identity_fingerprint_version"],
        "status": "registered",
    }


def broker_location(appliance: dict[str, Any], share: dict[str, Any]) -> dict[str, Any]:
    return {
        "location_id": share["location_id"],
        "source_type": "nas",
        "display_name": share["display_name"],
        "host_slot": share["host_slot"],
        "runtime_slot": share["runtime_slot"],
        "filesystem_type": "cifs",
        "canonical_source": share["canonical_source"],
        "authoritative_target": share["authoritative_target"],
        "nas_appliance_id": appliance["registration_id"],
        "nas_share_id": share["registration_id"],
        "server_guid_hash": appliance["server_guid_hash"],
        "server_guid_masked": appliance["server_guid_masked"],
        "identity_fingerprint_hash": share["identity_fingerprint_hash"],
        "identity_fingerprint_version": share["identity_fingerprint_version"],
    }


def adopt_existing() -> None:
    config, config_gid = load_source_config()
    matches = [item for item in config["locations"] if item.get("location_id") == LEGACY_LOCATION_ID]
    if len(matches) != 1:
        fail("Existing Photo Organizer NAS location is missing or ambiguous.")
    location = matches[0]
    if (
        location.get("canonical_source") != "//192.168.1.171/PhotoOrganizer"
        or location.get("authoritative_target") != "/mnt/nas/photo-organizer"
    ):
        fail("Existing Photo Organizer NAS contract changed.")
    guid_hash, guid_masked = smb_server_guid_hash("192.168.1.171")
    registry = load_registry()
    existing = [item for item in registry["appliances"] if item.get("registration_id") == LEGACY_APPLIANCE_ID]
    if existing:
        if len(existing) != 1 or existing[0].get("server_guid_hash") != guid_hash:
            fail("Existing NAS registry identity conflicts.")
        appliance = existing[0]
    else:
        appliance = {
            "registration_id": LEGACY_APPLIANCE_ID,
            "friendly_name": "Photo Organizer NAS",
            "network_host": "192.168.1.171",
            "server_guid_hash": guid_hash,
            "server_guid_masked": guid_masked,
            "shares": [],
            "status": "active",
        }
        registry["appliances"].append(appliance)
    shares = [item for item in appliance["shares"] if item.get("location_id") == LEGACY_LOCATION_ID]
    if not shares:
        appliance["shares"].append({
            "registration_id": LEGACY_SHARE_ID,
            "location_id": LEGACY_LOCATION_ID,
            "display_name": "Photo Organizer NAS",
            "share_name": "PhotoOrganizer",
            "canonical_source": "//192.168.1.171/PhotoOrganizer",
            "credential_reference": "managed-by-existing-fstab",
            "authoritative_target": "/mnt/nas/photo-organizer",
            "host_slot": "/mnt/photo-organizer-sources/nas/photo-organizer",
            "runtime_slot": "/app/sources/nas/photo-organizer",
            "mount_unit": "mnt-nas-photo\\x2dorganizer.mount",
            "automount_unit": "mnt-nas-photo\\x2dorganizer.automount",
            "identity_fingerprint_hash": LEGACY_FINGERPRINT,
            "identity_fingerprint_version": "source_endpoint_identity_v1",
            "status": "registered",
        })
    elif len(shares) != 1 or shares[0].get("identity_fingerprint_hash") != LEGACY_FINGERPRINT:
        fail("Existing NAS share registry conflicts.")
    location.update({
        "nas_appliance_id": LEGACY_APPLIANCE_ID,
        "nas_share_id": LEGACY_SHARE_ID,
        "server_guid_hash": guid_hash,
        "server_guid_masked": guid_masked,
        "identity_fingerprint_hash": LEGACY_FINGERPRINT,
        "identity_fingerprint_version": "source_endpoint_identity_v1",
    })
    config["protocol_version"] = 2
    atomic_json(NAS_REGISTRY, registry, mode=0o600, gid=0)
    atomic_json(SOURCE_CONFIG, config, mode=0o640, gid=config_gid)
    print(f"EXISTING_NAS_SERVER_GUID_MASKED={guid_masked}")
    print("EXISTING_NAS_LOCATION_ID_PRESERVED=True")
    print("EXISTING_NAS_FINGERPRINT_PRESERVED=True")
    print("CREDENTIAL_STATE_CHANGED=False")
    print("MOUNT_STATE_CHANGED=False")
    print("EXISTING_NAS_PROTECTED_REGISTRY_ADOPTION=PASS")


def unit_names(authority: str) -> tuple[str, str]:
    mount = run(["systemd-escape", "--path", "--suffix=mount", authority]).stdout.strip()
    automount = run(["systemd-escape", "--path", "--suffix=automount", authority]).stdout.strip()
    if not re.fullmatch(r"[A-Za-z0-9_.@\\x-]+\.(?:mount|automount)", mount) or not automount.endswith(".automount"):
        fail("Generated systemd unit identity is invalid.")
    return mount, automount


def update_network_registration(
    registration_id: UUID,
    manifest: dict[str, str],
    config: dict[str, Any],
    config_gid: int,
    registry: dict[str, Any],
) -> None:
    """Move one existing registration only after its stable SMB identity matches."""

    config_matches = [item for item in config["locations"] if item.get("location_id") == manifest["location_id"]]
    appliance_matches = [
        item for item in registry["appliances"]
        if item.get("registration_id") == manifest["proposed_appliance_id"]
    ]
    if len(config_matches) != 1 or len(appliance_matches) != 1:
        fail("Existing registered NAS location is missing or ambiguous.")
    location = config_matches[0]
    appliance = appliance_matches[0]
    share_matches = [
        item for item in appliance.get("shares", [])
        if item.get("registration_id") == manifest["proposed_share_id"]
    ]
    if len(share_matches) != 1:
        fail("Existing registered NAS share is missing or ambiguous.")
    share = share_matches[0]
    expected_identity = {
        "location_id": manifest["location_id"],
        "identity_fingerprint_hash": manifest["identity_fingerprint_hash"],
        "identity_fingerprint_version": manifest["identity_fingerprint_version"],
    }
    if any(location.get(key) != value or share.get(key) != value for key, value in expected_identity.items()):
        fail("Existing registered NAS share identity changed.")
    credential_path = Path(str(share.get("credential_reference", "")))
    authority = str(share.get("authoritative_target", ""))
    host_slot = str(share.get("host_slot", ""))
    mount_unit = str(share.get("mount_unit", ""))
    automount_unit = str(share.get("automount_unit", ""))
    if (
        credential_path.parent != CREDENTIAL_DIRECTORY
        or not authority.startswith("/mnt/nas/photo-organizer-")
        or not host_slot.startswith("/mnt/photo-organizer-sources/nas/")
        or not mount_unit.endswith(".mount")
        or not automount_unit.endswith(".automount")
    ):
        fail("Existing registered NAS host targets are outside approved roots.")
    require_safe_file(credential_path, mode=0o600)
    mount_unit_path = UNIT_DIRECTORY / mount_unit
    automount_unit_path = UNIT_DIRECTORY / automount_unit
    require_safe_file(mount_unit_path, mode=0o644)
    require_safe_file(automount_unit_path, mode=0o644)
    old_canonical = str(share.get("canonical_source", ""))
    new_canonical = f"//{manifest['requested_host']}/{manifest['share_name']}"
    mount_text = mount_unit_path.read_text(encoding="utf-8")
    old_what = f"What={old_canonical}\n"
    if mount_text.count(old_what) != 1:
        fail("Existing NAS mount unit does not contain one exact registered source.")
    updated_mount_text = mount_text.replace(old_what, f"What={new_canonical}\n")
    rollback = Path("/var/backups/photo-organizer") / f"nas-registration-{registration_id}"
    if rollback.exists():
        fail("Exact NAS registration rollback directory already exists.")
    rollback.mkdir(mode=0o700, parents=True)
    os.chown(rollback, 0, 0)
    shutil.copy2(SOURCE_CONFIG, rollback / "source-access.json")
    shutil.copy2(NAS_REGISTRY, rollback / "nas-registrations.json")
    shutil.copy2(mount_unit_path, rollback / mount_unit)
    instance = f"photo-organizer-source-nas@{manifest['location_id']}.service"
    try:
        run(["systemctl", "stop", instance])
        active_slot = run(
            ["findmnt", "--kernel", "--noheadings", "--mountpoint", host_slot],
            check=False,
        ).returncode == 0
        if active_slot:
            run(["umount", "--", host_slot])
        run(["systemctl", "disable", "--now", automount_unit])
        run(["systemctl", "stop", mount_unit], check=False)
        atomic_text(mount_unit_path, updated_mount_text, mode=0o644)
        share["canonical_source"] = new_canonical
        appliance["network_host"] = manifest["requested_host"]
        location["canonical_source"] = new_canonical
        atomic_json(NAS_REGISTRY, registry, mode=0o600, gid=0)
        atomic_json(SOURCE_CONFIG, config, mode=0o640, gid=config_gid)
        run(["systemctl", "daemon-reload"])
        run(["systemctl", "enable", "--now", automount_unit])
        run(["systemctl", "enable", "--now", instance], timeout=45)
        require_namespace_instance_ready(instance)
        run(["systemctl", "restart", BROKER_UNIT])
        complete_registration_with_retry(registration_id)
    except Exception:
        run(["systemctl", "stop", instance], check=False)
        run(["systemctl", "disable", "--now", automount_unit], check=False)
        shutil.copy2(rollback / "source-access.json", SOURCE_CONFIG)
        shutil.copy2(rollback / "nas-registrations.json", NAS_REGISTRY)
        shutil.copy2(rollback / mount_unit, mount_unit_path)
        run(["systemctl", "daemon-reload"], check=False)
        run(["systemctl", "enable", "--now", automount_unit], check=False)
        run(["systemctl", "enable", "--now", instance], timeout=45, check=False)
        run(["systemctl", "restart", BROKER_UNIT], check=False)
        raise
    print(f"NAS_LOCATION_ID={manifest['location_id']}")
    print(f"NAS_SERVER_GUID_MASKED={manifest['server_guid_masked']}")
    print("NAS_DURABLE_IDENTITY_PRESERVED=True")
    print("CREDENTIAL_STATE_CHANGED=False")
    print("NETWORK_LOCATION_UPDATE=PASS")
    print("RAW_USERNAME_PRINTED=False")
    print("RAW_SECRET_PRINTED=False")


def install_registration(registration_id: UUID) -> None:
    manifest = validate_manifest(
        fetch_json(f"/api/admin/nas-registrations/pending/{registration_id}/installer-manifest"),
        registration_id,
    )
    actual_guid_hash, actual_guid_masked = smb_server_guid_hash(manifest["requested_host"])
    if actual_guid_hash != manifest["server_guid_hash"] or actual_guid_masked != manifest["server_guid_masked"]:
        fail("NAS appliance identity changed after pending registration was created.")
    config, config_gid = load_source_config()
    registry = load_registry()
    if manifest["operation"] == "update_network_host":
        update_network_registration(registration_id, manifest, config, config_gid, registry)
        return
    if any(item.get("location_id") == manifest["location_id"] for item in config["locations"]):
        fail("Pending NAS location is already installed.")
    appliance_matches = [
        item for item in registry["appliances"]
        if item.get("registration_id") == manifest["proposed_appliance_id"]
    ]
    if appliance_matches:
        if len(appliance_matches) != 1 or appliance_matches[0].get("server_guid_hash") != actual_guid_hash:
            fail("Registered NAS appliance identity conflicts.")
        appliance = appliance_matches[0]
    else:
        if any(
            item.get("network_host", "").casefold() == manifest["requested_host"].casefold()
            and item.get("server_guid_hash") != actual_guid_hash
            for item in registry["appliances"]
        ):
            fail("Another registered appliance occupies this network address.")
        appliance = {
            "registration_id": manifest["proposed_appliance_id"],
            "friendly_name": manifest["appliance_name"],
            "network_host": manifest["requested_host"],
            "server_guid_hash": actual_guid_hash,
            "server_guid_masked": actual_guid_masked,
            "shares": [],
            "status": "active",
        }
        registry["appliances"].append(appliance)
    if any(item.get("share_name", "").casefold() == manifest["share_name"].casefold() for item in appliance["shares"]):
        fail("This NAS share is already installed.")
    token = UUID(manifest["proposed_share_id"]).hex[:16]
    credential_path = CREDENTIAL_DIRECTORY / f"photo-organizer-{token}"
    authority = f"/mnt/nas/photo-organizer-{token}"
    mount_unit, automount_unit = unit_names(authority)
    mount_unit_path = UNIT_DIRECTORY / mount_unit
    automount_unit_path = UNIT_DIRECTORY / automount_unit
    instance = f"photo-organizer-source-nas@{manifest['location_id']}.service"
    for path in (credential_path, mount_unit_path, automount_unit_path, Path(authority)):
        if os.path.lexists(path):
            fail("A generated host target already exists; refusing reuse.")
    username = getpass.getpass("NAS username (hidden): ")
    password = getpass.getpass("NAS password (hidden): ")
    if not username or not password or "\n" in username or "\n" in password:
        fail("NAS credentials are empty or malformed.")
    rollback = Path("/var/backups/photo-organizer") / f"nas-registration-{registration_id}"
    if rollback.exists():
        fail("Exact NAS registration rollback directory already exists.")
    rollback.mkdir(mode=0o700, parents=True)
    os.chown(rollback, 0, 0)
    shutil.copy2(SOURCE_CONFIG, rollback / "source-access.json")
    if NAS_REGISTRY.exists():
        shutil.copy2(NAS_REGISTRY, rollback / "nas-registrations.json")
    CREDENTIAL_DIRECTORY.mkdir(mode=0o700, parents=True, exist_ok=True)
    credential_directory_stat = CREDENTIAL_DIRECTORY.stat()
    if (
        CREDENTIAL_DIRECTORY.is_symlink()
        or credential_directory_stat.st_uid != 0
        or credential_directory_stat.st_gid != 0
        or stat.S_IMODE(credential_directory_stat.st_mode) != 0o700
    ):
        fail("Protected credential directory is unsafe.")
    created_paths: list[Path] = []
    try:
        atomic_text(credential_path, f"username={username}\npassword={password}\n", mode=0o600)
        created_paths.append(credential_path)
        username = password = ""
        data_group = str(config.get("data_read_group", ""))
        data_gid = grp.getgrnam(data_group).gr_gid
        if data_gid <= 0:
            fail("Approved Source data group is invalid.")
        Path(authority).mkdir(mode=0o755, parents=True)
        os.chown(authority, 0, 0)
        os.chmod(authority, 0o755)
        created_paths.append(Path(authority))
        canonical = f"//{manifest['requested_host']}/{manifest['share_name']}"
        mount_text = (
            "[Unit]\nDescription=Photo Organizer registered NAS authority\n"
            "After=network-online.target\nWants=network-online.target\n\n"
            f"[Mount]\nWhat={canonical}\nWhere={authority}\nType=cifs\n"
            f"Options=credentials={credential_path},uid=1000,gid={data_gid},vers=3.1.1,iocharset=utf8,ro,file_mode=0440,dir_mode=0550,_netdev,nofail\n"
            "TimeoutSec=30\n\n[Install]\nWantedBy=multi-user.target\n"
        )
        automount_text = (
            "[Unit]\nDescription=Photo Organizer registered NAS automount\n"
            "After=network-online.target\nWants=network-online.target\n\n"
            f"[Automount]\nWhere={authority}\nTimeoutIdleSec=0\n\n"
            "[Install]\nWantedBy=multi-user.target\n"
        )
        atomic_text(mount_unit_path, mount_text, mode=0o644)
        created_paths.append(mount_unit_path)
        atomic_text(automount_unit_path, automount_text, mode=0o644)
        created_paths.append(automount_unit_path)
        share = registered_location(manifest, credential_path, mount_unit, automount_unit)
        appliance["shares"].append(share)
        config["locations"].append(broker_location(appliance, share))
        config["protocol_version"] = 2
        atomic_json(NAS_REGISTRY, registry, mode=0o600, gid=0)
        atomic_json(SOURCE_CONFIG, config, mode=0o640, gid=config_gid)
        run(["systemctl", "daemon-reload"])
        run(["systemctl", "enable", "--now", automount_unit])
        run(["systemctl", "enable", "--now", instance], timeout=45)
        require_namespace_instance_ready(instance)
        run(["systemctl", "restart", BROKER_UNIT])
        complete_registration_with_retry(registration_id)
    except Exception:
        run(["systemctl", "disable", "--now", instance], check=False)
        run(["systemctl", "disable", "--now", automount_unit], check=False)
        backup_config = rollback / "source-access.json"
        if backup_config.exists():
            shutil.copy2(backup_config, SOURCE_CONFIG)
        backup_registry = rollback / "nas-registrations.json"
        if backup_registry.exists():
            shutil.copy2(backup_registry, NAS_REGISTRY)
        elif NAS_REGISTRY.exists():
            NAS_REGISTRY.unlink()
        for path in reversed(created_paths):
            if path.is_dir() and not path.is_symlink():
                try:
                    path.rmdir()
                except OSError:
                    pass
            else:
                path.unlink(missing_ok=True)
        run(["systemctl", "daemon-reload"], check=False)
        run(["systemctl", "restart", BROKER_UNIT], check=False)
        raise
    print(f"NAS_LOCATION_ID={manifest['location_id']}")
    print(f"NAS_SERVER_GUID_MASKED={actual_guid_masked}")
    print("CREDENTIAL_FILE_OWNER_MODE_VALID=True")
    print("PROTECTED_REGISTRY_UPDATED=True")
    print("AUTHORITY_AUTOMOUNT_ENABLED=True")
    print("SOURCE_NAMESPACE_LOCATION_ACTIVE=True")
    print("BROKER_REGISTRATION_COMPLETED=True")
    print("RAW_USERNAME_PRINTED=False")
    print("RAW_SECRET_PRINTED=False")
    print("NAS_REGISTRATION_INSTALL=PASS")


def main() -> None:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="action", required=True)
    subparsers.add_parser("adopt-existing")
    install = subparsers.add_parser("install")
    install.add_argument("--registration-id", required=True, type=UUID)
    args = parser.parse_args()
    require_root()
    try:
        if args.action == "adopt-existing":
            adopt_existing()
        else:
            install_registration(args.registration_id)
    except InstallFailure as exc:
        print("RAW_SECRET_PRINTED=False")
        raise SystemExit(f"FAIL: {exc}") from exc


if __name__ == "__main__":
    main()
