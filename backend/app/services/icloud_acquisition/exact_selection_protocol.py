"""Secret-free JSON contract for the isolated iCloud exact-selection helper."""

from __future__ import annotations

import base64
from pathlib import PurePosixPath
import re
from typing import Any


PROTOCOL_VERSION = 1
OPERATION_AUTH_STATUS = "auth_status"
OPERATION_LIST = "list"
OPERATION_DOWNLOAD_SELECTED = "download_selected"
SUPPORTED_OPERATIONS = {
    OPERATION_AUTH_STATUS,
    OPERATION_LIST,
    OPERATION_DOWNLOAD_SELECTED,
}

MAX_CANDIDATE_SCAN_LIMIT = 500
MAX_SELECTED_ITEM_COUNT = 500
MAX_RESOURCES_PER_ITEM = 8
MAX_HELPER_JSON_BYTES = 5_000_000

RESOURCE_PRIMARY_ORIGINAL = "primary_original"
RESOURCE_LIVE_PHOTO_ORIGINAL = "live_photo_original"

AUTHENTICATED = "authenticated"
AUTHENTICATION_REQUIRED = "authentication_required"
SESSION_EXPIRED = "session_expired"
REAUTHENTICATION_REQUIRED = "reauthentication_required"
AUTHENTICATION_FAILED = "authentication_failed"
HELPER_UNAVAILABLE = "helper_unavailable"

_RUN_TOKEN = re.compile(r"^[a-f0-9]{16,64}$")


class ExactSelectionProtocolError(ValueError):
    def __init__(self, message: str, *, code: str = "invalid_request") -> None:
        super().__init__(message)
        self.code = code


def _required_string(
    payload: dict[str, Any],
    field: str,
    *,
    max_length: int,
) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ExactSelectionProtocolError(f"{field} is required.")
    cleaned = value.strip()
    if len(cleaned) > max_length or any(char in cleaned for char in ("\x00", "\r", "\n")):
        raise ExactSelectionProtocolError(f"{field} is invalid.")
    return cleaned


def normalize_relative_resource_path(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ExactSelectionProtocolError("relative_path is required.")
    normalized = value.strip().replace("\\", "/")
    path = PurePosixPath(normalized)
    if (
        path.is_absolute()
        or normalized.startswith("/")
        or any(":" in part for part in path.parts)
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        raise ExactSelectionProtocolError("relative_path must remain inside staging.")
    if len(normalized) > 2048:
        raise ExactSelectionProtocolError("relative_path is too long.")
    return path.as_posix()


def _candidate_scan_limit(payload: dict[str, Any]) -> int:
    value = payload.get("candidate_scan_limit")
    if not isinstance(value, int) or isinstance(value, bool):
        raise ExactSelectionProtocolError("candidate_scan_limit must be an integer.")
    if value < 1 or value > MAX_CANDIDATE_SCAN_LIMIT:
        raise ExactSelectionProtocolError(
            f"candidate_scan_limit must be between 1 and {MAX_CANDIDATE_SCAN_LIMIT}."
        )
    return value


def validate_helper_request(payload: object) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ExactSelectionProtocolError("The helper request must be a JSON object.")
    if payload.get("protocol_version") != PROTOCOL_VERSION:
        raise ExactSelectionProtocolError(
            "Unsupported exact-selection protocol version.",
            code="unsupported_protocol_version",
        )

    operation = payload.get("operation")
    if operation not in SUPPORTED_OPERATIONS:
        raise ExactSelectionProtocolError("Unsupported helper operation.")

    cleaned: dict[str, Any] = {
        "protocol_version": PROTOCOL_VERSION,
        "operation": operation,
        "account_username": _required_string(
            payload,
            "account_username",
            max_length=255,
        ),
    }
    if operation == OPERATION_AUTH_STATUS:
        return cleaned

    cleaned["library"] = _required_string(payload, "library", max_length=255)
    cleaned["candidate_scan_limit"] = _candidate_scan_limit(payload)
    if operation == OPERATION_LIST:
        return cleaned

    staging_root = _required_string(payload, "staging_root", max_length=2048)
    run_token = _required_string(payload, "run_token", max_length=64)
    if _RUN_TOKEN.fullmatch(run_token) is None:
        raise ExactSelectionProtocolError("run_token is invalid.")

    selected_items = payload.get("selected_items")
    if not isinstance(selected_items, list) or not selected_items:
        raise ExactSelectionProtocolError("selected_items must be a non-empty list.")
    if len(selected_items) > MAX_SELECTED_ITEM_COUNT:
        raise ExactSelectionProtocolError("selected_items exceeds the bounded maximum.")

    cleaned_items: list[dict[str, Any]] = []
    seen_item_ids: set[str] = set()
    for item_value in selected_items:
        if not isinstance(item_value, dict):
            raise ExactSelectionProtocolError("Each selected item must be an object.")
        item_id = _required_string(item_value, "item_id", max_length=512)
        if item_id in seen_item_ids:
            raise ExactSelectionProtocolError("selected_items contains a duplicate item_id.")
        seen_item_ids.add(item_id)

        resources = item_value.get("resources")
        if not isinstance(resources, list) or not resources:
            raise ExactSelectionProtocolError("Each selected item requires resources.")
        if len(resources) > MAX_RESOURCES_PER_ITEM:
            raise ExactSelectionProtocolError("An item contains too many resources.")

        cleaned_resources: list[dict[str, Any]] = []
        seen_resource_ids: set[str] = set()
        for resource_value in resources:
            if not isinstance(resource_value, dict):
                raise ExactSelectionProtocolError("Each selected resource must be an object.")
            resource_id = _required_string(resource_value, "resource_id", max_length=128)
            if resource_id in seen_resource_ids:
                raise ExactSelectionProtocolError("An item contains a duplicate resource_id.")
            seen_resource_ids.add(resource_id)

            expected_size = resource_value.get("expected_size")
            if (
                not isinstance(expected_size, int)
                or isinstance(expected_size, bool)
                or expected_size < 0
            ):
                raise ExactSelectionProtocolError(
                    "expected_size must be a non-negative integer."
                )
            expected_checksum = _required_string(
                resource_value,
                "expected_checksum",
                max_length=256,
            )
            try:
                decoded_checksum = base64.b64decode(expected_checksum, validate=True)
            except (ValueError, TypeError) as exc:
                raise ExactSelectionProtocolError(
                    "expected_checksum must be valid base64."
                ) from exc
            if len(decoded_checksum) not in {16, 20, 32}:
                raise ExactSelectionProtocolError(
                    "expected_checksum uses an unsupported digest."
                )

            cleaned_resources.append(
                {
                    "resource_id": resource_id,
                    "relative_path": normalize_relative_resource_path(
                        resource_value.get("relative_path")
                    ),
                    "expected_size": expected_size,
                    "expected_checksum": expected_checksum,
                }
            )
        cleaned_items.append({"item_id": item_id, "resources": cleaned_resources})

    cleaned.update(
        {
            "staging_root": staging_root,
            "run_token": run_token,
            "selected_items": cleaned_items,
        }
    )
    return cleaned


def helper_failure(operation: object, code: str) -> dict[str, Any]:
    return {
        "protocol_version": PROTOCOL_VERSION,
        "operation": operation if operation in SUPPORTED_OPERATIONS else "unknown",
        "status": "failed",
        "error_code": code,
    }
