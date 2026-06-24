from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from datetime import UTC, datetime
from unittest.mock import patch

from app.services.icloud_acquisition.exact_selection_protocol import (
    AUTHENTICATED,
    OPERATION_AUTH_STATUS,
    OPERATION_DOWNLOAD_SELECTED,
    OPERATION_LIST,
    PROTOCOL_VERSION,
)
from app.services.icloud_acquisition.icloud_exact_selection_helper import (
    IcloudpdInternalProvider,
    SafeHelperError,
    execute_download_selected,
    execute_list,
    handle_request,
)
from app.services.icloud_acquisition import icloud_exact_selection_helper as helper_module


def _checksum(content: bytes) -> str:
    return base64.b64encode(hashlib.sha1(content).digest()).decode("ascii")


def _resource(resource_id: str, relative_path: str, content: bytes) -> dict[str, object]:
    return {
        "resource_id": resource_id,
        "role": (
            "primary_original"
            if resource_id == "primary_original"
            else "live_photo_motion"
        ),
        "relative_path": relative_path,
        "expected_size": len(content),
        "expected_checksum": _checksum(content),
        "content_type": "application/octet-stream",
    }


def _asset(
    item_id: str,
    resources: list[dict[str, object]],
    *,
    identity_ambiguous: bool = False,
    unsupported_reasons: list[str] | None = None,
) -> dict[str, object]:
    return {
        "descriptor": {
            "item_id": item_id,
            "created_at": "2026-06-24T10:00:00+00:00",
            "added_at": "2026-06-24T10:01:00+00:00",
            "grouping": (
                "live_photo_explicit" if len(resources) > 1 else "primary_asset_explicit"
            ),
            "identity_ambiguous": identity_ambiguous,
            "unsupported_reasons": unsupported_reasons or [],
            "resources": resources,
        }
    }


class _FakeResponse:
    def __init__(self, content: bytes, *, ok: bool = True) -> None:
        self.content = content
        self.ok = ok
        self.closed = False

    def iter_content(self, chunk_size: int):
        del chunk_size
        yield self.content

    def close(self) -> None:
        self.closed = True


class _FakeProvider:
    auth_state = AUTHENTICATED

    def __init__(
        self,
        assets: list[dict[str, object]],
        content_by_resource: dict[tuple[str, str], bytes],
    ) -> None:
        self.assets = assets
        self.content_by_resource = content_by_resource
        self.opened: list[tuple[str, str]] = []
        self.responses: list[_FakeResponse] = []

    def iter_assets(self, limit: int):
        return iter(self.assets[:limit])

    def describe_asset(self, asset: dict[str, object]) -> dict[str, object]:
        return asset["descriptor"]  # type: ignore[return-value]

    def open_resource(
        self,
        asset: dict[str, object],
        resource_id: str,
    ) -> _FakeResponse:
        descriptor = asset["descriptor"]
        item_id = descriptor["item_id"]  # type: ignore[index]
        key = (str(item_id), resource_id)
        self.opened.append(key)
        response = _FakeResponse(self.content_by_resource[key])
        self.responses.append(response)
        return response


def _download_request(
    staging_root: Path,
    item_id: str,
    resources: list[dict[str, object]],
) -> dict[str, object]:
    return {
        "protocol_version": PROTOCOL_VERSION,
        "operation": OPERATION_DOWNLOAD_SELECTED,
        "account_username": "fixture@example.com",
        "library": "PrimarySync",
        "candidate_scan_limit": 10,
        "staging_root": str(staging_root),
        "run_token": "0123456789abcdef",
        "selected_items": [
            {
                "item_id": item_id,
                "resources": [
                    {
                        "resource_id": resource["resource_id"],
                        "relative_path": resource["relative_path"],
                        "expected_size": resource["expected_size"],
                        "expected_checksum": resource["expected_checksum"],
                    }
                    for resource in resources
                ],
            }
        ],
    }


