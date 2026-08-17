from __future__ import annotations

import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import MagicMock, patch
from uuid import uuid4

from photo_organizer_windows_helper.client import HelperApiClient, HELPER_BASE_URL
from photo_organizer_windows_helper.credential_store import (
    DpapiCredentialStore,
    StoredCredential,
)
from photo_organizer_windows_helper.tunnel import (
    LOCAL_PORT,
    SSH_HOST_ALIAS,
    TunnelError,
    TunnelManager,
    TunnelProcessEvidence,
    WindowsTunnelInspector,
    tunnel_arguments,
    validate_tunnel_evidence,
)
from windows_helper_shared.channel import HelperHeartbeatRequest, PairingCompleteRequest
from photo_organizer_windows_helper.capabilities import capability_identity


class _Response:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


class _Inspector:
    def __init__(self, evidence: tuple[TunnelProcessEvidence, ...] = ()) -> None:
        self.evidence = evidence

    def listener_evidence(self, port: int) -> tuple[TunnelProcessEvidence, ...]:
        if port != LOCAL_PORT:
            raise AssertionError("unexpected port")
        return self.evidence


class CredentialStoreTests(unittest.TestCase):
    def test_dpapi_store_persists_no_plaintext_and_forget_is_local_only(self) -> None:
        credential = StoredCredential(
            access_node_id=str(uuid4()),
            credential_id="c_public",
            credential_version=1,
            token="raw-secret-token-that-must-not-be-stored",
        )
        with tempfile.TemporaryDirectory() as directory, patch(
            "photo_organizer_windows_helper.credential_store._protect_dpapi",
            return_value=b"opaque-dpapi-ciphertext",
        ), patch(
            "photo_organizer_windows_helper.credential_store._unprotect_dpapi",
            return_value=credential.token.encode("utf-8"),
        ):
            store = DpapiCredentialStore(Path(directory))
            store.save(credential)
            combined = store.credential_path.read_bytes() + store.state_path.read_bytes()
            self.assertNotIn(credential.token.encode("utf-8"), combined)
            self.assertEqual(store.load(), credential)
            self.assertTrue(store.forget())
            self.assertFalse(store.forget())

    def test_dpapi_is_platform_isolated(self) -> None:
        from photo_organizer_windows_helper import credential_store

        with patch.object(credential_store.sys, "platform", "linux"):
            with self.assertRaisesRegex(RuntimeError, "unavailable"):
                credential_store._protect_dpapi(b"secret")


