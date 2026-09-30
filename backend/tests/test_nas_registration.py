"""Focused generalized NAS registry, pending request, and completion tests."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace
import sys
import unittest
from uuid import UUID

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.models.nas_registration import (
    NasApplianceRegistration,
    NasPendingRegistration,
    NasShareRegistration,
)
from app.models.source_endpoint import AccessNode, SourceEndpoint
from app.services.nas_registration.schema import ensure_nas_registration_schema
from app.services.nas_registration.schemas import CreateNasPendingRegistrationRequest
from app.services.nas_registration.service import (
    LEGACY_APPLIANCE_UUID,
    LEGACY_LOCATION_ID,
    NasRegistrationError,
    complete_registration,
    create_pending_registration,
    ensure_existing_nas_adoption,
    get_installer_manifest,
    list_registrations,
)


GUID_A = bytes.fromhex("00112233445566778899aabbccddeeff")
GUID_B = bytes.fromhex("ffeeddccbbaa99887766554433221100")


class FakeBroker:
    def __init__(self, locations: list[object]) -> None:
        self.locations = locations

    def probe(self, **_kwargs: object) -> object:
        return SimpleNamespace(locations=self.locations)

    def list_locations(self) -> object:
        return SimpleNamespace(locations=self.locations)


def location(
    location_id: str,
    fingerprint_hash: str,
    fingerprint_version: str,
    *,
    status: str = "available",
    blocker_code: str | None = None,
) -> object:
    blockers = [] if blocker_code is None else [SimpleNamespace(code=blocker_code)]
    return SimpleNamespace(
        location_id=location_id,
        status=status,
        identity_fingerprint_hash=fingerprint_hash,
        identity_fingerprint_version=fingerprint_version,
        blockers=blockers,
    )


class NasRegistrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
        AccessNode.__table__.create(self.engine)
        SourceEndpoint.__table__.create(self.engine)
        self.db = Session(self.engine)
        ensure_nas_registration_schema(self.db)

    def tearDown(self) -> None:
        self.db.close()
        self.engine.dispose()

    def request(self, **overrides: str) -> CreateNasPendingRegistrationRequest:
        values = {
            "network_host": "nas.example.test",
            "share_name": "FamilyPhotos",
            "appliance_name": "Family NAS",
            "location_name": "Family Photos",
        }
        values.update(overrides)
        return CreateNasPendingRegistrationRequest(**values)

    def test_additive_schema_is_idempotent(self) -> None:
        summary = ensure_nas_registration_schema(self.db)
        self.assertEqual(summary.created_tables, [])

    def test_existing_adoption_preserves_endpoint_identity(self) -> None:
        endpoint = SourceEndpoint(
            source_type="nas",
            alias="12.65.4 Development NAS",
            alias_normalized="12.65.4 development nas",
            identity_fingerprint_hash="sha256:" + "1" * 64,
            identity_fingerprint_version="source_endpoint_identity_v1",
            identity_confidence="strong_match",
        )
        self.db.add(endpoint)
        self.db.commit()
        ensure_existing_nas_adoption(self.db)
        ensure_existing_nas_adoption(self.db)
        appliance = self.db.scalar(select(NasApplianceRegistration))
        share = self.db.scalar(select(NasShareRegistration))
        assert appliance is not None and share is not None
        self.assertEqual(UUID(appliance.registration_uuid), LEGACY_APPLIANCE_UUID)
        self.assertEqual(share.location_id, LEGACY_LOCATION_ID)
        self.assertEqual(share.source_endpoint_id, endpoint.id)
        self.assertEqual(share.identity_fingerprint_hash, endpoint.identity_fingerprint_hash)
        self.assertEqual(self.db.query(NasShareRegistration).count(), 1)

    def test_pending_is_secret_free_unguessable_immutable_and_reused(self) -> None:
        first = create_pending_registration(self.db, self.request(), probe=lambda _host: GUID_A)
        second = create_pending_registration(self.db, self.request(), probe=lambda _host: GUID_A)
        self.assertEqual(first.registration_id, second.registration_id)
        self.assertGreaterEqual(len(first.registration_id.hex), 32)
        serialized = first.model_dump_json().casefold()
        for forbidden in ('"password"', '"username"', '"credential_reference"'):
            self.assertNotIn(forbidden, serialized)
        row = self.db.scalar(select(NasPendingRegistration))
        assert row is not None
        manifest = get_installer_manifest(self.db, first.registration_id)
        self.assertEqual(manifest.request_digest, row.request_digest)
        self.assertEqual(manifest.location_id, row.location_id)

    def test_expired_or_completed_pending_cannot_be_reinstalled(self) -> None:
        pending = create_pending_registration(self.db, self.request(), probe=lambda _host: GUID_A)
        row = self.db.scalar(select(NasPendingRegistration))
        assert row is not None
        row.expires_at = row.expires_at - timedelta(days=1)
        self.db.commit()
        with self.assertRaisesRegex(NasRegistrationError, "expired"):
            get_installer_manifest(self.db, pending.registration_id)
        self.assertEqual(row.state, "expired")

    def test_same_appliance_accepts_distinct_shares_but_rejects_duplicate(self) -> None:
        first = create_pending_registration(self.db, self.request(), probe=lambda _host: GUID_A)
        row = self.db.scalar(select(NasPendingRegistration).where(NasPendingRegistration.public_id == str(first.registration_id)))
        assert row is not None
        completed = complete_registration(
            self.db,
            first.registration_id,
            broker_client=FakeBroker([location(row.location_id, row.identity_fingerprint_hash, row.identity_fingerprint_version)]),
        )
        self.assertTrue(completed.created_appliance)
        with self.assertRaisesRegex(NasRegistrationError, "already registered"):
            create_pending_registration(self.db, self.request(), probe=lambda _host: GUID_A)
        second = create_pending_registration(
            self.db,
            self.request(share_name="Archive", location_name="Archive Photos"),
            probe=lambda _host: GUID_A,
        )
        second_row = self.db.scalar(select(NasPendingRegistration).where(NasPendingRegistration.public_id == str(second.registration_id)))
        assert second_row is not None
        result = complete_registration(
            self.db,
            second.registration_id,
            broker_client=FakeBroker([location(second_row.location_id, second_row.identity_fingerprint_hash, second_row.identity_fingerprint_version)]),
        )
        self.assertFalse(result.created_appliance)
        self.assertEqual(self.db.query(NasApplianceRegistration).count(), 1)
        self.assertEqual(self.db.query(NasShareRegistration).count(), 2)

    def test_same_host_with_different_appliance_identity_fails_closed(self) -> None:
        first = create_pending_registration(self.db, self.request(), probe=lambda _host: GUID_A)
        row = self.db.scalar(select(NasPendingRegistration))
        assert row is not None
        complete_registration(
            self.db,
            first.registration_id,
            broker_client=FakeBroker([location(row.location_id, row.identity_fingerprint_hash, row.identity_fingerprint_version)]),
        )
        with self.assertRaisesRegex(NasRegistrationError, "different NAS appliance"):
            create_pending_registration(
                self.db,
                self.request(share_name="Other"),
                probe=lambda _host: GUID_B,
            )

    def test_verified_appliance_network_change_preserves_share_identity(self) -> None:
        first = create_pending_registration(self.db, self.request(), probe=lambda _host: GUID_A)
        row = self.db.scalar(select(NasPendingRegistration).where(NasPendingRegistration.public_id == str(first.registration_id)))
        assert row is not None
        exact = FakeBroker([location(row.location_id, row.identity_fingerprint_hash, row.identity_fingerprint_version)])
        completed = complete_registration(self.db, first.registration_id, broker_client=exact)
        share_id = completed.share_id
        update = create_pending_registration(
            self.db,
            self.request(network_host="nas-new.example.test"),
            probe=lambda _host: GUID_A,
        )
        self.assertEqual(update.operation, "update_network_host")
        update_row = self.db.scalar(
            select(NasPendingRegistration).where(NasPendingRegistration.public_id == str(update.registration_id))
        )
        assert update_row is not None
        result = complete_registration(
            self.db,
            update.registration_id,
            broker_client=FakeBroker([
                location(update_row.location_id, update_row.identity_fingerprint_hash, update_row.identity_fingerprint_version)
            ]),
        )
        appliance = self.db.scalar(select(NasApplianceRegistration))
        assert appliance is not None
        self.assertFalse(result.created_appliance)
        self.assertFalse(result.created_share)
        self.assertEqual(result.share_id, share_id)
        self.assertEqual(appliance.network_host_normalized, "nas-new.example.test")
        self.assertEqual(self.db.query(NasShareRegistration).count(), 1)

    def test_distinct_appliances_may_share_a_display_name(self) -> None:
        requests = [
            (self.request(network_host="nas-a.example.test", share_name="PhotosA"), GUID_A),
            (self.request(network_host="nas-b.example.test", share_name="PhotosB"), GUID_B),
        ]
        for request, guid in requests:
            pending = create_pending_registration(self.db, request, probe=lambda _host, value=guid: value)
            row = self.db.scalar(
                select(NasPendingRegistration).where(NasPendingRegistration.public_id == str(pending.registration_id))
            )
            assert row is not None
            complete_registration(
                self.db,
                pending.registration_id,
                broker_client=FakeBroker([location(row.location_id, row.identity_fingerprint_hash, row.identity_fingerprint_version)]),
            )
        self.assertEqual(self.db.query(NasApplianceRegistration).count(), 2)
        self.assertEqual(
            [item.friendly_name for item in self.db.scalars(select(NasApplianceRegistration).order_by(NasApplianceRegistration.id))],
            ["Family NAS", "Family NAS"],
        )

    def test_completion_requires_exact_broker_fingerprint_and_is_idempotent(self) -> None:
        pending = create_pending_registration(self.db, self.request(), probe=lambda _host: GUID_A)
        row = self.db.scalar(select(NasPendingRegistration))
        assert row is not None
        with self.assertRaisesRegex(NasRegistrationError, "does not match"):
            complete_registration(
                self.db,
                pending.registration_id,
                broker_client=FakeBroker([location(row.location_id, "sha256:" + "9" * 64, row.identity_fingerprint_version)]),
            )
        exact = FakeBroker([location(row.location_id, row.identity_fingerprint_hash, row.identity_fingerprint_version)])
        first = complete_registration(self.db, pending.registration_id, broker_client=exact)
        second = complete_registration(self.db, pending.registration_id, broker_client=exact)
        self.assertTrue(first.created_share)
        self.assertFalse(second.created_share)
        self.assertEqual(self.db.query(NasShareRegistration).count(), 1)

    def test_location_availability_isolated_per_registered_share(self) -> None:
        appliance = NasApplianceRegistration(
            registration_uuid="11111111-1111-4111-8111-111111111111",
            friendly_name="NAS",
            server_guid_hash="sha256:" + "1" * 64,
            server_guid_masked="sha256:…111111111111",
            network_host="nas.example.test",
            network_host_normalized="nas.example.test",
        )
        self.db.add(appliance)
        self.db.flush()
        shares = []
        for index in range(2):
            share = NasShareRegistration(
                registration_uuid=f"22222222-2222-4222-8222-22222222222{index}",
                nas_appliance_id=appliance.id,
                location_id=f"linux-nas-share-{index}",
                display_name=f"Share {index}",
                share_name=f"Share{index}",
                share_name_normalized=f"share{index}",
                identity_fingerprint_hash="sha256:" + str(index + 2) * 64,
                identity_fingerprint_version="registered_nas_share_v1",
            )
            self.db.add(share)
            shares.append(share)
        self.db.commit()
        response = list_registrations(
            self.db,
            broker_client=FakeBroker([
                location(shares[0].location_id, shares[0].identity_fingerprint_hash, shares[0].identity_fingerprint_version),
                location(shares[1].location_id, shares[1].identity_fingerprint_hash, shares[1].identity_fingerprint_version, status="unavailable"),
            ]),
        )
        self.assertEqual([item.availability for item in response.registrations], ["available", "unavailable"])


if __name__ == "__main__":
    unittest.main()
