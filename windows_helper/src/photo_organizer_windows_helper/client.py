"""Small HTTP/JSON client restricted to the Helper API namespace."""

from __future__ import annotations

import json
import re
from typing import Any
from uuid import UUID
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from windows_helper_shared.channel import (
    HelperHeartbeatRequest,
    HelperHeartbeatResponse,
    HelperOperationClaimResponse,
    HelperOperationCompletionResponse,
    HelperOperationFailureRequest,
    HelperOperationFailureResponse,
    HelperSessionResponse,
    PairingCompleteRequest,
    PairingCompleteResponse,
)
from windows_helper_shared.protocol import (
    HelperInventoryPageResponse,
    HelperProbeResponse,
)

from .credential_store import StoredCredential


HELPER_BASE_URL = "http://127.0.0.1:18011/api/helper/v1"


class HelperClientError(RuntimeError):
    pass


class HelperApiClient:
    def __init__(self, base_url: str = HELPER_BASE_URL, *, timeout_seconds: float = 10.0) -> None:
        if base_url.rstrip("/") != HELPER_BASE_URL:
            raise ValueError("The Helper API target must be the approved loopback ingress.")
        self.base_url = HELPER_BASE_URL
        self.timeout_seconds = timeout_seconds

    def pair(self, request: PairingCompleteRequest) -> PairingCompleteResponse:
        payload = self._request("POST", "/pair", request.model_dump(mode="json"))
        return PairingCompleteResponse.model_validate(payload)

    def session(self, credential: StoredCredential) -> HelperSessionResponse:
        payload = self._request("GET", "/session", credential=credential)
        return HelperSessionResponse.model_validate(payload)

    def heartbeat(
        self,
        credential: StoredCredential,
        request: HelperHeartbeatRequest,
    ) -> HelperHeartbeatResponse:
        payload = self._request(
            "POST",
            "/heartbeat",
            request.model_dump(mode="json"),
            credential=credential,
        )
        return HelperHeartbeatResponse.model_validate(payload)

    def claim_operation(
        self,
        credential: StoredCredential,
    ) -> HelperOperationClaimResponse:
        payload = self._request("POST", "/operations/claim", {}, credential=credential)
        return HelperOperationClaimResponse.model_validate(payload)

    def complete_probe(
        self,
        credential: StoredCredential,
        operation_id: UUID,
        result: HelperProbeResponse,
    ) -> HelperOperationCompletionResponse:
        payload = self._request(
            "POST",
            f"/operations/{operation_id}/complete-probe",
            result.model_dump(mode="json"),
            credential=credential,
        )
        return HelperOperationCompletionResponse.model_validate(payload)

    def complete_inventory(
        self,
        credential: StoredCredential,
        operation_id: UUID,
        result: HelperInventoryPageResponse,
    ) -> HelperOperationCompletionResponse:
        payload = self._request(
            "POST",
            f"/operations/{operation_id}/complete-inventory",
            result.model_dump(mode="json"),
            credential=credential,
        )
        return HelperOperationCompletionResponse.model_validate(payload)

    def fail_operation(
        self,
        credential: StoredCredential,
        operation_id: UUID,
        error_code: str,
    ) -> HelperOperationFailureResponse:
        request = HelperOperationFailureRequest(error_code=error_code)
        payload = self._request(
            "POST",
            f"/operations/{operation_id}/fail",
            request.model_dump(mode="json"),
            credential=credential,
        )
        return HelperOperationFailureResponse.model_validate(payload)

    def _request(
        self,
        method: str,
        path: str,
        body: dict[str, Any] | None = None,
        *,
        credential: StoredCredential | None = None,
    ) -> dict[str, Any]:
        static_paths = {"/pair", "/session", "/heartbeat", "/operations/claim"}
        operation_path = re.fullmatch(
            r"/operations/[0-9a-fA-F-]{36}/(complete-probe|complete-inventory|fail)",
            path,
        )
        if path not in static_paths and operation_path is None:
            raise ValueError("Unsupported Helper API path.")
        headers = {"Accept": "application/json"}
        data = None
        if body is not None:
            data = json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
            headers["Content-Type"] = "application/json"
        if credential is not None:
            headers["Authorization"] = (
                f"PhotoOrganizerHelper {credential.credential_id}.{credential.token}"
            )
        request = Request(self.base_url + path, data=data, headers=headers, method=method)
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            raise HelperClientError(f"Helper API request failed with HTTP {exc.code}.") from None
        except (URLError, TimeoutError, json.JSONDecodeError):
            raise HelperClientError("Helper API request failed.") from None
        if not isinstance(payload, dict):
            raise HelperClientError("Helper API response was invalid.")
        return payload
