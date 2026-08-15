from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import unittest
from uuid import UUID, uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import create_engine, inspect, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.windows_helper import router as helper_router
from app.api.windows_helper_admin import router as admin_router
from app.db.session import get_db_session
from app.helper_main import create_helper_app
from app.models.source_endpoint import AccessNode, SourceEndpoint, SourceEndpointObservedPath
from app.models.windows_helper import WindowsHelperCredential, WindowsHelperPairingAuthorization
from app.services.windows_helper.schema import ensure_windows_helper_schema
from app.services.windows_helper.service import (
    ACCESS_NODE_LABEL,
    HELPER_PROVIDER_NAME,
    HELPER_PROVIDER_VERSION,
    WindowsHelperServiceError,
    authenticate_credential,
    complete_pairing,
    create_pairing_authorization,
    credential_token_digest,
    record_heartbeat,
    revoke_credential,
)
from app.windows_helper_shared.channel import HelperHeartbeatRequest, PairingCompleteRequest
from app.windows_helper_shared.protocol import (
    CapabilityVersion,
    CollectorCapability,
    HelperCapabilityIdentity,
    SourceType,
)


def _capability(access_node_id: UUID, *, protocol_version: int = 1) -> HelperCapabilityIdentity:
    return HelperCapabilityIdentity(
        protocol_version=protocol_version,
        helper_version="0.2.0",
        intended_access_node_id=access_node_id,
        os_version="synthetic-windows",
        supported_source_types=[SourceType.LOCAL],
        collectors=[
            CollectorCapability(
                name="windows_non_admin_probe_v1",
                version="1",
                supported_source_types=[SourceType.LOCAL],
            )
        ],
        capabilities=[CapabilityVersion(name="authenticated_channel", version="1")],
    )


class WindowsHelperChannelTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
        AccessNode.__table__.create(self.engine)
        self.db = Session(self.engine, expire_on_commit=False)
        ensure_windows_helper_schema(self.db)

    def tearDown(self) -> None:
        self.db.close()
        self.engine.dispose()

    def _pairing(self) -> tuple[object, PairingCompleteRequest]:
        authorization = create_pairing_authorization(self.db)
        request = PairingCompleteRequest(
            pairing_code=authorization.pairing_code,
            access_node_id=authorization.access_node_id,
            capability_identity=_capability(authorization.access_node_id),
        )
        return authorization, request

    def _paired(self):
        authorization, request = self._pairing()
        return authorization, complete_pairing(self.db, request)

    def test_schema_is_additive_and_idempotent(self) -> None:
        second = ensure_windows_helper_schema(self.db)
        self.assertEqual(second.created_tables, [])
        tables = set(inspect(self.engine).get_table_names())
        self.assertEqual(
            tables,
            {
                "access_nodes",
                "windows_helper_credentials",
                "windows_helper_pairing_authorizations",
                "windows_helper_operations",
            },
        )

    def test_pairing_creates_only_access_node_and_rotates_single_credential(self) -> None:
        authorization, first = self._paired()
        node = self.db.scalar(select(AccessNode))
        credential = self.db.scalar(select(WindowsHelperCredential))
        stored_authorization = self.db.scalar(select(WindowsHelperPairingAuthorization))

        self.assertEqual(node.label, ACCESS_NODE_LABEL)
        self.assertEqual(node.provider_name, HELPER_PROVIDER_NAME)
        self.assertEqual(node.provider_version, HELPER_PROVIDER_VERSION)
        self.assertEqual(stored_authorization.status, "consumed")
        self.assertNotEqual(credential.token_digest, first.credential_token)
        self.assertEqual(credential.token_digest, credential_token_digest(first.credential_token))
        self.assertNotIn(first.credential_token, json.dumps(node.capabilities_json))
        self.assertFalse(inspect(self.engine).has_table(SourceEndpoint.__tablename__))
        self.assertFalse(inspect(self.engine).has_table(SourceEndpointObservedPath.__tablename__))

        second_authorization = create_pairing_authorization(self.db)
        second = complete_pairing(
            self.db,
            PairingCompleteRequest(
                pairing_code=second_authorization.pairing_code,
                access_node_id=authorization.access_node_id,
                capability_identity=_capability(authorization.access_node_id),
            ),
        )
        self.assertEqual(self.db.query(WindowsHelperCredential).count(), 1)
        self.assertEqual(second.credential_version, 2)
        self.assertNotEqual(second.credential_id, first.credential_id)
        with self.assertRaises(WindowsHelperServiceError):
            authenticate_credential(
                self.db,
                f"PhotoOrganizerHelper {first.credential_id}.{first.credential_token}",
            )

    def test_pairing_replay_expiry_wrong_node_and_malformed_requests_fail_closed(self) -> None:
        authorization, request = self._pairing()
        complete_pairing(self.db, request)
        with self.assertRaisesRegex(WindowsHelperServiceError, "unavailable"):
            complete_pairing(self.db, request)

        expired = create_pairing_authorization(self.db)
        row = self.db.scalar(
            select(WindowsHelperPairingAuthorization).where(
                WindowsHelperPairingAuthorization.public_id == expired.pairing_id
            )
        )
        row.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        self.db.commit()
        with self.assertRaisesRegex(WindowsHelperServiceError, "expired"):
            complete_pairing(
                self.db,
                PairingCompleteRequest(
                    pairing_code=expired.pairing_code,
                    access_node_id=expired.access_node_id,
                    capability_identity=_capability(expired.access_node_id),
                ),
            )

        fresh = create_pairing_authorization(self.db)
        wrong_node = uuid4()
        with self.assertRaisesRegex(WindowsHelperServiceError, "does not match"):
            complete_pairing(
                self.db,
                PairingCompleteRequest(
                    pairing_code=fresh.pairing_code,
                    access_node_id=wrong_node,
                    capability_identity=_capability(wrong_node),
                ),
            )
        with self.assertRaises(ValidationError):
            PairingCompleteRequest.model_validate(
                {
                    "pairing_code": "x" * 40,
                    "access_node_id": str(authorization.access_node_id),
                    "capability_identity": _capability(authorization.access_node_id).model_dump(mode="json"),
                    "unexpected": True,
                }
            )

    def test_authentication_revocation_binding_and_idempotent_heartbeat(self) -> None:
        _, paired = self._paired()
        header = f"PhotoOrganizerHelper {paired.credential_id}.{paired.credential_token}"
        credential = authenticate_credential(self.db, header)
        for bad_header in (
            None,
            "Bearer anything",
            f"PhotoOrganizerHelper {paired.credential_id}.{'x' * 43}",
            f"PhotoOrganizerHelper c_{'0' * 32}.{'x' * 43}",
        ):
            with self.assertRaises(WindowsHelperServiceError):
                authenticate_credential(self.db, bad_header)

        request = HelperHeartbeatRequest(
            access_node_id=paired.access_node_id,
            capability_identity=_capability(paired.access_node_id),
        )
        first = record_heartbeat(self.db, credential, request)
        second = record_heartbeat(self.db, credential, request)
        self.assertEqual(first.credential_id, second.credential_id)
        self.assertEqual(self.db.query(WindowsHelperCredential).count(), 1)
        self.assertEqual(self.db.query(AccessNode).count(), 1)

        wrong_node = uuid4()
        with self.assertRaisesRegex(WindowsHelperServiceError, "does not match"):
            record_heartbeat(
                self.db,
                credential,
                HelperHeartbeatRequest(
                    access_node_id=wrong_node,
                    capability_identity=_capability(wrong_node),
                ),
            )

        first_revoke = revoke_credential(self.db, paired.access_node_id)
        second_revoke = revoke_credential(self.db, paired.access_node_id)
        self.assertTrue(first_revoke.changed)
        self.assertFalse(second_revoke.changed)
        with self.assertRaises(WindowsHelperServiceError):
            authenticate_credential(self.db, header)

    def test_unsupported_protocol_fails_before_persistence(self) -> None:
        authorization = create_pairing_authorization(self.db)
        payload = _capability(authorization.access_node_id).model_dump(mode="json")
        payload["protocol_version"] = 2
        with self.assertRaises(ValidationError):
            HelperCapabilityIdentity.model_validate(payload)
        self.assertEqual(self.db.query(WindowsHelperCredential).count(), 0)


class WindowsHelperApiIsolationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            future=True,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        AccessNode.__table__.create(self.engine)
        self.db = Session(self.engine, expire_on_commit=False)
        ensure_windows_helper_schema(self.db)

        def override_db():
            yield self.db

        self.helper_app = create_helper_app()
        self.helper_app.dependency_overrides[get_db_session] = override_db
        self.helper_client = TestClient(self.helper_app)

        self.admin_app = FastAPI()
        self.admin_app.include_router(admin_router)
        self.admin_app.dependency_overrides[get_db_session] = override_db
        self.admin_client = TestClient(self.admin_app)

    def tearDown(self) -> None:
        self.helper_app.dependency_overrides.clear()
        self.admin_app.dependency_overrides.clear()
        self.db.close()
        self.engine.dispose()

    def test_isolated_ingress_mounts_helper_routes_only(self) -> None:
        self.assertEqual(self.helper_client.get("/api/helper/v1/health").status_code, 200)
        self.assertEqual(self.helper_client.get("/api/admin/windows-helper/status").status_code, 404)
        self.assertEqual(self.helper_client.get("/api/admin/summary").status_code, 404)
        self.assertEqual(self.helper_client.get("/api/photos").status_code, 404)
        self.assertEqual(self.helper_client.get("/docs").status_code, 404)
        self.assertEqual(self.helper_client.get("/openapi.json").status_code, 404)

    def test_pair_session_heartbeat_and_redacted_validation(self) -> None:
        created = self.admin_client.post("/api/admin/windows-helper/pairing-authorizations", json={})
        self.assertEqual(created.status_code, 200)
        self.assertEqual(created.headers["cache-control"], "no-store")
        pairing = created.json()
        node_id = UUID(pairing["access_node_id"])
        capability = _capability(node_id).model_dump(mode="json")
        paired = self.helper_client.post(
            "/api/helper/v1/pair",
            json={
                "pairing_code": pairing["pairing_code"],
                "access_node_id": str(node_id),
                "capability_identity": capability,
            },
        )
        self.assertEqual(paired.status_code, 200)
        self.assertEqual(paired.headers["cache-control"], "no-store")
        credential = paired.json()
        header = {
            "Authorization": (
                f"PhotoOrganizerHelper {credential['credential_id']}.{credential['credential_token']}"
            )
        }
        self.assertEqual(self.helper_client.get("/api/helper/v1/session", headers=header).status_code, 200)
        self.assertEqual(
            self.helper_client.post(
                "/api/helper/v1/heartbeat",
                headers=header,
                json={"access_node_id": str(node_id), "capability_identity": capability},
            ).status_code,
            200,
        )
        operation = self.admin_client.post(
            "/api/admin/windows-helper/operations/probe-source",
            json={
                "access_node_id": str(node_id),
                "source_type": "local",
                "provider_native_root": "C:\\Controlled",
            },
        )
        self.assertEqual(operation.status_code, 200)
        claimed = self.helper_client.post(
            "/api/helper/v1/operations/claim",
            headers=header,
        )
        self.assertEqual(claimed.status_code, 200)
        self.assertEqual(
            claimed.json()["operation"]["operation_id"],
            operation.json()["operation_id"],
        )

        self.assertEqual(self.helper_client.get("/api/helper/v1/session").status_code, 401)
        self.assertEqual(
            self.helper_client.post("/api/helper/v1/operations/claim").status_code,
            401,
        )

        malformed = self.helper_client.post(
            "/api/helper/v1/pair",
            json={"pairing_code": pairing["pairing_code"], "unexpected": "secret-like"},
        )
        self.assertEqual(malformed.status_code, 422)
        self.assertNotIn(pairing["pairing_code"], malformed.text)
        self.assertNotIn("secret-like", malformed.text)

        revoked = self.admin_client.post(
            "/api/admin/windows-helper/revoke", json={"access_node_id": str(node_id)}
        )
        self.assertEqual(revoked.status_code, 200)
        self.assertEqual(self.helper_client.get("/api/helper/v1/session", headers=header).status_code, 401)
        self.assertEqual(
            self.helper_client.post(
                "/api/helper/v1/operations/claim",
                headers=header,
            ).status_code,
            401,
        )


if __name__ == "__main__":
    unittest.main()
