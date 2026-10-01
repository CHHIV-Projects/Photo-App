from __future__ import annotations

import io
import json
import unittest
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import uuid4

from photo_organizer_windows_helper.cli import _serve, run
from photo_organizer_windows_helper.credential_store import StoredCredential
from windows_helper_shared.channel import (
    ClaimedAcquireOperation,
    HelperOperationClaimResponse,
    HelperSessionResponse,
    PairingCompleteResponse,
)
from windows_helper_shared.protocol import HelperAcquireItemRequest


class CliRedactionTests(unittest.TestCase):
    def test_pair_output_never_contains_pairing_or_credential_secret(self) -> None:
        node_id = uuid4()
        pairing_secret = "p_" + "a" * 32 + "." + "b" * 43
        credential_secret = "c" * 43
        response = PairingCompleteResponse(
            access_node_id=node_id,
            credential_id="c_" + "d" * 32,
            credential_version=1,
            credential_token=credential_secret,
        )
        store = MagicMock()
        output = io.StringIO()
        with patch("photo_organizer_windows_helper.cli.DpapiCredentialStore", return_value=store), patch(
            "photo_organizer_windows_helper.cli.getpass.getpass", return_value=pairing_secret
        ), patch("photo_organizer_windows_helper.cli.TunnelManager"), patch(
            "photo_organizer_windows_helper.cli.HelperApiClient"
        ) as client_type, patch("sys.stdout", output):
            client_type.return_value.pair.return_value = response
            result = run(["pair", "--access-node-id", str(node_id)])
        self.assertEqual(result, 0)
        self.assertNotIn(pairing_secret, output.getvalue())
        self.assertNotIn(credential_secret, output.getvalue())
        saved = store.save.call_args.args[0]
        self.assertEqual(saved.token, credential_secret)

    def test_status_is_redacted_and_forget_does_not_claim_server_revocation(self) -> None:
        node_id = uuid4()
        raw_token = "raw-token-not-for-output"
        credential = StoredCredential(
            access_node_id=str(node_id),
            credential_id="c_public",
            credential_version=1,
            token=raw_token,
        )
        store = MagicMock()
        store.load.return_value = credential
        store.forget.return_value = True
        status = HelperSessionResponse(
            access_node_id=node_id,
            credential_id="c_public",
            credential_version=1,
            helper_version="0.2.0",
        )
        output = io.StringIO()
        with patch("photo_organizer_windows_helper.cli.DpapiCredentialStore", return_value=store), patch(
            "photo_organizer_windows_helper.cli.TunnelManager"
        ), patch("photo_organizer_windows_helper.cli.HelperApiClient") as client_type, patch(
            "sys.stdout", output
        ):
            client_type.return_value.session.return_value = status
            self.assertEqual(run(["status"]), 0)
            self.assertEqual(run(["forget"]), 0)
        self.assertNotIn(raw_token, output.getvalue())
        lines = [json.loads(line) for line in output.getvalue().splitlines()]
        self.assertFalse(lines[-1]["server_revoked"])
        store.forget.assert_called_once()

    def test_failures_print_only_generic_error(self) -> None:
        secret_error = "raw-secret-should-not-print"
        output = io.StringIO()
        with patch("photo_organizer_windows_helper.cli.DpapiCredentialStore") as store_type, patch(
            "sys.stderr", output
        ):
            store_type.return_value.load.side_effect = RuntimeError(secret_error)
            self.assertEqual(run(["status"]), 1)
        self.assertNotIn(secret_error, output.getvalue())
        self.assertEqual(output.getvalue().strip(), "Windows Helper operation failed safely.")

    def test_status_can_write_redacted_windowless_result_file(self) -> None:
        node_id = uuid4()
        store = MagicMock()
        store.load.return_value = StoredCredential(
            access_node_id=str(node_id), credential_id="c_public", credential_version=1,
            token="raw-token-not-for-output",
        )
        response = HelperSessionResponse(
            access_node_id=node_id, credential_id="c_public", credential_version=1,
            helper_version="0.5.4",
        )
        with tempfile.TemporaryDirectory() as directory, patch(
            "photo_organizer_windows_helper.cli.DpapiCredentialStore", return_value=store
        ), patch("photo_organizer_windows_helper.cli.TunnelManager"), patch(
            "photo_organizer_windows_helper.cli.HelperApiClient"
        ) as client_type:
            client_type.return_value.session.return_value = response
            output_path = Path(directory) / "status.json"
            self.assertEqual(run(["status", "--output-file", str(output_path)]), 0)
            result = json.loads(output_path.read_text(encoding="utf-8"))
        self.assertEqual(result["command"], "status")
        self.assertEqual(result["helper_version"], "0.5.4")
        self.assertNotIn("raw-token-not-for-output", json.dumps(result))

    def test_active_child_uses_bounded_adaptive_short_polling(self) -> None:
        credential = StoredCredential(
            access_node_id=str(uuid4()), credential_id="c_public", credential_version=1,
            token="protected-token",
        )
        operation = ClaimedAcquireOperation.model_construct(
            operation_id=uuid4(),
            lease_expires_at=None,
            request=HelperAcquireItemRequest.model_construct(),
        )
        client = MagicMock()
        client.claim_operation.side_effect = [
            HelperOperationClaimResponse(operation=operation),
            HelperOperationClaimResponse(operation=None, poll_after_seconds=2),
            HelperOperationClaimResponse(operation=None, poll_after_seconds=2),
            KeyboardInterrupt(),
        ]
        sleeps: list[float] = []
        with patch(
            "photo_organizer_windows_helper.cli.execute_acquisition",
            return_value=MagicMock(),
        ), patch("photo_organizer_windows_helper.cli.time.sleep", side_effect=sleeps.append):
            self.assertEqual(_serve(client, credential), 0)
        self.assertEqual(sleeps, [0.05, 0.1])
        self.assertNotIn(2, sleeps)

    def test_windowless_status_failure_writes_only_bounded_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory, patch(
            "photo_organizer_windows_helper.cli.DpapiCredentialStore"
        ) as store_type:
            store_type.return_value.load.side_effect = RuntimeError("sensitive detail")
            output_path = Path(directory) / "status.json"
            self.assertEqual(run(["status", "--output-file", str(output_path)]), 1)
            result = json.loads(output_path.read_text(encoding="utf-8"))
        self.assertEqual(
            result,
            {
                "command": "status",
                "error_code": "status_check_failed",
                "status": "failed",
            },
        )


if __name__ == "__main__":
    unittest.main()
