"""Redacted foreground development CLI for pairing and presence."""

from __future__ import annotations

import argparse
import getpass
import json
import sys
import time
from pathlib import Path
from typing import Sequence
from uuid import UUID

from windows_helper_shared.channel import (
    ClaimedAcquireOperation,
    ClaimedChildAttestationOperation,
    ClaimedInventoryOperation,
    ClaimedInventoryAttestationOperation,
    ClaimedObserveVolumesOperation,
    ClaimedProbeOperation,
    HelperHeartbeatRequest,
    PairingCompleteRequest,
)
from windows_helper_shared.protocol import (
    HelperInventoryPageResponse,
    HelperKnownSourceAttestationResponse,
    HelperChildAttestationResponse,
    HelperObserveVolumesResponse,
    HelperProbeResponse,
)

from .acquisition import execute_acquisition
from .attestation import ChildAttestationAuthority, ChildIdentityMismatch, InventoryAttestationAuthority
from . import HELPER_VERSION
from .capabilities import capability_identity
from .client import HelperApiClient, HelperClientError
from .credential_store import DpapiCredentialStore, StoredCredential
from .lifecycle import DEFAULT_IDLE_SECONDS, IdleDeadline, SingleInstance, mutex_name, parse_start_uri
from .logging_config import configure_file_logging
from .operations import HelperOperationExecutor
from .tunnel import TunnelError, TunnelManager


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="photo-organizer-windows-helper")
    parser.add_argument("--version", action="version", version=HELPER_VERSION)
    subcommands = parser.add_subparsers(dest="command", required=True)
    pair = subcommands.add_parser("pair", help="Pair this Helper through the approved channel.")
    pair.add_argument("--access-node-id", required=True, type=UUID)
    status = subcommands.add_parser("status", help="Check the authenticated Helper session.")
    status.add_argument(
        "--output-file",
        help="Write the bounded redacted status JSON for a windowless packaged invocation.",
    )
    subcommands.add_parser("heartbeat", help="Send one bounded presence heartbeat.")
    subcommands.add_parser("serve", help="Run the foreground bounded operation loop.")
    subcommands.add_parser("forget", help="Remove only the local protected credential/state.")
    return parser


def _safe_output(*, output_file: str | None = None, **values: object) -> None:
    rendered = json.dumps(values, sort_keys=True, separators=(",", ":"))
    if output_file is None:
        print(rendered)
        return
    path = Path(output_file)
    if not path.is_absolute() or path.suffix.casefold() != ".json" or not path.parent.is_dir():
        raise ValueError("Status output file must be an absolute JSON path in an existing directory.")
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(rendered + "\n", encoding="utf-8")
    temporary.replace(path)


