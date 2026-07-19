from __future__ import annotations

import unittest

from sqlalchemy import inspect, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy import create_engine

from app.models.ingestion_source import IngestionSource
from app.models.source_endpoint import (
    SOURCE_ENDPOINT_TYPES,
    AccessNode,
    SourceEndpoint,
    SourceEndpointAliasEvent,
    SourceEndpointObservedPath,
)
from app.services.source_endpoint_schema import ensure_source_endpoint_schema


class SourceEndpointSchemaTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
        self.db = Session(self.engine)
        self._create_legacy_ingestion_sources_table()

    def tearDown(self) -> None:
        self.db.close()
        self.engine.dispose()

    def _create_legacy_ingestion_sources_table(self) -> None:
        with self.engine.begin() as connection:
            connection.execute(
                text(
                    """
                    CREATE TABLE ingestion_sources (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        source_label VARCHAR(255) NOT NULL,
                        source_label_normalized VARCHAR(255) NOT NULL,
                        source_type VARCHAR(64) NOT NULL DEFAULT 'local_folder',
                        source_root_path VARCHAR(2048) NULL,
                        source_root_path_normalized VARCHAR(2048) NOT NULL DEFAULT '',
                        profile_status VARCHAR(32) NOT NULL DEFAULT 'active',
                        cloud_provider VARCHAR(64) NULL,
                        acquisition_method VARCHAR(64) NULL,
                        managed_staging_path VARCHAR(2048) NULL,
                        account_username VARCHAR(255) NULL,
                        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        CONSTRAINT uq_ingestion_sources_lookup
                            UNIQUE (source_label_normalized, source_type, source_root_path_normalized)
                    )
                    """
                )
            )
            connection.execute(
                text(
                    """
                    INSERT INTO ingestion_sources (
                        source_label,
                        source_label_normalized,
                        source_type,
                        source_root_path,
                        source_root_path_normalized,
                        profile_status
                    )
                    VALUES (
                        'Legacy Source',
                        'legacy source',
                        'external_drive',
                        'E:\\Photos',
                        'e:\\photos',
                        'active'
                    )
                    """
                )
            )

    def test_schema_creates_endpoint_tables_and_nullable_source_link(self) -> None:
        summary = ensure_source_endpoint_schema(self.db)

        self.assertEqual(
            summary.created_tables,
            [
                "access_nodes",
                "source_endpoints",
                "source_endpoint_alias_events",
                "source_endpoint_observed_paths",
            ],
        )
        self.assertIn("ingestion_sources.endpoint_id", summary.added_columns)
        self.assertIn("ingestion_sources.endpoint_relative_root", summary.added_columns)
        self.assertIn("ix_ingestion_sources_endpoint_id", summary.added_indexes)

        inspector = inspect(self.engine)
        table_names = set(inspector.get_table_names())
        self.assertIn("access_nodes", table_names)
        self.assertIn("source_endpoints", table_names)
        self.assertIn("source_endpoint_alias_events", table_names)
        self.assertIn("source_endpoint_observed_paths", table_names)

        ingestion_columns = {column["name"]: column for column in inspector.get_columns("ingestion_sources")}
        self.assertIn("endpoint_id", ingestion_columns)
        self.assertTrue(ingestion_columns["endpoint_id"]["nullable"])
        self.assertIn("endpoint_relative_root", ingestion_columns)
        self.assertTrue(ingestion_columns["endpoint_relative_root"]["nullable"])

        legacy_source = self.db.scalar(
            select(IngestionSource).where(IngestionSource.source_label == "Legacy Source")
        )
        self.assertIsNotNone(legacy_source)
        self.assertIsNone(legacy_source.endpoint_id)
        self.assertIsNone(legacy_source.endpoint_relative_root)

    def test_schema_helper_is_idempotent(self) -> None:
        ensure_source_endpoint_schema(self.db)
        second = ensure_source_endpoint_schema(self.db)

        self.assertEqual(second.created_tables, [])
        self.assertEqual(second.added_columns, [])
        self.assertEqual(second.added_indexes, [])

    def test_models_can_link_access_node_endpoint_and_observed_path(self) -> None:
        ensure_source_endpoint_schema(self.db)

        access_node = AccessNode(
            access_node_uuid="node-test-0001",
            label="Chuck Windows PC",
            os_family="windows",
            provider_name="windows_non_admin_probe_v1",
            provider_version="1",
            host_fingerprint_hash="host_hash_abcd",
            host_fingerprint_masked="host_...abcd",
            capabilities_json='{"path_exists_check": true}',
        )
        endpoint = SourceEndpoint(
            endpoint_uuid="endpoint-test-0001",
            source_type="nas",
            alias="HENDERSON NAS Photos",
            alias_normalized="henderson nas photos",
            status="active",
            identity_fingerprint_hash="endpoint_hash_1234",
            identity_fingerprint_version="v1",
            identity_confidence="medium_needs_review",
            evidence_summary_json='{"network_share_evidence": "present"}',
            created_from_access_node=access_node,
        )
        observed_path = SourceEndpointObservedPath(
            source_endpoint=endpoint,
            access_node=access_node,
            observed_path=r"\\HENDERSON-NAS\Photos",
            normalized_observed_path=r"\\henderson-nas\photos",
            filesystem_boundary_type="nas_share_root",
            source_root_candidate_path=r"\\HENDERSON-NAS\Photos",
            is_valid_source_root_candidate=True,
            probe_provider_name="windows_non_admin_probe_v1",
            probe_provider_version="1",
            probe_status="completed",
            confidence_tier="medium_needs_review",
            match_status="needs_review",
            safe_to_run="needs_review",
            blockers_json="[]",
            warnings_json="[]",
            evidence_summary_json='{"path_evidence": "present"}',
        )

        self.db.add(observed_path)
        self.db.commit()

        saved_endpoint = self.db.scalar(
            select(SourceEndpoint).where(SourceEndpoint.alias_normalized == "henderson nas photos")
        )
        self.assertIsNotNone(saved_endpoint)
        self.assertEqual(saved_endpoint.created_from_access_node.label, "Chuck Windows PC")
        self.assertEqual(len(saved_endpoint.observed_paths), 1)
        self.assertEqual(saved_endpoint.observed_paths[0].safe_to_run, "needs_review")

    def test_alias_normalized_uniqueness_is_enforced(self) -> None:
        ensure_source_endpoint_schema(self.db)

        self.db.add_all(
            [
                SourceEndpoint(
                    endpoint_uuid="endpoint-alias-0001",
                    source_type="local",
                    alias="Archive",
                    alias_normalized="archive",
                    identity_confidence="unknown",
                ),
                SourceEndpoint(
                    endpoint_uuid="endpoint-alias-0002",
                    source_type="external_device",
                    alias="Archive Duplicate",
                    alias_normalized="archive",
                    identity_confidence="unknown",
                ),
            ]
        )

        with self.assertRaises(IntegrityError):
            self.db.commit()

    def test_alias_event_records_only_endpoint_display_name_change(self) -> None:
        ensure_source_endpoint_schema(self.db)
        endpoint = SourceEndpoint(
            endpoint_uuid="endpoint-alias-event",
            source_type="local",
            alias="Old Name",
            alias_normalized="old name",
            identity_confidence="strong_match",
        )
        self.db.add(endpoint)
        self.db.flush()
        event = SourceEndpointAliasEvent(
            source_endpoint_id=endpoint.id,
            old_alias="Old Name",
            new_alias="New Name",
            action_source="test",
        )
        self.db.add(event)
        self.db.commit()

        saved = self.db.scalar(select(SourceEndpointAliasEvent))
        self.assertIsNotNone(saved)
        self.assertEqual(saved.source_endpoint_id, endpoint.id)
        self.assertEqual(saved.old_alias, "Old Name")
        self.assertEqual(saved.new_alias, "New Name")

    def test_source_type_values_are_storable(self) -> None:
        ensure_source_endpoint_schema(self.db)

        endpoints = [
            SourceEndpoint(
                endpoint_uuid=f"endpoint-type-{source_type}",
                source_type=source_type,
                alias=f"{source_type} endpoint",
                alias_normalized=f"{source_type} endpoint",
                identity_confidence="unknown",
            )
            for source_type in sorted(SOURCE_ENDPOINT_TYPES)
        ]
        self.db.add_all(endpoints)
        self.db.commit()

        saved_types = set(self.db.scalars(select(SourceEndpoint.source_type)).all())
        self.assertEqual(saved_types, SOURCE_ENDPOINT_TYPES)

    def test_observed_path_payload_fields_store_sanitized_summaries(self) -> None:
        ensure_source_endpoint_schema(self.db)

        access_node = AccessNode(
            access_node_uuid="node-test-0002",
            label="Windows Test Node",
            os_family="windows",
        )
        endpoint = SourceEndpoint(
            endpoint_uuid="endpoint-safe-payload",
            source_type="external_device",
            alias="External Photos",
            alias_normalized="external photos",
            identity_confidence="medium_needs_review",
        )
        observed_path = SourceEndpointObservedPath(
            source_endpoint=endpoint,
            access_node=access_node,
            observed_path="E:\\Photos",
            normalized_observed_path="e:\\photos",
            filesystem_boundary_type="external_folder",
            is_valid_source_root_candidate=True,
            probe_status="completed",
            confidence_tier="medium_needs_review",
            match_status="needs_review",
            safe_to_run="needs_review",
            blockers_json="[]",
            warnings_json='["operator_review_required"]',
            evidence_summary_json='{"volume_evidence": "present", "path_evidence": "present"}',
        )
        self.db.add(observed_path)
        self.db.commit()

        saved = self.db.scalar(select(SourceEndpointObservedPath))
        self.assertIsNotNone(saved)
        combined_payload = "\n".join(
            value or ""
            for value in (saved.blockers_json, saved.warnings_json, saved.evidence_summary_json)
        )
        self.assertNotIn("Volume Serial Number is", combined_payload)
        self.assertNotIn("USBSTOR", combined_payload)
        self.assertNotIn("token", combined_payload.lower())
        self.assertNotIn("password", combined_payload.lower())


if __name__ == "__main__":
    unittest.main()
