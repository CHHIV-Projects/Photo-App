"""Standalone isolated helper for exact selected iCloud acquisition.

The helper runs inside ``.tools/icloud_exact_helper``. It reads one bounded
JSON request from stdin and writes one secret-free JSON response to stdout.
Apple credentials, keyring values, cookies, sessions, tokens, and raw download
URLs never cross this process boundary.
"""

from __future__ import annotations

from contextlib import redirect_stdout
from datetime import datetime
import hashlib
import itertools
import json
import logging
import os
from pathlib import Path
import shutil
import sys
from typing import Any, Callable, Iterable, Protocol

try:
    from .exact_selection_protocol import (
        AUTHENTICATED,
        AUTHENTICATION_FAILED,
        AUTHENTICATION_REQUIRED,
        HELPER_UNAVAILABLE,
        MAX_HELPER_JSON_BYTES,
        OPERATION_AUTH_STATUS,
        OPERATION_DOWNLOAD_SELECTED,
        OPERATION_LIST,
        PROTOCOL_VERSION,
        REAUTHENTICATION_REQUIRED,
        RESOURCE_LIVE_PHOTO_ORIGINAL,
        RESOURCE_PRIMARY_ORIGINAL,
        SESSION_EXPIRED,
        ExactSelectionProtocolError,
        decode_verification_checksum,
        helper_failure,
        normalize_relative_resource_path,
        validate_helper_request,
    )
except ImportError:  # pragma: no cover - standalone helper execution
    from exact_selection_protocol import (  # type: ignore[no-redef]
        AUTHENTICATED,
        AUTHENTICATION_FAILED,
        AUTHENTICATION_REQUIRED,
        HELPER_UNAVAILABLE,
        MAX_HELPER_JSON_BYTES,
        OPERATION_AUTH_STATUS,
        OPERATION_DOWNLOAD_SELECTED,
        OPERATION_LIST,
        PROTOCOL_VERSION,
        REAUTHENTICATION_REQUIRED,
        RESOURCE_LIVE_PHOTO_ORIGINAL,
        RESOURCE_PRIMARY_ORIGINAL,
        SESSION_EXPIRED,
        ExactSelectionProtocolError,
        decode_verification_checksum,
        helper_failure,
        normalize_relative_resource_path,
        validate_helper_request,
    )


logging.disable(logging.CRITICAL)