def _serve(
    client: HelperApiClient,
    credential: StoredCredential,
    *,
    idle_timeout_seconds: float | None = None,
) -> int:
    executor = HelperOperationExecutor()
    child_attestation_authority = ChildAttestationAuthority()
    inventory_attestation_authority = InventoryAttestationAuthority()
    active_child_until = 0.0
    active_poll_delay = 0.05
    last_heartbeat = 0.0
    idle = IdleDeadline(idle_timeout_seconds) if idle_timeout_seconds is not None else None
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
                active_poll_delay = 0.05
                report_pending = False
                if idle is not None:
                    idle.set_busy(True)
                try:
                    if isinstance(operation, ClaimedAcquireOperation):
                        result = execute_acquisition(
                            operation,
                            client,
                            credential,
                            attestation_authority=child_attestation_authority,
                        )
                        client.complete_acquire(credential, operation.operation_id, result)
                        active_child_until = time.monotonic() + 2.0
                        if idle is not None:
                            idle.set_busy(False)
                        continue
                    result = executor.execute(
                        operation,
                        attestation_authority=(
                            inventory_attestation_authority
                            if isinstance(operation, (ClaimedInventoryOperation, ClaimedInventoryAttestationOperation))
                            else child_attestation_authority
                        ),
                    )
                    if (
                        isinstance(operation, ClaimedProbeOperation)
                        and isinstance(result, HelperProbeResponse)
                    ):
                        client.complete_probe(credential, operation.operation_id, result)
                    elif (
                        isinstance(operation, ClaimedObserveVolumesOperation)
                        and isinstance(result, HelperObserveVolumesResponse)
                    ):
                        client.complete_volume_observation(
                            credential,
                            operation.operation_id,
                            result,
                        )
                    elif (
                        isinstance(operation, ClaimedInventoryAttestationOperation)
                        and isinstance(result, HelperKnownSourceAttestationResponse)
                    ):
                        client.complete_inventory_attestation(
                            credential,
                            operation.operation_id,
                            result,
                        )
                    elif (
                        isinstance(operation, ClaimedInventoryOperation)
                        and isinstance(result, HelperInventoryPageResponse)
                    ):
                        client.complete_inventory(credential, operation.operation_id, result)
                    elif (
                        isinstance(operation, ClaimedChildAttestationOperation)
                        and isinstance(result, HelperChildAttestationResponse)
                    ):
                        client.complete_child_attestation(
                            credential,
                            operation.operation_id,
                            result,
                        )
                        active_child_until = time.monotonic() + 2.0
                        if idle is not None:
                            idle.set_busy(False)
                        continue
                    else:
                        client.fail_operation(
                            credential,
                            operation.operation_id,
                            "operation_unsupported",
                        )
                except ChildIdentityMismatch:
                    try:
                        client.fail_operation(
                            credential,
                            operation.operation_id,
                            "identity_changed",
                        )
                    except HelperClientError:
                        report_pending = True
                except (OSError, RuntimeError, ValueError):
                    try:
                        client.fail_operation(
                            credential,
                            operation.operation_id,
                            "operation_failed",
                        )
                    except HelperClientError:
                        report_pending = True
                finally:
                    if idle is not None:
                        idle.set_busy(report_pending)
            if idle is not None and idle.should_exit():
                return 0
            if operation is None and time.monotonic() < active_child_until:
                time.sleep(active_poll_delay)
                active_poll_delay = min(0.4, active_poll_delay * 2.0)
            else:
                time.sleep(claim.poll_after_seconds)
    except KeyboardInterrupt:
        _safe_output(command="serve", status="stopped")
        return 0


def run(argv: Sequence[str] | None = None) -> int:
    raw_arguments = list(argv) if argv is not None else sys.argv[1:]
    if len(raw_arguments) == 1 and raw_arguments[0].startswith("photoorganizer-helper:"):
        return _run_packaged_uri(raw_arguments[0])
    arguments = _parser().parse_args(raw_arguments)
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
                    output_file=arguments.output_file,
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
        if (
            "arguments" in locals()
            and arguments.command == "status"
            and arguments.output_file is not None
        ):
            try:
                _safe_output(
                    output_file=arguments.output_file,
                    command="status",
                    status="failed",
                    error_code="status_check_failed",
                )
            except (OSError, ValueError):
                pass
        print("Windows Helper operation failed safely.", file=sys.stderr)
        return 1


def _run_packaged_uri(uri: str) -> int:
    """Start the retained identity on demand through the exact allowlisted URI."""
    logger = None
    try:
        parse_start_uri(uri)
        store = DpapiCredentialStore()
        logger = configure_file_logging(store.state_directory)
        credential = store.load()
        if credential is None:
            raise RuntimeError("No protected Helper credential is stored.")
        with SingleInstance(mutex_name(credential.access_node_id)) as instance:
            if not instance.acquire():
                logger.info("event=duplicate_start_reused")
                return 0
            logger.info("event=packaged_start version=%s", HELPER_VERSION)
            with TunnelManager():
                result = _serve(
                    HelperApiClient(),
                    credential,
                    idle_timeout_seconds=DEFAULT_IDLE_SECONDS,
                )
            logger.info("event=idle_or_requested_exit")
            return result
    except (HelperClientError, TunnelError, RuntimeError, ValueError, OSError):
        if logger is not None:
            logger.error("event=packaged_start_failed")
        return 1


def main() -> None:
    raise SystemExit(run())
