"""Shared helpers for direct iCloud feasibility scripts (Milestone 12.33)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from getpass import getpass, getuser
from pathlib import Path
from typing import Any


try:
    from pyicloud import PyiCloudService
    from pyicloud.base import resolve_cookie_directory
except ImportError as exc:  # pragma: no cover - defensive import guard for operators
    raise RuntimeError(
        "pyicloud is not installed in this environment. Install it temporarily for Milestone 12.33."
    ) from exc


DEFAULT_SOURCE_LABEL = "chuck_icloud_direct_test"


@dataclass(frozen=True)
class AuthSummary:
    authenticated: bool
    requires_2fa: bool
    requires_2sa: bool
    trusted_session: bool
    cookie_directory: str


def workspace_root() -> Path:
    """Return workspace root based on backend/scripts/experimental location."""
    return Path(__file__).resolve().parents[3]


def report_root() -> Path:
    return workspace_root() / "storage" / "logs" / "icloud_connector_reports"


def default_staging_root(source_label: str) -> Path:
    return workspace_root() / "storage" / "exports" / "icloud" / source_label


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def now_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def prompt_username(username: str | None) -> str:
    if username and username.strip():
        return username.strip()
    return input("Apple ID email: ").strip()


def prompt_password() -> str:
    return getpass("Apple ID password (input hidden): ")


def _pick_trusted_device(api: PyiCloudService) -> dict[str, Any]:
    devices = list(api.trusted_devices)
    if not devices:
        raise RuntimeError("No trusted devices were returned for 2SA verification.")

    if len(devices) == 1:
        return devices[0]

    print("Trusted devices:")
    for idx, device in enumerate(devices, start=1):
        name = device.get("deviceName") or device.get("phoneNumber") or "unknown"
        print(f"  {idx}. {name}")

    selection = input("Choose device number for verification (default 1): ").strip()
    if not selection:
        return devices[0]

    try:
        index = int(selection)
    except ValueError as exc:
        raise RuntimeError("Invalid device selection for 2SA verification.") from exc

    if index < 1 or index > len(devices):
        raise RuntimeError("Device selection out of range for 2SA verification.")
    return devices[index - 1]


def authenticate_interactive(
    *,
    username: str | None = None,
    cookie_directory: str | None = None,
) -> tuple[PyiCloudService, AuthSummary]:
    """Authenticate to iCloud with interactive password and verification prompts."""
    resolved_username = prompt_username(username)
    password = prompt_password()

    api = PyiCloudService(
        resolved_username,
        password,
        cookie_directory=cookie_directory,
    )

    requires_2fa = bool(api.requires_2fa)
    requires_2sa = bool(api.requires_2sa)

    if requires_2fa:
        code = input("Enter 2FA code from trusted Apple device: ").strip()
        if not api.validate_2fa_code(code):
            raise RuntimeError("2FA validation failed.")
        if not api.is_trusted_session:
            api.trust_session()

    if requires_2sa and not requires_2fa:
        device = _pick_trusted_device(api)
        if not api.send_verification_code(device):
            raise RuntimeError("Failed to send verification code to trusted device.")
        code = input("Enter verification code: ").strip()
        if not api.validate_verification_code(device, code):
            raise RuntimeError("2SA verification failed.")

    summary = AuthSummary(
        authenticated=True,
        requires_2fa=requires_2fa,
        requires_2sa=requires_2sa,
        trusted_session=bool(getattr(api, "is_trusted_session", False)),
        cookie_directory=resolve_cookie_directory(cookie_directory),
    )
    return api, summary


def extract_extension(filename: str | None) -> str:
    if not filename:
        return ""
    return Path(filename).suffix.lower()


def item_type_from_photo(photo: Any) -> str | None:
    try:
        return str(photo.item_type)
    except Exception:
        return None


def safe_identifier_candidates(photo: Any) -> dict[str, Any]:
    master_record = getattr(photo, "_master_record", {}) or {}
    asset_record = getattr(photo, "_asset_record", {}) or {}

    master_fields = (
        "recordName",
        "masterRef",
        "resOriginalRes",
        "resJPEGFullRes",
        "resVidFullRes",
    )
    asset_fields = (
        "recordName",
        "masterRef",
    )

    return {
        "id": getattr(photo, "id", None),
        "master_record_name": master_record.get("recordName"),
        "asset_record_name": asset_record.get("recordName"),
        "master_ref": master_record.get("masterRef") or asset_record.get("masterRef"),
        "master_record_keys": sorted([k for k in master_record.keys() if k in master_fields]),
        "asset_record_keys": sorted([k for k in asset_record.keys() if k in asset_fields]),
    }


def ensure_unique_path(target_path: Path) -> Path:
    if not target_path.exists():
        return target_path

    stem = target_path.stem
    suffix = target_path.suffix
    parent = target_path.parent
    counter = 2
    while True:
        candidate = parent / f"{stem}__dup{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def summarize_install_environment() -> dict[str, str]:
    return {
        "python_user": getuser(),
        "generated_at_utc": now_utc_iso(),
    }
