#!/usr/bin/env python3
"""Bounded operator-safe protocol/identity check for the Linux Source broker."""

from __future__ import annotations

import argparse
import json
import socket

MAX_BYTES = 256 * 1024
EXPECTED_LOCATIONS = {"linux-local-server-photos", "linux-nas-photo-organizer"}


def fail(message: str) -> None:
    raise SystemExit(f"FAIL: {message}")


def request_broker(socket_path: str, request: dict[str, object]) -> dict[str, object]:
    encoded_request = json.dumps(request, separators=(",", ":")).encode() + b"\n"
    raw = b""
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
            connection.settimeout(5)
            connection.connect(socket_path)
            connection.sendall(encoded_request)
            while b"\n" not in raw and len(raw) <= MAX_BYTES:
                chunk = connection.recv(min(65536, MAX_BYTES + 1 - len(raw)))
                if not chunk:
                    break
                raw += chunk
    except (OSError, TimeoutError) as exc:
        fail(f"broker protocol check failed safely ({type(exc).__name__}).")
    if len(raw) > MAX_BYTES:
        fail("broker response exceeded the safe size limit.")
    try:
        payload = json.loads(raw.split(b"\n", 1)[0].decode())
    except (UnicodeDecodeError, json.JSONDecodeError):
        fail("broker returned malformed protocol data.")
    if not isinstance(payload, dict):
        fail("broker returned a non-object protocol result.")
    return payload


def verify_envelope(payload: dict[str, object]) -> None:
    if (
        payload.get("protocol_version") != 1
        or payload.get("provider_name") != "linux_stable_mount_v1"
        or payload.get("provider_version") != "1"
    ):
        fail("broker protocol/provider identity differs from the approved contract.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--socket", default="/run/photo-organizer-source-access/broker.sock")
    args = parser.parse_args()
    payload = request_broker(
        args.socket,
        {"protocol_version": 1, "action": "list_locations"},
    )
    verify_envelope(payload)
    if payload.get("action") != "list_locations":
        fail("broker location-list action differs from the approved contract.")
    locations = payload.get("locations")
    if not isinstance(locations, list):
        fail("broker location inventory is malformed.")
    ids = [item.get("location_id") for item in locations if isinstance(item, dict)]
    if len(ids) != len(EXPECTED_LOCATIONS) or set(ids) != EXPECTED_LOCATIONS:
        fail("broker location inventory differs from the approved exact set.")
    statuses = sorted(str(item.get("status", "invalid")) for item in locations)
    if any(status not in {"available", "unavailable", "blocked", "error"} for status in statuses):
        fail("broker location status is malformed.")
    access_nodes = [item.get("access_node") for item in locations if isinstance(item, dict)]
    access_node_ids = {
        node.get("access_node_id")
        for node in access_nodes
        if isinstance(node, dict) and isinstance(node.get("access_node_id"), str)
    }
    if (
        len(access_nodes) != len(EXPECTED_LOCATIONS)
        or len(access_node_ids) != 1
        or not next(iter(access_node_ids), "").startswith("linux-access-node:")
        or any(
            not isinstance(node, dict)
            or node.get("os_family") != "linux"
            or not isinstance(node.get("host_fingerprint_hash"), str)
            for node in access_nodes
        )
    ):
        fail("stable Access Node evidence is missing or inconsistent.")

    rejected = request_broker(
        args.socket,
        {"protocol_version": 1, "action": "list_locations", "host_path": "/"},
    )
    verify_envelope(rejected)
    blockers = rejected.get("blockers")
    if (
        rejected.get("locations") != []
        or not isinstance(blockers, list)
        or len(blockers) != 1
        or not isinstance(blockers[0], dict)
        or blockers[0].get("code") != "malformed_request"
    ):
        fail("broker did not reject arbitrary path input under the bounded protocol.")

    print(
        "PASS: broker protocol/provider, stable Access Node presence, "
        f"{len(ids)} bounded location summaries, and arbitrary-path rejection verified; "
        f"statuses={','.join(statuses)}"
    )


if __name__ == "__main__":
    main()