class SafeHelperError(RuntimeError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class DownloadResponse(Protocol):
    ok: bool

    def iter_content(self, chunk_size: int) -> Iterable[bytes]: ...

    def close(self) -> None: ...


class ExactSelectionProvider(Protocol):
    auth_state: str

    def iter_assets(self, limit: int) -> Iterable[object]: ...

    def describe_asset(self, asset: object) -> dict[str, Any]: ...

    def open_resource(self, asset: object, resource_id: str) -> DownloadResponse: ...


def _auth_directory() -> Path:
    configured = (os.environ.get("PHOTO_ORGANIZER_ICLOUD_EXACT_AUTH_DIR") or "").strip()
    if configured:
        auth_root = Path(configured).expanduser()
    else:
        local_app_data = (os.environ.get("LOCALAPPDATA") or "").strip()
        if not local_app_data:
            raise SafeHelperError(HELPER_UNAVAILABLE)
        auth_root = Path(local_app_data) / "PhotoOrganizer" / "icloud_exact_helper" / "auth"
    try:
        auth_root.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise SafeHelperError(HELPER_UNAVAILABLE) from exc
    return auth_root.resolve()


class IcloudpdInternalProvider:
    """Narrow wrapper around the pinned official icloudpd source APIs."""

    def __init__(
        self,
        *,
        account_username: str,
        library: str | None,
    ) -> None:
        try:
            from icloudpd.base import build_filename_cleaner, lp_filename_concatinator
            from icloudpd.filename_policies import create_filename_builder
            from pyicloud_ipd.asset_version import calculate_version_filename
            from pyicloud_ipd.base import PyiCloudService
            from pyicloud_ipd.exceptions import (
                PyiCloud2SARequiredException,
                PyiCloudAPIResponseException,
                PyiCloudConnectionErrorException,
                PyiCloudFailedLoginException,
                PyiCloudFailedMFAException,
                PyiCloudNoStoredPasswordAvailableException,
                PyiCloudServiceUnavailableException,
            )
            from pyicloud_ipd.file_match import FileMatchPolicy
            from pyicloud_ipd.utils import get_password_from_keyring
            from pyicloud_ipd.version_size import AssetVersionSize, LivePhotoVersionSize
        except ImportError as exc:
            raise SafeHelperError(HELPER_UNAVAILABLE) from exc

        self._asset_original = AssetVersionSize.ORIGINAL
        self._asset_alternative = AssetVersionSize.ALTERNATIVE
        self._asset_adjusted = AssetVersionSize.ADJUSTED
        self._live_original = LivePhotoVersionSize.ORIGINAL
        self._live_filename = lp_filename_concatinator
        self._calculate_version_filename = calculate_version_filename
        self._filename_builder = create_filename_builder(
            FileMatchPolicy.NAME_SIZE_DEDUP_WITH_SUFFIX,
            build_filename_cleaner(False),
        )

        normalized_username = account_username.strip().lower()

        def password_provider() -> str | None:
            return get_password_from_keyring(normalized_username)

        try:
            self._icloud = PyiCloudService(
                "com",
                normalized_username,
                password_provider,
                None,
                cookie_directory=str(_auth_directory()),
                client_id=os.environ.get("CLIENT_ID"),
                http_timeout=30.0,
            )
            if not getattr(self._icloud, "data", None):
                raise SafeHelperError(AUTHENTICATION_REQUIRED)
            if self._icloud.requires_2fa or self._icloud.requires_2sa:
                raise SafeHelperError(REAUTHENTICATION_REQUIRED)
        except SafeHelperError:
            raise
        except PyiCloudNoStoredPasswordAvailableException as exc:
            raise SafeHelperError(AUTHENTICATION_REQUIRED) from exc
        except (PyiCloud2SARequiredException, PyiCloudFailedMFAException) as exc:
            raise SafeHelperError(REAUTHENTICATION_REQUIRED) from exc
        except PyiCloudFailedLoginException as exc:
            raise SafeHelperError(AUTHENTICATION_FAILED) from exc
        except (PyiCloudConnectionErrorException, PyiCloudServiceUnavailableException) as exc:
            raise SafeHelperError("network_error") from exc
        except PyiCloudAPIResponseException as exc:
            raise SafeHelperError(SESSION_EXPIRED) from exc
        except Exception as exc:  # noqa: BLE001 - never expose provider exception text
            raise SafeHelperError(HELPER_UNAVAILABLE) from exc

        self.auth_state = AUTHENTICATED
        self._library = None
        if library is not None:
            try:
                photos = self._icloud.photos
                if library == "PrimarySync":
                    self._library = photos
                elif library in photos.private_libraries:
                    self._library = photos.private_libraries[library]
                elif library in photos.shared_libraries:
                    self._library = photos.shared_libraries[library]
                else:
                    raise SafeHelperError("library_unavailable")
            except SafeHelperError:
                raise
            except Exception as exc:  # noqa: BLE001
                raise SafeHelperError("icloud_service_unavailable") from exc

    def iter_assets(self, limit: int) -> Iterable[object]:
        if self._library is None:
            raise SafeHelperError("library_unavailable")
        return itertools.islice(self._library.all, limit)

    @staticmethod
    def _record_fields(asset: object) -> list[dict[str, Any]]:
        fields: list[dict[str, Any]] = []
        for record_name in ("_master_record", "_asset_record"):
            record = getattr(asset, record_name, {})
            record_fields = record.get("fields", {}) if isinstance(record, dict) else {}
            if isinstance(record_fields, dict):
                fields.append(record_fields)
        return fields

    @staticmethod
    def _field_has_value(fields: list[dict[str, Any]], field_name: str) -> bool:
        for record_fields in fields:
            entry = record_fields.get(field_name)
            if isinstance(entry, dict):
                value = entry.get("value")
                if value is not None and value != "" and value != 0 and value is not False:
                    return True
        return False

    @staticmethod
    def _checksum_supported(value: object) -> bool:
        try:
            decode_verification_checksum(value)
        except ExactSelectionProtocolError:
            return False
        return True

    def describe_asset(self, asset: object) -> dict[str, Any]:
        try:
            item_id = str(getattr(asset, "id")).strip()
            versions = getattr(asset, "versions")
            created = getattr(asset, "created")
            added = getattr(asset, "added_date")
            base_filename = self._filename_builder(asset)
        except Exception as exc:  # noqa: BLE001
            raise SafeHelperError("identity_unavailable") from exc

        resources: list[dict[str, Any]] = []
        if self._asset_original in versions:
            resources.append(
                self._describe_version(
                    asset,
                    base_filename,
                    created,
                    RESOURCE_PRIMARY_ORIGINAL,
                    "primary_original",
                    self._asset_original,
                    versions[self._asset_original],
                )
            )
        if self._live_original in versions:
            resources.append(
                self._describe_version(
                    asset,
                    base_filename,
                    created,
                    RESOURCE_LIVE_PHOTO_ORIGINAL,
                    "live_photo_motion",
                    self._live_original,
                    versions[self._live_original],
                )
            )

        fields = self._record_fields(asset)
        unsupported_reasons: list[str] = []
        if any("resSidecarRes" in record_fields for record_fields in fields):
            unsupported_reasons.append("unsupported_remote_sidecar")
        if self._asset_alternative in versions:
            unsupported_reasons.append("unsupported_raw_or_alternative")
        if self._asset_adjusted in versions:
            unsupported_reasons.append("unsupported_adjusted_resource")
        if not item_id or not resources or not any(
            resource["resource_id"] == RESOURCE_PRIMARY_ORIGINAL for resource in resources
        ):
            unsupported_reasons.append("identity_unavailable")
        for resource in resources:
            if resource["expected_size"] < 0 or not self._checksum_supported(
                resource["expected_checksum"]
            ):
                unsupported_reasons.append("verification_metadata_unavailable")
                break

        return {
            "item_id": item_id,
            "created_at": created.isoformat(),
            "added_at": added.isoformat(),
            "grouping": (
                "live_photo_explicit" if len(resources) > 1 else "primary_asset_explicit"
            ),
            "identity_ambiguous": bool(unsupported_reasons),
            "unsupported_reasons": sorted(set(unsupported_reasons)),
            "resources": resources,
        }

    def _describe_version(
        self,
        asset: object,
        base_filename: str,
        created: object,
        resource_id: str,
        role: str,
        version_size: object,
        version: object,
    ) -> dict[str, Any]:
        filename = self._calculate_version_filename(
            base_filename,
            version,
            version_size,
            self._live_filename,
            getattr(asset, "item_type"),
        )
        date_path = getattr(created, "strftime")("%Y/%m/%d")
        return {
            "resource_id": resource_id,
            "role": role,
            "relative_path": normalize_relative_resource_path(f"{date_path}/{filename}"),
            "expected_size": int(getattr(version, "size")),
            "expected_checksum": str(getattr(version, "checksum")),
            "content_type": str(getattr(version, "type")),
        }

    def open_resource(self, asset: object, resource_id: str) -> DownloadResponse:
        versions = getattr(asset, "versions")
        if resource_id == RESOURCE_PRIMARY_ORIGINAL:
            version = versions.get(self._asset_original)
        elif resource_id == RESOURCE_LIVE_PHOTO_ORIGINAL:
            version = versions.get(self._live_original)
        else:
            version = None
        if version is None:
            raise SafeHelperError("resource_unavailable")
        try:
            return getattr(asset, "download")(
                self._icloud.photos.session,
                getattr(version, "url"),
                0,
            )
        except Exception as exc:  # noqa: BLE001
            raise SafeHelperError("download_failed") from exc


def _mark_identity_collisions(items: list[dict[str, Any]]) -> None:
    item_indexes: dict[str, list[int]] = {}
    path_indexes: dict[str, list[int]] = {}
    for index, item in enumerate(items):
        item_indexes.setdefault(str(item.get("item_id", "")), []).append(index)
        item_paths: list[str] = []
        for resource in item.get("resources", []):
            path_key = str(resource.get("relative_path", "")).casefold()
            path_indexes.setdefault(path_key, []).append(index)
            item_paths.append(path_key)
        if len(item_paths) != len(set(item_paths)):
            item["identity_ambiguous"] = True
            reasons = item.setdefault("unsupported_reasons", [])
            if "identity_collision" not in reasons:
                reasons.append("identity_collision")

    collision_indexes = {
        index
        for indexes in list(item_indexes.values()) + list(path_indexes.values())
        if len(set(indexes)) > 1
        for index in indexes
    }
    for index in collision_indexes:
        item = items[index]
        item["identity_ambiguous"] = True
        reasons = item.setdefault("unsupported_reasons", [])
        if "identity_collision" not in reasons:
            reasons.append("identity_collision")


def execute_list(request: dict[str, Any], provider: ExactSelectionProvider) -> dict[str, Any]:
    limit = int(request["candidate_scan_limit"])
    assets = list(provider.iter_assets(limit + 1))
    source_exhausted = len(assets) <= limit
    items = [provider.describe_asset(asset) for asset in assets[:limit]]
    _mark_identity_collisions(items)
    return {
        "protocol_version": PROTOCOL_VERSION,
        "operation": OPERATION_LIST,
        "status": "completed",
        "auth_state": provider.auth_state,
        "stop_reason": "no_more_candidates" if source_exhausted else "scan_limit_reached",
        "source_exhausted": source_exhausted,
        "scan_limit_reached": not source_exhausted,
        "logical_item_count": len(items),
        "resource_file_count": sum(len(item.get("resources", [])) for item in items),
        "ambiguous_item_count": sum(1 for item in items if item.get("identity_ambiguous")),
        "items": items,
    }


def _resolved_child(root: Path, relative_path: str) -> Path:
    root_resolved = root.resolve()
    candidate = (root_resolved / Path(relative_path)).resolve()
    try:
        candidate.relative_to(root_resolved)
    except ValueError as exc:
        raise SafeHelperError("unsafe_staging_path") from exc
    return candidate


def _checksum_hasher(expected_checksum: str) -> tuple[bytes | None, Any | None]:
    try:
        algorithm, expected = decode_verification_checksum(expected_checksum)
    except ExactSelectionProtocolError as exc:
        raise SafeHelperError("verification_metadata_unavailable") from exc
    if algorithm == "icloud_file_checksum":
        return None, None
    algorithms: dict[str, Callable[[], Any]] = {
        "md5": hashlib.md5,  # noqa: S324 - provider digest comparison only
        "sha1": hashlib.sha1,  # noqa: S324 - provider digest comparison only
        "sha256": hashlib.sha256,
    }
    factory = algorithms.get(algorithm)
    if factory is None:
        raise SafeHelperError("verification_metadata_unavailable")
    return expected, factory()


def _download_verified(
    response: DownloadResponse,
    destination: Path,
    *,
    expected_size: int,
    expected_checksum: str,
) -> int:
    if not response.ok:
        response.close()
        raise SafeHelperError("download_failed")
    try:
        expected_digest, hasher = _checksum_hasher(expected_checksum)
    except SafeHelperError:
        response.close()
        raise
    destination.parent.mkdir(parents=True, exist_ok=True)
    byte_count = 0
    try:
        try:
            with destination.open("wb") as file_obj:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if not chunk:
                        continue
                    file_obj.write(chunk)
                    if hasher is not None:
                        hasher.update(chunk)
                    byte_count += len(chunk)
        except OSError as exc:
            raise SafeHelperError("local_file_error") from exc
        except Exception as exc:  # noqa: BLE001
            raise SafeHelperError("network_error") from exc
    finally:
        response.close()
    if byte_count != expected_size:
        raise SafeHelperError("size_mismatch")
    if hasher is not None and expected_digest is not None and hasher.digest() != expected_digest:
        raise SafeHelperError("checksum_mismatch")
    return byte_count


def _publish_item(
    staging_root: Path,
    verified_resources: list[tuple[Path, Path]],
) -> None:
    if any(final_path.exists() for _, final_path in verified_resources):
        raise SafeHelperError("destination_exists")
    published: list[tuple[Path, Path]] = []
    try:
        for partial_path, final_path in verified_resources:
            final_path.parent.mkdir(parents=True, exist_ok=True)
            partial_path.replace(final_path)
            published.append((partial_path, final_path))
    except OSError as exc:
        rollback_failed = False
        for partial_path, final_path in reversed(published):
            try:
                if final_path.exists():
                    final_path.replace(partial_path)
            except OSError:
                rollback_failed = True
        code = "publish_rollback_failed" if rollback_failed else "publish_failed"
        raise SafeHelperError(code) from exc

    for _, final_path in verified_resources:
        try:
            final_path.resolve().relative_to(staging_root.resolve())
        except ValueError as exc:
            raise SafeHelperError("unsafe_staging_path") from exc


def _execute_item_download(
    selection_index: int,
    request_item: dict[str, Any],
    asset: object,
    descriptor: dict[str, Any],
    provider: ExactSelectionProvider,
    staging_root: Path,
    partial_run_root: Path,
) -> dict[str, Any]:
    if descriptor.get("identity_ambiguous"):
        return {
            "selection_index": selection_index,
            "status": "failed",
            "error_code": "logical_item_identity_ambiguous",
            "resources": [],
        }

    described_resources = {
        resource["resource_id"]: resource for resource in descriptor.get("resources", [])
    }
    partial_item_root = partial_run_root / f"item_{selection_index:04d}"
    verified: list[tuple[Path, Path]] = []
    resource_results: list[dict[str, Any]] = []
    try:
        for selected in request_item["resources"]:
            actual = described_resources.get(selected["resource_id"])
            manifest_matches = actual is not None and all(
                actual.get(field) == selected[field]
                for field in ("relative_path", "expected_size", "expected_checksum")
            )
            if not manifest_matches:
                raise SafeHelperError("selection_manifest_changed")

            final_path = _resolved_child(staging_root, selected["relative_path"])
            partial_relative = f"{selected['relative_path']}.partial"
            partial_path = _resolved_child(partial_item_root, partial_relative)
            response = provider.open_resource(asset, selected["resource_id"])
            byte_count = _download_verified(
                response,
                partial_path,
                expected_size=selected["expected_size"],
                expected_checksum=selected["expected_checksum"],
            )
            try:
                created_timestamp = datetime.fromisoformat(
                    str(descriptor["created_at"])
                ).timestamp()
                os.utime(partial_path, (created_timestamp, created_timestamp))
            except (KeyError, TypeError, ValueError, OSError) as exc:
                raise SafeHelperError("local_file_error") from exc
            verified.append((partial_path, final_path))
            resource_results.append(
                {
                    "resource_id": selected["resource_id"],
                    "relative_path": selected["relative_path"],
                    "status": "verified",
                    "bytes": byte_count,
                }
            )

        _publish_item(staging_root, verified)
        for result in resource_results:
            result["status"] = "published"
        return {
            "selection_index": selection_index,
            "status": "completed",
            "error_code": None,
            "resources": resource_results,
        }
    except SafeHelperError as exc:
        for result in resource_results:
            result["status"] = "discarded_due_to_item_failure"
        return {
            "selection_index": selection_index,
            "status": "failed",
            "error_code": exc.code,
            "resources": resource_results,
        }
    finally:
        shutil.rmtree(partial_item_root, ignore_errors=True)


def _validate_staging_root(staging_root_value: str, approved_exports_root: Path) -> Path:
    raw_path = Path(staging_root_value).expanduser()
    if raw_path.is_symlink():
        raise SafeHelperError("unsafe_staging_path")
    staging_root = raw_path.resolve()
    approved_root = approved_exports_root.resolve()
    try:
        staging_root.relative_to(approved_root)
    except ValueError as exc:
        raise SafeHelperError("unsafe_staging_path") from exc
    if not staging_root.exists() or not staging_root.is_dir():
        raise SafeHelperError("staging_path_unavailable")
    return staging_root


def execute_download_selected(
    request: dict[str, Any],
    provider: ExactSelectionProvider,
    *,
    approved_exports_root: Path,
) -> dict[str, Any]:
    staging_root = _validate_staging_root(request["staging_root"], approved_exports_root)
    selected_items = request["selected_items"]
    requested_ids = {item["item_id"] for item in selected_items}
    assets_by_id: dict[str, object] = {}
    descriptors_by_id: dict[str, dict[str, Any]] = {}
    for asset in provider.iter_assets(int(request["candidate_scan_limit"])):
        descriptor = provider.describe_asset(asset)
        item_id = str(descriptor.get("item_id", ""))
        if item_id in requested_ids:
            if item_id in assets_by_id:
                raise SafeHelperError("logical_item_identity_ambiguous")
            assets_by_id[item_id] = asset
            descriptors_by_id[item_id] = descriptor

    partial_run_root = staging_root / ".partial" / request["run_token"]
    results: list[dict[str, Any]] = []
    for index, item in enumerate(selected_items, start=1):
        item_id = item["item_id"]
        asset = assets_by_id.get(item_id)
        if asset is None:
            results.append(
                {
                    "selection_index": index,
                    "status": "failed",
                    "error_code": "selected_item_not_found",
                    "resources": [],
                }
            )
            continue
        results.append(
            _execute_item_download(
                index,
                item,
                asset,
                descriptors_by_id[item_id],
                provider,
                staging_root,
                partial_run_root,
            )
        )

    try:
        partial_run_root.rmdir()
        partial_run_root.parent.rmdir()
    except OSError:
        pass

    completed_items = sum(1 for result in results if result["status"] == "completed")
    published_resources = sum(
        1
        for result in results
        for resource in result["resources"]
        if resource["status"] == "published"
    )
    selected_resource_count = sum(len(item["resources"]) for item in selected_items)
    status = (
        "completed"
        if completed_items == len(results)
        else ("partial" if completed_items else "failed")
    )
    return {
        "protocol_version": PROTOCOL_VERSION,
        "operation": OPERATION_DOWNLOAD_SELECTED,
        "status": status,
        "auth_state": provider.auth_state,
        "stop_reason": (
            "target_new_count_reached" if status == "completed" else "partial_item_failed"
        ),
        "error_code": None if status == "completed" else "one_or_more_items_failed",
        "selected_new_item_count": len(selected_items),
        "selected_new_resource_count": selected_resource_count,
        "downloaded_item_count": completed_items,
        "downloaded_resource_count": published_resources,
        "failed_item_count": len(selected_items) - completed_items,
        "failed_resource_count": selected_resource_count - published_resources,
        "items": results,
    }


def _default_exports_root() -> Path:
    return (Path(__file__).resolve().parents[4] / "storage" / "exports" / "icloud").resolve()


def _auth_state_response(operation: str, auth_state: str) -> dict[str, Any]:
    status = "completed" if auth_state == AUTHENTICATED else "blocked"
    return {
        "protocol_version": PROTOCOL_VERSION,
        "operation": operation,
        "status": status,
        "auth_state": auth_state,
        "error_code": None if status == "completed" else auth_state,
    }


def handle_request(
    payload: object,
    *,
    provider_factory: Callable[..., ExactSelectionProvider] = IcloudpdInternalProvider,
    approved_exports_root: Path | None = None,
) -> dict[str, Any]:
    operation = payload.get("operation") if isinstance(payload, dict) else "unknown"
    try:
        request = validate_helper_request(payload)
        resolved_exports_root = approved_exports_root or _default_exports_root()
        if request["operation"] == OPERATION_DOWNLOAD_SELECTED:
            _validate_staging_root(request["staging_root"], resolved_exports_root)
        provider = provider_factory(
            account_username=request["account_username"],
            library=None if request["operation"] == OPERATION_AUTH_STATUS else request["library"],
        )
        if request["operation"] == OPERATION_AUTH_STATUS:
            return _auth_state_response(OPERATION_AUTH_STATUS, provider.auth_state)
        if request["operation"] == OPERATION_LIST:
            return execute_list(request, provider)
        return execute_download_selected(
            request,
            provider,
            approved_exports_root=resolved_exports_root,
        )
    except ExactSelectionProtocolError as exc:
        return helper_failure(operation, exc.code)
    except SafeHelperError as exc:
        if operation == OPERATION_AUTH_STATUS and exc.code in {
            AUTHENTICATION_REQUIRED,
            SESSION_EXPIRED,
            REAUTHENTICATION_REQUIRED,
            AUTHENTICATION_FAILED,
            HELPER_UNAVAILABLE,
        }:
            return _auth_state_response(OPERATION_AUTH_STATUS, exc.code)
        return helper_failure(operation, exc.code)
    except Exception:  # noqa: BLE001 - secret-safe terminal boundary
        return helper_failure(operation, "helper_internal_error")


def main() -> int:
    raw = sys.stdin.buffer.read(MAX_HELPER_JSON_BYTES + 1)
    if len(raw) > MAX_HELPER_JSON_BYTES:
        result = helper_failure("unknown", "request_too_large")
    else:
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            result = helper_failure("unknown", "invalid_json")
        else:
            with redirect_stdout(sys.stderr):
                result = handle_request(payload)

    encoded = json.dumps(result, separators=(",", ":"), sort_keys=True)
    if len(encoded.encode("utf-8")) > MAX_HELPER_JSON_BYTES:
        encoded = json.dumps(
            helper_failure(result.get("operation"), "response_too_large"),
            separators=(",", ":"),
            sort_keys=True,
        )
    sys.stdout.write(encoded)
    sys.stdout.write("\n")
    structured_download_result = (
        result.get("operation") == OPERATION_DOWNLOAD_SELECTED
        and "selected_new_item_count" in result
    )
    return 0 if result.get("status") != "failed" or structured_download_result else 1


if __name__ == "__main__":  # pragma: no cover - subprocess entry point
    raise SystemExit(main())
