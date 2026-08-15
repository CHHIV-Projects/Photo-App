"""Redacted foreground development CLI for pairing and presence."""

from __future__ import annotations

import argparse
import getpass
import json
import sys
import time
from typing import Sequence
from uuid import UUID

from windows_helper_shared.channel import (
    ClaimedAcquireOperation,
    ClaimedInventoryOperation,
    ClaimedProbeOperation,
    HelperHeartbeatRequest,
    PairingCompleteRequest,
)
from windows_helper_shared.protocol import (
    HelperInventoryPageResponse,
    HelperProbeResponse,
)

from .acquisition import execute_acquisition
from .capabilities import capability_identity
from .client import HelperApiClient, HelperClientError
from .credential_store import DpapiCredentialStore, StoredCredential
from .operations import HelperOperationExecutor
from .tunnel import TunnelError, TunnelManager


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="photo-organizer-windows-helper")
    subcommands = parser.add_subparsers(dest="command", required=True)
    pair = subcommands.add_parser("pair", help="Pair this Helper through the approved channel.")
    pair.add_argument("--access-node-id", required=True, type=UUID)
    subcommands.add_parser("status", help="Check the authenticated Helper session.")
    subcommands.add_parser("heartbeat", help="Send one bounded presence heartbeat.")
    subcommands.add_parser("serve", help="Run the foreground bounded operation loop.")
    subcommands.add_parser("forget", help="Remove only the local protected credential/state.")
    return parser


def _safe_output(**values: object) -> None:
    print(json.dumps(values, sort_keys=True, separators=(",", ":")))


def _serve(
    client: HelperApiClient,
    credential: StoredCredential,
) -> int:
    executor = HelperOperationExecutor()
    last_heartbeat = 0.0
    try:
        while True:
            now = time.monotonic()
            if now - last_heartbeat >= 30.0:
                client.heartbeat(
                    credential,
                    HelperHeartbeatRequest(
                        access_node_id=UUID(credential.access_node_id),
                        capability_identity=capability_identity(credential.access_node_id),
                    ),
                )
                last_heartbeat = now
            claim = client.claim_operation(credential)
            operation = claim.operation
            if operation is not None:
                try:
                    if isinstance(operation, ClaimedAcquireOperation):
                        result = execute_acquisition(operation, client, credential)
                        client.complete_acquire(credential, operation.operation_id, result)
                        continue
                    result = executor.execute(operation)
                    if (
                        isinstance(operation, ClaimedProbeOperation)
                        and isinstance(result, HelperProbeResponse)
                    ):
                        client.complete_probe(credential, operation.operation_id, result)
                    elif (
                        isinstance(operation, ClaimedInventoryOperation)
                        and isinstance(result, HelperInventoryPageResponse)
                    ):
                        client.complete_inventory(credential, operation.operation_id, result)
                    else:
                        client.fail_operation(
                            credential,
                            operation.operation_id,
                            "operation_unsupported",
                        )
                except (OSError, RuntimeError, ValueError):
                    try:
                        client.fail_operation(
                            credential,
                            operation.operation_id,
                            "operation_failed",
                        )
                    except HelperClientError:
                        pass
            time.sleep(claim.poll_after_seconds)
    except KeyboardInterrupt:
        _safe_output(command="serve", status="stopped")
        return 0


def run(argv: Sequence[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    store = DpapiCredentialStore()
    if arguments.command == "forget":
        _safe_output(command="forget", local_state_removed=store.forget(), server_revoked=False)
        return 0

    try:
        client = HelperApiClient()
        if arguments.command == "pair":
            pairing_code = getpass.getpass("One-time pairing code: ")
            access_node_id = str(arguments.access_node_id)
            request = PairingCompleteRequest(
                pairing_code=pairing_code,
                access_node_id=arguments.access_node_id,
                capability_identity=capability_identity(access_node_id),
            )
            pairing_code = ""
            with TunnelManager():
                response = client.pair(request)
            store.save(
                StoredCredential(
                    access_node_id=str(response.access_node_id),
                    credential_id=response.credential_id,
                    credential_version=response.credential_version,
                    token=response.credential_token,
                )
            )
            _safe_output(
                command="pair",
                status=response.status,
                access_node_id=str(response.access_node_id),
                credential_id=response.credential_id,
                credential_version=response.credential_version,
            )
            return 0

        credential = store.load()
        if credential is None:
            raise RuntimeError("No protected Helper credential is stored.")
        with TunnelManager():
            if arguments.command == "serve":
                return _serve(client, credential)
            if arguments.command == "status":
                response = client.session(credential)
                _safe_output(
                    command="status",
                    credential_status=response.credential_status,
                    access_node_id=str(response.access_node_id),
                    credential_id=response.credential_id,
                    credential_version=response.credential_version,
                    helper_version=response.helper_version,
                    last_seen_at=response.last_seen_at.isoformat() if response.last_seen_at else None,
                )
            else:
                response = client.heartbeat(
                    credential,
                    HelperHeartbeatRequest(
                        access_node_id=UUID(credential.access_node_id),
                        capability_identity=capability_identity(credential.access_node_id),
                    ),
                )
                _safe_output(
                    command="heartbeat",
                    heartbeat_status=response.heartbeat_status,
                    access_node_id=str(response.access_node_id),
                    credential_id=response.credential_id,
                    credential_version=response.credential_version,
                    helper_version=response.helper_version,
                    last_seen_at=response.last_seen_at.isoformat() if response.last_seen_at else None,
                )
        return 0
    except (HelperClientError, TunnelError, RuntimeError, ValueError):
        print("Windows Helper operation failed safely.", file=sys.stderr)
        return 1


def main() -> None:
    raise SystemExit(run())
