"""Bounded interactive iCloud authentication without password persistence."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import selectors
import subprocess
from threading import RLock
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.ingestion_source import IngestionSource


AUTHENTICATED = "authenticated"
AUTHENTICATION_REQUIRED = "authentication_required"
MFA_REQUIRED = "mfa_required"
AUTHENTICATION_FAILED = "authentication_failed"
SESSION_EXPIRED = "session_expired"
PROVIDER_UNAVAILABLE = "provider_unavailable"


class IcloudAuthenticationError(RuntimeError):
    """Browser-safe authentication error with no provider exception detail."""

    def __init__(self, code: str, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.code = code
        self.safe_message = message
        self.retryable = retryable


@dataclass
class IcloudAuthenticationSnapshot:
    session_id: UUID | None
    source_profile_id: int
    account_hint: str
    state: str
    message: str
    retryable: bool
    expires_at: datetime | None = None


@dataclass
class _AuthSession:
    session_id: UUID
    source_profile_id: int
    account_username: str
    account_hint: str
    created_at: datetime
    expires_at: datetime
    state: str = "password_required"
    provider: subprocess.Popen[str] | None = None


_lock = RLock()
_sessions: dict[UUID, _AuthSession] = {}
_source_sessions: dict[int, UUID] = {}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _mask_account(value: str) -> str:
    local, separator, domain = value.partition("@")
    if not separator:
        return "***"
    visible = local[:1] if local else ""
    return f"{visible}***@{domain}"


def icloud_auth_directory_path(account_username: str) -> Path:
    """Return the opaque account-specific auth path without creating it."""
    account_key = hashlib.sha256(account_username.casefold().encode("utf-8")).hexdigest()
    return Path(settings.icloud_auth_state_path).expanduser() / account_key


def _account_auth_directory(account_username: str) -> Path:
    root = Path(settings.icloud_auth_state_path).expanduser()
    try:
        root.mkdir(parents=True, exist_ok=True, mode=0o700)
        if root.is_symlink() or not root.is_dir():
            raise OSError
        os.chmod(root, 0o700)
        account_dir = icloud_auth_directory_path(account_username)
        account_dir.mkdir(mode=0o700, exist_ok=True)
        if account_dir.is_symlink() or not account_dir.is_dir():
            raise OSError
        os.chmod(account_dir, 0o700)
        return account_dir.resolve()
    except OSError as exc:
        raise IcloudAuthenticationError(
            PROVIDER_UNAVAILABLE,
            "Protected iCloud session storage is unavailable.",
        ) from exc


_HELPER_SCRIPT = Path(__file__).with_name("icloud_authentication_helper.py").resolve()
_MAX_RESPONSE_BYTES = 16 * 1024


def _start_provider_process() -> subprocess.Popen[str]:
    provider_python = Path(settings.icloud_provider_python_path)
    if not provider_python.is_absolute() or not provider_python.is_file() or not _HELPER_SCRIPT.is_file():
        raise IcloudAuthenticationError(
            PROVIDER_UNAVAILABLE,
            "The iCloud authentication provider is unavailable.",
        )
    try:
        provider_env = {
            key: value
            for key in (
                "CLIENT_ID",
                "HOME",
                "LANG",
                "LC_ALL",
                "PATH",
                "REQUESTS_CA_BUNDLE",
                "SSL_CERT_FILE",
            )
            if (value := os.environ.get(key)) is not None
        }
        provider_env["ICLOUD_AUTH_STATE_PATH"] = settings.icloud_auth_state_path
        return subprocess.Popen(
            [str(provider_python), str(_HELPER_SCRIPT)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            env=provider_env,
        )
    except OSError as exc:
        raise IcloudAuthenticationError(
            PROVIDER_UNAVAILABLE,
            "The iCloud authentication provider could not start.",
        ) from exc


def _send_provider_request(process: subprocess.Popen[str], request: dict[str, str]) -> dict[str, Any]:
    if process.stdin is None or process.stdout is None or process.poll() is not None:
        raise IcloudAuthenticationError(PROVIDER_UNAVAILABLE, "The iCloud authentication session ended.")
    try:
        process.stdin.write(json.dumps(request, separators=(",", ":")) + "\n")
        process.stdin.flush()
        with selectors.DefaultSelector() as selector:
            selector.register(process.stdout, selectors.EVENT_READ)
            if not selector.select(timeout=float(settings.icloudpd_probe_timeout_seconds)):
                process.kill()
                process.wait(timeout=5)
                raise IcloudAuthenticationError(
                    PROVIDER_UNAVAILABLE,
                    "The iCloud authentication provider timed out.",
                    retryable=True,
                )
        line = process.stdout.readline(_MAX_RESPONSE_BYTES + 1)
        if not line or len(line.encode("utf-8")) > _MAX_RESPONSE_BYTES:
            raise ValueError
        response = json.loads(line)
        if not isinstance(response, dict):
            raise ValueError
        state = response.get("state")
        message = response.get("message")
        retryable = response.get("retryable")
        allowed_states = {
            AUTHENTICATED,
            AUTHENTICATION_REQUIRED,
            MFA_REQUIRED,
            AUTHENTICATION_FAILED,
            SESSION_EXPIRED,
            PROVIDER_UNAVAILABLE,
        }
        if state not in allowed_states or not isinstance(message, str) or not isinstance(retryable, bool):
            raise ValueError
        return {"state": state, "message": message[:512], "retryable": retryable}
    except IcloudAuthenticationError:
        raise
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)
        raise IcloudAuthenticationError(
            PROVIDER_UNAVAILABLE,
            "The iCloud authentication provider returned an invalid safe response.",
            retryable=True,
        ) from exc


def _close_process(process: subprocess.Popen[str] | None) -> None:
    if process is None:
        return
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def _get_icloud_source(db_session: Session, source_profile_id: int) -> IngestionSource:
    source = db_session.get(IngestionSource, source_profile_id)
    if source is None:
        raise LookupError("Source profile not found.")
    if source.source_type != "cloud_export" or source.cloud_provider != "icloud":
        raise IcloudAuthenticationError("not_icloud_profile", "This Source is not an iCloud Source.")
    if not (source.account_username or "").strip():
        raise IcloudAuthenticationError("account_missing", "The iCloud account identity is missing.")
    return source


def probe_icloud_authentication(account_username: str) -> str:
    """Return a bounded live provider-session state without acquiring media."""

    process: subprocess.Popen[str] | None = None
    try:
        _account_auth_directory(account_username)
        process = _start_provider_process()
        response = _send_provider_request(
            process,
            {"operation": "probe", "account_username": account_username},
        )
        return str(response["state"])
    except IcloudAuthenticationError as exc:
        return exc.code
    finally:
        _close_process(process)


def _expire_locked(now: datetime) -> None:
    expired = [session_id for session_id, session in _sessions.items() if session.expires_at <= now]
    for session_id in expired:
        session = _sessions.pop(session_id)
        _source_sessions.pop(session.source_profile_id, None)
        _close_process(session.provider)
        session.provider = None


def start_icloud_authentication(db_session: Session, *, source_profile_id: int) -> IcloudAuthenticationSnapshot:
    source = _get_icloud_source(db_session, source_profile_id)
    account = source.account_username.strip().casefold()
    now = _utcnow()
    with _lock:
        _expire_locked(now)
        existing_id = _source_sessions.get(source_profile_id)
        if existing_id is not None:
            existing = _sessions[existing_id]
            return _snapshot(existing, "Continue the existing iCloud sign-in.")
        if any(existing.account_username == account for existing in _sessions.values()):
            raise IcloudAuthenticationError(
                "account_authentication_active",
                "An iCloud sign-in is already active for this account.",
                retryable=True,
            )
        session = _AuthSession(
            session_id=uuid4(),
            source_profile_id=source_profile_id,
            account_username=account,
            account_hint=_mask_account(account),
            created_at=now,
            expires_at=now + timedelta(seconds=settings.icloud_auth_session_ttl_seconds),
        )
        _sessions[session.session_id] = session
        _source_sessions[source_profile_id] = session.session_id
        return _snapshot(session, "Enter the Apple account password to continue.")


def _snapshot(session: _AuthSession, message: str, *, retryable: bool = True) -> IcloudAuthenticationSnapshot:
    return IcloudAuthenticationSnapshot(
        session_id=session.session_id,
        source_profile_id=session.source_profile_id,
        account_hint=session.account_hint,
        state=session.state,
        message=message,
        retryable=retryable,
        expires_at=session.expires_at,
    )


def _require_session(session_id: UUID, source_profile_id: int) -> _AuthSession:
    now = _utcnow()
    with _lock:
        _expire_locked(now)
        session = _sessions.get(session_id)
        if session is None:
            raise IcloudAuthenticationError("expired", "The iCloud sign-in session expired.")
        if session.source_profile_id != source_profile_id:
            raise IcloudAuthenticationError(
                "session_mismatch",
                "The iCloud sign-in session does not match this Source.",
            )
        return session


def submit_icloud_password(
    db_session: Session,
    *,
    session_id: UUID,
    source_profile_id: int,
    password: str,
) -> IcloudAuthenticationSnapshot:
    source = _get_icloud_source(db_session, source_profile_id)
    session = _require_session(session_id, source_profile_id)
    if source.account_username.strip().casefold() != session.account_username:
        raise IcloudAuthenticationError(
            "account_mismatch",
            "The iCloud account no longer matches this sign-in session.",
        )
    if not password:
        raise IcloudAuthenticationError("password_required", "Enter the Apple account password.", retryable=True)
    with _lock:
        if session.state not in {"password_required", AUTHENTICATION_FAILED}:
            raise IcloudAuthenticationError(
                "invalid_state",
                "A password is not expected in the current sign-in state.",
            )
        session.state = "authenticating"

    process: subprocess.Popen[str] | None = None
    try:
        _account_auth_directory(session.account_username)
        process = _start_provider_process()
        response = _send_provider_request(
            process,
            {
                "operation": "authenticate",
                "account_username": session.account_username,
                "password": password,
            },
        )
    except IcloudAuthenticationError as exc:
        _close_process(process)
        session.state = AUTHENTICATION_FAILED
        return _snapshot(session, exc.safe_message, retryable=exc.retryable)
    finally:
        password = ""

    response_state = str(response["state"])
    response_message = str(response["message"])
    response_retryable = bool(response["retryable"])
    if response_state == MFA_REQUIRED:
        session.provider = process
        session.state = MFA_REQUIRED
        return _snapshot(session, response_message, retryable=response_retryable)
    _close_process(process)
    if response_state == AUTHENTICATED:
        return _finish_success(session)
    if response_state in {SESSION_EXPIRED, AUTHENTICATION_REQUIRED, AUTHENTICATION_FAILED}:
        session.state = AUTHENTICATION_FAILED
    else:
        session.state = AUTHENTICATION_FAILED
    return _snapshot(session, response_message, retryable=response_retryable)


def submit_icloud_mfa(
    db_session: Session,
    *,
    session_id: UUID,
    source_profile_id: int,
    code: str,
) -> IcloudAuthenticationSnapshot:
    _get_icloud_source(db_session, source_profile_id)
    session = _require_session(session_id, source_profile_id)
    with _lock:
        if session.state != MFA_REQUIRED or session.provider is None:
            raise IcloudAuthenticationError(
                "invalid_state",
                "A verification code is not expected in the current sign-in state.",
            )
    if not code.isdigit() or len(code) != 6:
        return _snapshot(session, "Enter the six-digit Apple verification code.", retryable=True)
    with _lock:
        if session.state != MFA_REQUIRED or session.provider is None:
            raise IcloudAuthenticationError(
                "invalid_state",
                "A verification code is not expected in the current sign-in state.",
            )
        session.state = "authenticating"
    process = session.provider
    try:
        response = _send_provider_request(process, {"operation": "mfa", "code": code})
    except IcloudAuthenticationError as exc:
        _close_process(process)
        session.provider = None
        session.state = AUTHENTICATION_FAILED
        return _snapshot(session, exc.safe_message, retryable=exc.retryable)
    finally:
        code = ""
    if response["state"] == MFA_REQUIRED:
        session.state = MFA_REQUIRED
        return _snapshot(session, str(response["message"]), retryable=bool(response["retryable"]))
    _close_process(process)
    session.provider = None
    if response["state"] == AUTHENTICATED:
        return _finish_success(session)
    session.state = AUTHENTICATION_FAILED
    return _snapshot(session, str(response["message"]), retryable=bool(response["retryable"]))


def _finish_success(session: _AuthSession) -> IcloudAuthenticationSnapshot:
    session.state = AUTHENTICATED
    snapshot = _snapshot(session, "iCloud sign-in succeeded.", retryable=False)
    with _lock:
        _sessions.pop(session.session_id, None)
        _source_sessions.pop(session.source_profile_id, None)
        _close_process(session.provider)
        session.provider = None
    return snapshot


def cancel_icloud_authentication(*, session_id: UUID, source_profile_id: int) -> IcloudAuthenticationSnapshot:
    session = _require_session(session_id, source_profile_id)
    session.state = "cancelled"
    snapshot = _snapshot(session, "iCloud sign-in was cancelled.", retryable=False)
    with _lock:
        _sessions.pop(session.session_id, None)
        _source_sessions.pop(session.source_profile_id, None)
        _close_process(session.provider)
        session.provider = None
    return snapshot
