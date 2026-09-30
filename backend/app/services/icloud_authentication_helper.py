"""Isolated provider process for bounded interactive iCloud authentication."""

from __future__ import annotations

from contextlib import redirect_stdout
import hashlib
import json
import logging
import os
from pathlib import Path
import sys
from typing import Any


MAX_MESSAGE_BYTES = 16 * 1024


def _read_request() -> dict[str, Any]:
    line = sys.stdin.readline(MAX_MESSAGE_BYTES + 1)
    if not line or len(line.encode("utf-8")) > MAX_MESSAGE_BYTES:
        raise ValueError
    value = json.loads(line)
    if not isinstance(value, dict):
        raise ValueError
    return value


def _write(state: str, message: str, *, retryable: bool) -> None:
    sys.stdout.write(json.dumps({"state": state, "message": message, "retryable": retryable}) + "\n")
    sys.stdout.flush()


def _auth_directory(account_username: str) -> Path:
    root = Path(os.environ["ICLOUD_AUTH_STATE_PATH"]).expanduser()
    account_key = hashlib.sha256(account_username.casefold().encode("utf-8")).hexdigest()
    target = root / account_key
    target.mkdir(parents=True, exist_ok=True, mode=0o700)
    if target.is_symlink() or not target.is_dir():
        raise OSError
    os.chmod(target, 0o700)
    return target.resolve()


def _apple_service_error_code(exc: Exception) -> str | None:
    """Extract only an allowlist-relevant Apple code without exposing response text."""

    pending: list[BaseException] = [exc]
    visited: set[int] = set()
    while pending:
        current = pending.pop()
        if id(current) in visited:
            continue
        visited.add(id(current))

        code = getattr(current, "code", None)
        if isinstance(code, (str, int)) and str(code).startswith("-"):
            return str(code)

        reason = getattr(current, "reason", None)
        if isinstance(reason, str):
            try:
                payload = json.loads(reason)
            except (TypeError, ValueError):
                payload = None
            if isinstance(payload, dict):
                errors = payload.get("serviceErrors") or payload.get("service_errors")
                if isinstance(errors, list):
                    for item in errors:
                        if isinstance(item, dict):
                            item_code = item.get("code")
                            if isinstance(item_code, (str, int)) and str(item_code).startswith("-"):
                                return str(item_code)

        for nested in (current.__cause__, current.__context__, *current.args):
            if isinstance(nested, BaseException):
                pending.append(nested)
    return None


def _safe_exception_state(exc: Exception) -> tuple[str, str, bool]:
    name = type(exc).__name__
    if name in {"PyiCloudNoStoredPasswordAvailableException", "PyiCloud2SARequiredException"}:
        return "authentication_required", "iCloud sign-in is required.", True
    if name in {"PyiCloudFailedLoginException", "PyiCloudFailedMFAException"}:
        service_code = _apple_service_error_code(exc)
        if service_code == "-20209":
            return (
                "authentication_failed",
                "Apple reports that this account is locked. Unlock it with Apple before trying again.",
                False,
            )
        if service_code == "-20283":
            return (
                "authentication_failed",
                "Apple rejected this sign-in method. Use the regular Apple Account password, not an app-specific password.",
                False,
            )
        return "authentication_failed", "Apple rejected the sign-in information.", True
    if name == "PyiCloudAPIResponseException":
        return "session_expired", "The iCloud session is no longer valid.", True
    if name in {"PyiCloudConnectionErrorException", "PyiCloudServiceUnavailableException"}:
        return "provider_unavailable", "The iCloud service is temporarily unavailable.", True
    return "provider_unavailable", "iCloud authentication failed safely.", True


def _provider(account: str, password: str | None) -> Any:
    from pyicloud_ipd.base import PyiCloudService

    secret = [password]
    try:
        with open(os.devnull, "w", encoding="utf-8") as null_output, redirect_stdout(null_output):
            return PyiCloudService(
                "com",
                account,
                lambda: secret[0],
                None,
                cookie_directory=str(_auth_directory(account)),
                client_id=os.environ.get("CLIENT_ID"),
                http_timeout=30.0,
            )
    finally:
        secret[0] = None


def _authentication_requirement(provider: Any) -> str:
    """Classify modern HSA2 before the broader legacy HSA predicate."""

    if getattr(provider, "requires_2fa", False):
        return "modern_mfa"
    if getattr(provider, "requires_2sa", False):
        return "legacy_verification"
    return "none"


def main() -> int:
    logging.disable(logging.CRITICAL)
    try:
        request = _read_request()
        operation = request.get("operation")
        account = request.get("account_username")
        if operation not in {"probe", "authenticate"} or not isinstance(account, str) or not account.strip():
            raise ValueError
        password = request.get("password") if operation == "authenticate" else None
        if password is not None and not isinstance(password, str):
            raise ValueError
        request["password"] = None
        provider = _provider(account.strip().casefold(), password)
        password = None
        if not getattr(provider, "data", None):
            _write("authentication_required", "iCloud sign-in is required.", retryable=True)
            return 0
        authentication_requirement = _authentication_requirement(provider)
        if authentication_requirement == "legacy_verification":
            _write("authentication_failed", "This Apple account requires an unsupported legacy verification flow.", retryable=False)
            return 0
        if authentication_requirement == "modern_mfa":
            if operation == "probe":
                _write("authentication_required", "iCloud sign-in is required.", retryable=True)
                return 0
            try:
                provider.trigger_push_notification()
            except Exception:  # noqa: BLE001
                pass
            _write("mfa_required", "Enter the verification code sent by Apple.", retryable=True)
            for _ in range(3):
                verification = _read_request()
                code = verification.get("code")
                verification["code"] = None
                if verification.get("operation") != "mfa" or not isinstance(code, str):
                    raise ValueError
                accepted = False
                if code.isdigit() and len(code) == 6:
                    try:
                        accepted = bool(provider.validate_2fa_code(code))
                    except Exception:  # noqa: BLE001
                        accepted = False
                code = None
                if accepted:
                    _write("authenticated", "iCloud sign-in succeeded.", retryable=False)
                    return 0
                _write("mfa_required", "Apple did not accept that verification code. Try a new code.", retryable=True)
            return 0
        _write("authenticated", "iCloud sign-in succeeded.", retryable=False)
        return 0
    except Exception as exc:  # noqa: BLE001 - provider details never cross the boundary
        state, message, retryable = _safe_exception_state(exc)
        _write(state, message, retryable=retryable)
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