class IcloudExactSelectionHelperTests(unittest.TestCase):
    def test_pinned_provider_mapping_exposes_explicit_live_photo_resources(self) -> None:
        provider = object.__new__(IcloudpdInternalProvider)
        provider._asset_original = "original"
        provider._asset_alternative = "alternative"
        provider._live_original = "live_original"
        provider._live_filename = lambda name: name
        provider._filename_builder = lambda asset: asset.filename
        provider._calculate_version_filename = (
            lambda base, version, size, live_builder, item_type: (
                base if size == "original" else "IMG_500_HEVC.MOV"
            )
        )
        still = b"provider-still"
        motion = b"provider-motion"
        asset = SimpleNamespace(
            id="remote-provider-live",
            filename="IMG_500.HEIC",
            created=datetime(2026, 6, 24, 10, 0, tzinfo=UTC),
            added_date=datetime(2026, 6, 24, 10, 1, tzinfo=UTC),
            item_type="image",
            versions={
                "original": SimpleNamespace(
                    size=len(still),
                    checksum=_checksum(still),
                    type="image/heic",
                ),
                "live_original": SimpleNamespace(
                    size=len(motion),
                    checksum=_checksum(motion),
                    type="video/quicktime",
                ),
            },
            _master_record={"fields": {}},
            _asset_record={"fields": {}},
        )

        descriptor = provider.describe_asset(asset)

        self.assertEqual(descriptor["grouping"], "live_photo_explicit")
        self.assertFalse(descriptor["identity_ambiguous"])
        self.assertEqual(
            [resource["resource_id"] for resource in descriptor["resources"]],
            ["primary_original", "live_photo_original"],
        )
        self.assertEqual(
            [resource["relative_path"] for resource in descriptor["resources"]],
            ["2026/06/24/IMG_500.HEIC", "2026/06/24/IMG_500_HEVC.MOV"],
        )

        asset._asset_record = {
            "fields": {
                "adjustmentType": {"value": ["unhashable", "but-present"]},
                "resSidecarRes": {"value": {"remote": "metadata"}},
            }
        }
        asset.versions["alternative"] = SimpleNamespace()
        blocked = provider.describe_asset(asset)
        self.assertTrue(blocked["identity_ambiguous"])
        self.assertEqual(
            blocked["unsupported_reasons"],
            [
                "unsupported_adjusted_resource",
                "unsupported_raw_or_alternative",
                "unsupported_remote_sidecar",
            ],
        )

    def test_listing_is_bounded_and_reports_item_and_resource_counts(self) -> None:
        still = b"still"
        motion = b"motion"
        assets = [
            _asset(
                "remote-live-1",
                [
                    _resource("primary_original", "2026/06/24/IMG_1.HEIC", still),
                    _resource(
                        "live_photo_original",
                        "2026/06/24/IMG_1_HEVC.MOV",
                        motion,
                    ),
                ],
            ),
            _asset(
                "remote-still-2",
                [_resource("primary_original", "2026/06/23/IMG_2.JPG", still)],
            ),
            _asset(
                "remote-still-3",
                [_resource("primary_original", "2026/06/22/IMG_3.JPG", still)],
            ),
        ]
        provider = _FakeProvider(assets, {})

        response = execute_list(
            {
                "protocol_version": PROTOCOL_VERSION,
                "operation": OPERATION_LIST,
                "account_username": "fixture@example.com",
                "library": "PrimarySync",
                "candidate_scan_limit": 2,
            },
            provider,
        )

        self.assertEqual(response["logical_item_count"], 2)
        self.assertEqual(response["resource_file_count"], 3)
        self.assertTrue(response["scan_limit_reached"])
        self.assertFalse(response["source_exhausted"])
        self.assertEqual(response["stop_reason"], "scan_limit_reached")

    def test_exact_download_avoids_known_live_photo_sibling(self) -> None:
        still = b"known-still"
        motion = b"unknown-motion"
        primary = _resource("primary_original", "2026/06/24/IMG_10.HEIC", still)
        live = _resource(
            "live_photo_original",
            "2026/06/24/IMG_10_HEVC.MOV",
            motion,
        )
        remote_id = "remote-identifier-must-not-return"
        provider = _FakeProvider(
            [_asset(remote_id, [primary, live])],
            {(remote_id, "live_photo_original"): motion},
        )
        partial_destinations: list[Path] = []
        original_download_verified = helper_module._download_verified

        def capture_partial_destination(response, destination, **kwargs):
            partial_destinations.append(destination)
            return original_download_verified(response, destination, **kwargs)

        with tempfile.TemporaryDirectory() as temporary_root:
            exports_root = Path(temporary_root)
            staging_root = exports_root / "profile"
            staging_root.mkdir()
            with patch.object(
                helper_module,
                "_download_verified",
                side_effect=capture_partial_destination,
            ):
                response = execute_download_selected(
                    _download_request(staging_root, remote_id, [live]),
                    provider,
                    approved_exports_root=exports_root,
                )

            self.assertEqual(
                provider.opened,
                [(remote_id, "live_photo_original")],
            )
            self.assertFalse((staging_root / str(primary["relative_path"])).exists())
            self.assertEqual(
                (staging_root / str(live["relative_path"])).read_bytes(),
                motion,
            )
            self.assertEqual(response["downloaded_item_count"], 1)
            self.assertEqual(response["downloaded_resource_count"], 1)
            self.assertNotIn(remote_id, json.dumps(response))
            self.assertTrue(all(result.closed for result in provider.responses))
            self.assertEqual(len(partial_destinations), 1)
            self.assertTrue(partial_destinations[0].name.endswith(".partial"))
            self.assertEqual(partial_destinations[0].relative_to(staging_root).parts[0], ".partial")

    def test_item_checksum_failure_publishes_no_sibling_resources(self) -> None:
        still = b"verified-still"
        expected_motion = b"expected-motion"
        wrong_motion = b"wrong---motion"
        primary = _resource("primary_original", "2026/06/24/IMG_20.HEIC", still)
        live = _resource(
            "live_photo_original",
            "2026/06/24/IMG_20_HEVC.MOV",
            expected_motion,
        )
        remote_id = "remote-live-failure"
        provider = _FakeProvider(
            [_asset(remote_id, [primary, live])],
            {
                (remote_id, "primary_original"): still,
                (remote_id, "live_photo_original"): wrong_motion,
            },
        )

        with tempfile.TemporaryDirectory() as temporary_root:
            exports_root = Path(temporary_root)
            staging_root = exports_root / "profile"
            staging_root.mkdir()
            response = execute_download_selected(
                _download_request(staging_root, remote_id, [primary, live]),
                provider,
                approved_exports_root=exports_root,
            )

            self.assertEqual(response["status"], "failed")
            self.assertEqual(response["downloaded_item_count"], 0)
            self.assertEqual(response["downloaded_resource_count"], 0)
            self.assertFalse((staging_root / str(primary["relative_path"])).exists())
            self.assertFalse((staging_root / str(live["relative_path"])).exists())
            self.assertFalse(any(path.is_file() for path in staging_root.rglob("*.partial")))
            self.assertTrue(all(result.closed for result in provider.responses))

    def test_protocol_rejects_path_traversal_before_provider_creation(self) -> None:
        provider_called = False

        def provider_factory(**kwargs):
            nonlocal provider_called
            provider_called = True
            raise AssertionError(kwargs)

        payload = _download_request(
            Path("C:/safe"),
            "remote-item",
            [_resource("primary_original", "2026/06/24/IMG_30.JPG", b"photo")],
        )
        payload["selected_items"][0]["resources"][0]["relative_path"] = "../escape.jpg"  # type: ignore[index]

        response = handle_request(payload, provider_factory=provider_factory)

        self.assertEqual(response["status"], "failed")
        self.assertEqual(response["error_code"], "invalid_request")
        self.assertFalse(provider_called)

    def test_auth_failure_is_reduced_to_safe_state(self) -> None:
        def provider_factory(**kwargs):
            del kwargs
            raise SafeHelperError("session_expired")

        response = handle_request(
            {
                "protocol_version": PROTOCOL_VERSION,
                "operation": OPERATION_AUTH_STATUS,
                "account_username": "fixture@example.com",
            },
            provider_factory=provider_factory,
        )

        self.assertEqual(
            response,
            {
                "protocol_version": PROTOCOL_VERSION,
                "operation": OPERATION_AUTH_STATUS,
                "status": "blocked",
                "auth_state": "session_expired",
                "error_code": "session_expired",
            },
        )
        self.assertNotIn("password", json.dumps(response).casefold())


if __name__ == "__main__":
    unittest.main()