class TunnelTests(unittest.TestCase):
    def test_command_is_exact_loopback_strict_and_shell_free(self) -> None:
        arguments = tunnel_arguments()
        rendered = " ".join(arguments)
        self.assertIn("StrictHostKeyChecking=yes", arguments)
        self.assertIn("ExitOnForwardFailure=yes", arguments)
        self.assertIn("ServerAliveInterval=60", arguments)
        self.assertIn("ServerAliveCountMax=3", arguments)
        self.assertIn("GatewayPorts=no", arguments)
        self.assertIn("PermitLocalCommand=no", arguments)
        self.assertIn("127.0.0.1:18011:127.0.0.1:18011", arguments)
        self.assertEqual(arguments[-1], SSH_HOST_ALIAS)
        self.assertEqual(arguments.count("-L"), 1)
        self.assertNotIn("-R", arguments)
        self.assertNotIn("-D", arguments)
        self.assertNotIn("0.0.0.0", rendered)

    def test_windows_listener_inspection_uses_bounded_netstat_and_fails_closed(self) -> None:
        self.assertIn("netstat.exe -ano -p TCP", WindowsTunnelInspector._SCRIPT)
        self.assertNotIn("Get-NetTCPConnection", WindowsTunnelInspector._SCRIPT)
        inspector = WindowsTunnelInspector()
        with patch(
            "photo_organizer_windows_helper.tunnel.subprocess.run",
            side_effect=subprocess.TimeoutExpired(["powershell.exe"], 20),
        ) as run:
            with self.assertRaisesRegex(TunnelError, "failed safely"):
                inspector.listener_evidence(LOCAL_PORT)
        _, keywords = run.call_args
        self.assertEqual(keywords["creationflags"], 0)

    def test_exact_owned_tunnel_can_be_reused(self) -> None:
        executable = r"C:\Windows\System32\OpenSSH\ssh.exe"
        evidence = TunnelProcessEvidence(
            pid=123,
            executable=executable,
            owner=r"MACHINE\chuck",
            arguments=tunnel_arguments(),
        )
        self.assertTrue(
            validate_tunnel_evidence(
                evidence,
                expected_executable=executable,
                expected_owner="chuck",
            )
        )
        self.assertFalse(
            validate_tunnel_evidence(
                TunnelProcessEvidence(
                    pid=123,
                    executable=executable,
                    owner=r"MACHINE\chuck",
                    arguments=tunnel_arguments(),
                    local_address="0.0.0.0",
                ), expected_executable=executable, expected_owner="chuck"
            )
        )
        manager = TunnelManager(inspector=_Inspector((evidence,)), ssh_executable=executable)
        manager.configuration_validator = lambda *_: True
        with patch("photo_organizer_windows_helper.tunnel.getpass.getuser", return_value="chuck"):
            manager.open()
        self.assertTrue(manager.reused)
        manager.close()

    def test_wrong_or_ambiguous_listener_is_refused_without_termination(self) -> None:
        executable = r"C:\Windows\System32\OpenSSH\ssh.exe"
        wrong = TunnelProcessEvidence(
            pid=321,
            executable=executable,
            owner=r"MACHINE\other",
            arguments=tunnel_arguments(),
        )
        manager = TunnelManager(inspector=_Inspector((wrong,)), ssh_executable=executable)
        manager.configuration_validator = lambda *_: True
        with self.assertRaises(TunnelError):
            manager.open()
        manager = TunnelManager(inspector=_Inspector((wrong, wrong)), ssh_executable=executable)
        manager.configuration_validator = lambda *_: True
        with self.assertRaises(TunnelError):
            manager.open()

    def test_new_tunnel_uses_argument_list_and_owns_only_started_process(self) -> None:
        process = MagicMock()
        process.poll.return_value = None
        process.wait.return_value = 0
        with patch("photo_organizer_windows_helper.tunnel.subprocess.Popen", return_value=process) as popen, patch(
            "photo_organizer_windows_helper.tunnel.socket.create_connection"
        ) as connect:
            connect.return_value.__enter__.return_value = object()
            manager = TunnelManager(
                inspector=_Inspector(),
                ssh_executable=r"C:\Windows\System32\OpenSSH\ssh.exe",
                startup_timeout_seconds=0.1,
                configuration_validator=lambda *_: True,
            )
            manager.open()
            manager.close()
        args, kwargs = popen.call_args
        self.assertEqual(tuple(args[0][1:]), tunnel_arguments())
        self.assertFalse(kwargs["shell"])
        self.assertEqual(kwargs["creationflags"], 0)
        process.terminate.assert_called_once()


class ClientTests(unittest.TestCase):
    def test_pair_and_heartbeat_use_only_approved_routes_and_auth_header(self) -> None:
        node_id = uuid4()
        capability = capability_identity(str(node_id))
        pairing_request = PairingCompleteRequest(
            pairing_code="p_" + "a" * 32 + "." + "b" * 43,
            access_node_id=node_id,
            capability_identity=capability,
        )
        paired_payload = {
            "protocol_version": 1,
            "access_node_id": str(node_id),
            "credential_id": "c_" + "c" * 32,
            "credential_version": 1,
            "credential_token": "d" * 43,
            "status": "paired",
        }
        credential = StoredCredential(
            access_node_id=str(node_id),
            credential_id=paired_payload["credential_id"],
            credential_version=1,
            token=paired_payload["credential_token"],
        )
        heartbeat_payload = {
            "protocol_version": 1,
            "access_node_id": str(node_id),
            "credential_id": credential.credential_id,
            "credential_version": 1,
            "credential_status": "active",
            "helper_version": "0.2.0",
            "last_seen_at": None,
            "heartbeat_status": "accepted",
        }
        requests = []

        def fake_urlopen(request, timeout):
            requests.append(request)
            return _Response(paired_payload if request.full_url.endswith("/pair") else heartbeat_payload)

        client = HelperApiClient()
        with patch("photo_organizer_windows_helper.client.urlopen", side_effect=fake_urlopen):
            client.pair(pairing_request)
            client.heartbeat(
                credential,
                HelperHeartbeatRequest(
                    access_node_id=node_id,
                    capability_identity=capability,
                ),
            )
        self.assertEqual(requests[0].full_url, HELPER_BASE_URL + "/pair")
        self.assertIsNone(requests[0].get_header("Authorization"))
        self.assertEqual(requests[1].full_url, HELPER_BASE_URL + "/heartbeat")
        self.assertEqual(
            requests[1].get_header("Authorization"),
            f"PhotoOrganizerHelper {credential.credential_id}.{credential.token}",
        )

    def test_client_rejects_any_nonapproved_base_or_path(self) -> None:
        with self.assertRaises(ValueError):
            HelperApiClient("http://example.invalid/api/helper/v1")
        client = HelperApiClient()
        with self.assertRaises(ValueError):
            client._request("GET", "/api/admin/status")


if __name__ == "__main__":
    unittest.main()
