"""Stateless source endpoint enrollment planning and confirmation."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ingestion_source import IngestionSource
from app.models.source_endpoint import AccessNode, SourceEndpoint, SourceEndpointObservedPath
from app.services.source_identity.enrollment_schema import (
    EnrollmentMessage,
    SourceEndpointEnrollmentCandidate,
    SourceEndpointEnrollmentConfirmRequest,
    SourceEndpointEnrollmentConfirmResponse,
    SourceEndpointEnrollmentMatch,
    SourceEndpointEnrollmentPlanRequest,
    SourceEndpointEnrollmentPlanResponse,
)
from app.services.source_identity.durable_identity import summarize_durable_identity
from app.services.source_identity.identity_fingerprint import (
    STRONG_FINGERPRINT_STRENGTHS,
    fingerprint_from_probe,
    stable_hash,
)
from app.services.source_identity.probe_schema import SourceIdentityProbeResponse
from app.services.source_identity.probe_service import SourceIdentityProbeService


_ALIAS_MAX_LENGTH = 255


@dataclass(frozen=True)
class _AliasResult:
    alias: str | None
    alias_normalized: str | None
    blockers: tuple[EnrollmentMessage, ...] = ()


class SourceEndpointEnrollmentService:
    """Plan and confirm durable source endpoint enrollment."""

    def __init__(
        self,
        db_session: Session,
        probe_service: SourceIdentityProbeService | None = None,
    ) -> None:
        self._db = db_session
        self._probe_service = probe_service or SourceIdentityProbeService()

    def plan(self, request: SourceEndpointEnrollmentPlanRequest) -> SourceEndpointEnrollmentPlanResponse:
        """Build a read-only enrollment plan from a fresh probe."""
        return self._build_plan(request)

    def confirm(self, request: SourceEndpointEnrollmentConfirmRequest) -> SourceEndpointEnrollmentConfirmResponse:
        """Recompute the plan and write only after explicit confirmation."""
        plan_request = SourceEndpointEnrollmentPlanRequest(
            source_profile_id=request.source_profile_id,
            probe_request=request.probe_request,
            proposed_alias=request.confirmed_alias,
            selected_existing_endpoint_id=request.selected_existing_endpoint_id,
            operator_review_acknowledged=request.operator_review_acknowledged,
        )
        plan = self._build_plan(plan_request)

        blockers: list[EnrollmentMessage] = []
        already_linked_retry = plan.plan_status == "source_profile_already_linked" and not plan.blockers
        if (
            request.plan_fingerprint
            and request.plan_fingerprint != plan.plan_fingerprint
            and not already_linked_retry
        ):
            blockers.append(
                _message(
                    "plan_fingerprint_mismatch",
                    "The reviewed enrollment plan is stale. Refresh the plan before confirming.",
                )
            )
        if not request.operator_confirmed:
            blockers.append(
                _message(
                    "operator_confirmation_required",
                    "Confirm enrollment before creating or linking a source endpoint.",
                )
            )
        if plan.plan_status not in {"ready", "source_profile_already_linked"}:
            blockers.append(
                _message(
                    "plan_not_ready",
                    "The enrollment plan is not ready to confirm.",
                )
            )
        blockers.extend(plan.blockers)

        if blockers:
            return SourceEndpointEnrollmentConfirmResponse(
                enrollment_status="blocked",
                source_profile_id=request.source_profile_id,
                endpoint_action=plan.endpoint_action,
                source_profile_action=plan.source_profile_action,
                plan_fingerprint=plan.plan_fingerprint,
                **_plan_durable_identity_fields(plan),
                blockers=_dedupe_messages(blockers),
                warnings=plan.warnings,
            )

        source = self._db.get(IngestionSource, request.source_profile_id)
        if source is None or plan.candidate is None:
            return SourceEndpointEnrollmentConfirmResponse(
                enrollment_status="blocked",
                source_profile_id=request.source_profile_id,
                plan_fingerprint=plan.plan_fingerprint,
                **_plan_durable_identity_fields(plan),
                blockers=[
                    _message(
                        "source_profile_not_found",
                        "Source profile was not found.",
                    )
                ],
            )

        try:
            result = self._apply_confirm(source, plan)
            self._db.commit()
            return result
        except Exception:
            self._db.rollback()
            raise

    def _build_plan(self, request: SourceEndpointEnrollmentPlanRequest) -> SourceEndpointEnrollmentPlanResponse:
        source = self._db.get(IngestionSource, request.source_profile_id)
        if source is None:
            return self._blocked_without_probe(
                request,
                _message("source_profile_not_found", "Source profile was not found."),
            )

        probe = self._probe_service.probe(request.probe_request)
        candidate = self._build_candidate(probe)
        durable_identity = summarize_durable_identity(
            probe=probe,
            source_type=source.source_type,
            cloud_provider=source.cloud_provider,
        )
        blockers = list(self._candidate_blockers(probe, candidate))
        warnings = list(self._candidate_warnings(probe))
        required_confirmations = list(self._candidate_required_confirmations(probe, candidate))

        alias_result = _normalize_alias(request.proposed_alias)
        blockers.extend(alias_result.blockers)

        existing_endpoint_id = source.endpoint_id
        linked_endpoint = self._db.get(SourceEndpoint, existing_endpoint_id) if existing_endpoint_id is not None else None
        selected_endpoint = (
            self._db.get(SourceEndpoint, request.selected_existing_endpoint_id)
            if request.selected_existing_endpoint_id is not None
            else None
        )
        possible_matches = self._find_strong_matches(candidate)
        alias_conflict = (
            self._find_alias_conflict(alias_result.alias_normalized)
            if alias_result.alias_normalized is not None
            else None
        )

        endpoint_action = "create_new_endpoint"
        source_profile_action = "link_existing_profile"

        if existing_endpoint_id is not None:
            if linked_endpoint is None:
                blockers.append(
                    _message(
                        "linked_endpoint_not_found",
                        "Source profile is linked to an endpoint that was not found.",
                    )
                )
            else:
                mismatch = self._endpoint_mismatch(candidate, linked_endpoint, "linked_endpoint")
                if mismatch is not None:
                    blockers.append(mismatch)
                possible_matches = _prepend_match(
                    possible_matches,
                    _endpoint_match(linked_endpoint, "linked", "Source profile is already linked to this endpoint."),
                )
            if request.selected_existing_endpoint_id not in {None, existing_endpoint_id}:
                blockers.append(
                    _message(
                        "source_profile_endpoint_mismatch",
                        "Source profile is already linked to a different source endpoint.",
                    )
                )
            endpoint_action = "none"
            source_profile_action = "none"
        elif selected_endpoint is not None:
            endpoint_action = "link_existing_endpoint"
        elif request.selected_existing_endpoint_id is not None:
            blockers.append(
                _message(
                    "selected_endpoint_not_found",
                    "Selected source endpoint was not found.",
                )
            )
            endpoint_action = "none"
        elif possible_matches:
            endpoint_action = "link_existing_endpoint"
        else:
            endpoint_action = "create_new_endpoint"

        if endpoint_action == "create_new_endpoint":
            if not alias_result.alias_normalized:
                blockers.append(
                    _message(
                        "alias_required",
                        "A confirmed alias is required when creating a new source endpoint.",
                    )
                )
            elif alias_conflict is not None:
                blockers.append(
                    _message(
                        "alias_conflict",
                        "The requested endpoint alias is already in use.",
                    )
                )
        elif alias_conflict is not None and alias_conflict.id != request.selected_existing_endpoint_id:
            warnings.append(
                _message(
                    "confirmed_alias_ignored_for_existing_endpoint",
                    "Existing endpoint aliases are immutable; the selected endpoint alias will be preserved.",
                )
            )

        if selected_endpoint is not None:
            mismatch = self._endpoint_mismatch(candidate, selected_endpoint, "selected_endpoint")
            if mismatch is not None:
                blockers.append(mismatch)
            possible_matches = _prepend_match(
                possible_matches,
                _endpoint_match(selected_endpoint, "selected", "Operator-selected existing endpoint."),
            )

        if (
            possible_matches
            and endpoint_action == "link_existing_endpoint"
            and selected_endpoint is None
            and existing_endpoint_id is None
        ):
            required_confirmations.append(
                _message(
                    "select_existing_endpoint",
                    "Select the matching source endpoint before confirming.",
                )
            )

        blockers = _dedupe_messages(blockers)
        warnings = _dedupe_messages(warnings)
        required_confirmations = _dedupe_messages(required_confirmations)
        plan_status = self._plan_status(
            existing_endpoint_id=existing_endpoint_id,
            blockers=blockers,
            required_confirmations=required_confirmations,
            operator_review_acknowledged=request.operator_review_acknowledged,
            endpoint_action=endpoint_action,
            selected_endpoint=selected_endpoint,
            possible_matches=possible_matches,
        )

        fingerprint = _plan_fingerprint(
            source_profile_id=request.source_profile_id,
            candidate=candidate,
            alias_normalized=alias_result.alias_normalized,
            selected_existing_endpoint_id=request.selected_existing_endpoint_id,
            endpoint_action=endpoint_action,
            blockers=blockers,
            warnings=warnings,
            required_confirmations=required_confirmations,
        )

        return SourceEndpointEnrollmentPlanResponse(
            plan_status=plan_status,
            source_profile_id=request.source_profile_id,
            source_profile_label=source.source_label,
            existing_source_endpoint_id=existing_endpoint_id,
            endpoint_action=endpoint_action,
            source_profile_action=source_profile_action,
            proposed_alias=alias_result.alias,
            alias_normalized=alias_result.alias_normalized,
            plan_fingerprint=fingerprint,
            **durable_identity.response_fields(),
            candidate=candidate,
            possible_matches=possible_matches,
            blockers=blockers,
            warnings=warnings,
            required_confirmations=required_confirmations,
        )

    def _blocked_without_probe(
        self,
        request: SourceEndpointEnrollmentPlanRequest,
        blocker: EnrollmentMessage,
    ) -> SourceEndpointEnrollmentPlanResponse:
        fingerprint = _stable_hash(
            {
                "source_profile_id": request.source_profile_id,
                "blockers": [blocker.code],
                "probe_request": request.probe_request.model_dump(mode="json", exclude_none=True),
            }
        )
        return SourceEndpointEnrollmentPlanResponse(
            plan_status="blocked",
            source_profile_id=request.source_profile_id,
            plan_fingerprint=fingerprint,
            **summarize_durable_identity(probe=None).response_fields(),
            blockers=[blocker],
        )

    def _build_candidate(self, probe: SourceIdentityProbeResponse) -> SourceEndpointEnrollmentCandidate:
        fingerprint = fingerprint_from_probe(probe)
        safe_to_run = probe.safe_to_run if isinstance(probe.safe_to_run, str) else str(probe.safe_to_run).lower()
        return SourceEndpointEnrollmentCandidate(
            source_type=probe.source_type,
            observed_path=probe.observed_path,
            normalized_observed_path=probe.normalized_observed_path,
            source_root_candidate_path=probe.source_root_candidate.path,
            filesystem_boundary_type=probe.source_root_candidate.filesystem_boundary_type,
            is_valid_source_root_candidate=probe.source_root_candidate.is_valid_source_root_candidate,
            probe_status=probe.probe_status,
            confidence_tier=probe.confidence_tier,
            safe_to_run=safe_to_run,
            provider_name=probe.provider_name,
            provider_version=probe.provider_version,
            access_node_label=probe.access_node_summary.label,
            access_node_os_family=probe.access_node_summary.os_family,
            access_node_id=probe.access_node_summary.access_node_id,
            access_node_host_fingerprint_hash=probe.access_node_summary.host_fingerprint_hash,
            access_node_host_fingerprint_masked=probe.access_node_summary.host_fingerprint_masked,
            access_node_capabilities=probe.access_node_summary.capabilities,
            location_id=probe.location_id,
            relative_root=probe.relative_root,
            host_slot=probe.host_slot,
            runtime_slot=probe.runtime_slot,
            runtime_root=probe.runtime_root,
            identity_fingerprint_hash=fingerprint.hash_value,
            identity_fingerprint_version=fingerprint.version,
            identity_fingerprint_strength=fingerprint.strength,
        )

    def _candidate_blockers(
        self,
        probe: SourceIdentityProbeResponse,
        candidate: SourceEndpointEnrollmentCandidate,
    ) -> list[EnrollmentMessage]:
        blockers: list[EnrollmentMessage] = []
        if probe.probe_status not in {"completed", "completed_with_warnings"}:
            blockers.append(
                _message(
                    "probe_not_completed",
                    "The probe did not complete successfully.",
                )
            )
        if candidate.source_type == "cloud":
            blockers.append(
                _message(
                    "cloud_endpoint_enrollment_deferred",
                    "Cloud source endpoint enrollment is deferred for a later milestone.",
                )
            )
        if candidate.filesystem_boundary_type == "cloud_profile_scope":
            blockers.append(
                _message(
                    "cloud_profile_scope_not_enrollable",
                    "Cloud profile scopes are not enrolled as durable filesystem endpoints yet.",
                )
            )
        if candidate.filesystem_boundary_type == "nas_server_only":
            blockers.append(
                _message(
                    "nas_server_only_not_source_root",
                    "A NAS server alone is reachable but is not a runnable source root.",
                )
            )
        if not candidate.is_valid_source_root_candidate:
            blockers.append(
                _message(
                    "invalid_source_root_candidate",
                    "The probed path is not a valid source root candidate.",
                )
            )
        if probe.safe_to_run is False:
            blockers.append(
                _message(
                    "not_safe_to_run",
                    "The probe did not classify this source root as safe to run.",
                )
            )
        for item in probe.blockers:
            blockers.append(_message(item.code, item.message or "Probe reported a blocker."))
        return blockers

    def _candidate_warnings(self, probe: SourceIdentityProbeResponse) -> list[EnrollmentMessage]:
        warnings: list[EnrollmentMessage] = []
        for item in probe.warnings:
            warnings.append(_message(item.code, item.message or "Probe reported a warning."))
        if probe.probe_status == "completed_with_warnings":
            warnings.append(
                _message(
                    "probe_completed_with_warnings",
                    "The probe completed with warnings.",
                )
            )
        return warnings

    def _candidate_required_confirmations(
        self,
        probe: SourceIdentityProbeResponse,
        candidate: SourceEndpointEnrollmentCandidate,
    ) -> list[EnrollmentMessage]:
        required: list[EnrollmentMessage] = []
        if probe.safe_to_run == "needs_review":
            required.append(
                _message(
                    "safe_to_run_needs_review",
                    "Review the probe result before enrolling this endpoint.",
                )
            )
        if candidate.confidence_tier in {"medium_needs_review", "weak_manual_confirmation_required"}:
            required.append(
                _message(
                    "identity_confidence_needs_review",
                    "Endpoint identity confidence requires operator review.",
                )
            )
        if candidate.identity_fingerprint_strength == "weak":
            required.append(
                _message(
                    "weak_identity_fingerprint",
                    "The endpoint fingerprint uses weak evidence and requires manual confirmation.",
                )
            )
        return required

    def _find_strong_matches(
        self,
        candidate: SourceEndpointEnrollmentCandidate,
    ) -> list[SourceEndpointEnrollmentMatch]:
        if (
            candidate.identity_fingerprint_hash is None
            or candidate.identity_fingerprint_strength not in STRONG_FINGERPRINT_STRENGTHS
        ):
            return []
        endpoints = self._db.scalars(
            select(SourceEndpoint).where(
                SourceEndpoint.source_type == candidate.source_type,
                SourceEndpoint.identity_fingerprint_hash == candidate.identity_fingerprint_hash,
                SourceEndpoint.status != "retired",
            )
        ).all()
        return [
            _endpoint_match(
                endpoint,
                "strong",
                "Same source type and identity fingerprint hash.",
            )
            for endpoint in endpoints
        ]

    def _find_alias_conflict(self, alias_normalized: str | None) -> SourceEndpoint | None:
        if not alias_normalized:
            return None
        return self._db.scalar(
            select(SourceEndpoint).where(SourceEndpoint.alias_normalized == alias_normalized)
        )

    def _endpoint_mismatch(
        self,
        candidate: SourceEndpointEnrollmentCandidate,
        endpoint: SourceEndpoint,
        code_prefix: str,
    ) -> EnrollmentMessage | None:
        label = "Linked" if code_prefix == "linked_endpoint" else "Selected"
        if endpoint.status == "retired":
            return _message(
                f"{code_prefix}_retired",
                f"{label} source endpoint is retired.",
            )
        if endpoint.source_type != candidate.source_type:
            return _message(
                f"{code_prefix}_source_type_mismatch",
                f"{label} source endpoint has a different source type.",
            )
        if (
            candidate.identity_fingerprint_hash is not None
            and endpoint.identity_fingerprint_hash is not None
            and candidate.identity_fingerprint_hash != endpoint.identity_fingerprint_hash
        ):
            return _message(
                f"{code_prefix}_identity_mismatch",
                f"{label} source endpoint does not match the current probe fingerprint.",
            )
        return None

    def _plan_status(
        self,
        *,
        existing_endpoint_id: int | None,
        blockers: list[EnrollmentMessage],
        required_confirmations: list[EnrollmentMessage],
        operator_review_acknowledged: bool,
        endpoint_action: str,
        selected_endpoint: SourceEndpoint | None,
        possible_matches: list[SourceEndpointEnrollmentMatch],
    ) -> str:
        if blockers:
            if any(blocker.code == "alias_conflict" for blocker in blockers):
                return "alias_conflict"
            return "blocked"
        if existing_endpoint_id is not None:
            return "source_profile_already_linked"
        if endpoint_action == "link_existing_endpoint" and selected_endpoint is None and possible_matches:
            return "duplicate_match"
        if required_confirmations and not operator_review_acknowledged:
            return "needs_review"
        return "ready"

    def _apply_confirm(
        self,
        source: IngestionSource,
        plan: SourceEndpointEnrollmentPlanResponse,
    ) -> SourceEndpointEnrollmentConfirmResponse:
        candidate = plan.candidate
        if candidate is None:
            return SourceEndpointEnrollmentConfirmResponse(
                enrollment_status="blocked",
                source_profile_id=source.id,
                plan_fingerprint=plan.plan_fingerprint,
                **_plan_durable_identity_fields(plan),
                blockers=[
                    _message(
                        "candidate_missing",
                        "Enrollment candidate is missing.",
                    )
                ],
            )

        created_access_node = False
        created_endpoint = False
        created_observed_path = False

        access_node, created_access_node = self._get_or_create_access_node(plan)

        endpoint: SourceEndpoint | None = None
        already_linked = False
        if source.endpoint_id is not None:
            endpoint = self._db.get(SourceEndpoint, source.endpoint_id)
            already_linked = True
        elif plan.endpoint_action == "link_existing_endpoint" and plan.possible_matches:
            endpoint = self._db.get(SourceEndpoint, plan.possible_matches[0].source_endpoint_id)
        elif plan.endpoint_action == "create_new_endpoint":
            endpoint = SourceEndpoint(
                source_type=candidate.source_type,
                alias=plan.proposed_alias or "",
                alias_normalized=plan.alias_normalized or "",
                status="active",
                identity_fingerprint_hash=candidate.identity_fingerprint_hash,
                identity_fingerprint_version=candidate.identity_fingerprint_version,
                identity_confidence=candidate.confidence_tier,
                evidence_summary_json=_safe_json(
                    {
                        "source_root_candidate_path": candidate.source_root_candidate_path,
                        "filesystem_boundary_type": candidate.filesystem_boundary_type,
                        "probe_status": candidate.probe_status,
                        "confidence_tier": candidate.confidence_tier,
                    }
                ),
                created_from_access_node=access_node,
            )
            self._db.add(endpoint)
            self._db.flush()
            created_endpoint = True

        if endpoint is None:
            return SourceEndpointEnrollmentConfirmResponse(
                enrollment_status="blocked",
                source_profile_id=source.id,
                plan_fingerprint=plan.plan_fingerprint,
                **_plan_durable_identity_fields(plan),
                blockers=[
                    _message(
                        "source_endpoint_not_found",
                        "Source endpoint was not found.",
                    )
                ],
            )

        observed_path, created_observed_path = self._get_or_create_observed_path(
            endpoint=endpoint,
            access_node=access_node,
            plan=plan,
        )
        source.endpoint_id = endpoint.id
        self._db.add(source)
        self._db.flush()

        return SourceEndpointEnrollmentConfirmResponse(
            enrollment_status="completed",
            source_profile_id=source.id,
            source_endpoint_id=endpoint.id,
            source_profile_endpoint_id=source.endpoint_id,
            endpoint_action=plan.endpoint_action,
            source_profile_action=plan.source_profile_action,
            already_linked=already_linked,
            created_endpoint=created_endpoint,
            created_access_node=created_access_node,
            created_observed_path=created_observed_path,
            observed_path_id=observed_path.id,
            plan_fingerprint=plan.plan_fingerprint,
            **_plan_durable_identity_fields(plan),
            warnings=plan.warnings,
        )

    def _get_or_create_access_node(
        self,
        plan: SourceEndpointEnrollmentPlanResponse,
    ) -> tuple[AccessNode, bool]:
        candidate = plan.candidate
        if candidate is None:
            raise ValueError("Candidate is required.")
        access_node_uuid = candidate.access_node_id or _access_node_uuid(candidate)
        existing = self._db.scalar(
            select(AccessNode).where(AccessNode.access_node_uuid == access_node_uuid)
        )
        now = datetime.now(timezone.utc)
        if existing is not None:
            existing.last_seen_at = now
            if candidate.access_node_os_family == "linux":
                existing.host_fingerprint_hash = candidate.access_node_host_fingerprint_hash
                existing.host_fingerprint_masked = candidate.access_node_host_fingerprint_masked
                existing.capabilities_json = _safe_json(candidate.access_node_capabilities)
            self._db.add(existing)
            self._db.flush()
            return existing, False

        access_node = AccessNode(
            access_node_uuid=access_node_uuid,
            label=candidate.access_node_label,
            os_family=candidate.access_node_os_family,
            provider_name=candidate.provider_name,
            provider_version=candidate.provider_version,
            host_fingerprint_hash=candidate.access_node_host_fingerprint_hash,
            host_fingerprint_masked=candidate.access_node_host_fingerprint_masked,
            capabilities_json=_safe_json(candidate.access_node_capabilities),
            status="active",
            last_seen_at=now,
        )
        self._db.add(access_node)
        self._db.flush()
        return access_node, True

    def _get_or_create_observed_path(
        self,
        *,
        endpoint: SourceEndpoint,
        access_node: AccessNode,
        plan: SourceEndpointEnrollmentPlanResponse,
    ) -> tuple[SourceEndpointObservedPath, bool]:
        candidate = plan.candidate
        if candidate is None:
            raise ValueError("Candidate is required.")
        normalized_path = candidate.normalized_observed_path or candidate.observed_path or ""
        observed_path = candidate.observed_path or normalized_path
        existing = self._db.scalar(
            select(SourceEndpointObservedPath).where(
                SourceEndpointObservedPath.source_endpoint_id == endpoint.id,
                SourceEndpointObservedPath.access_node_id == access_node.id,
                SourceEndpointObservedPath.normalized_observed_path == normalized_path,
            )
        )
        now = datetime.now(timezone.utc)
        if existing is not None:
            existing.last_seen_at = now
            if candidate.probe_status in {"completed", "completed_with_warnings"}:
                existing.last_success_at = now
            self._db.add(existing)
            self._db.flush()
            return existing, False

        observed = SourceEndpointObservedPath(
            source_endpoint_id=endpoint.id,
            access_node_id=access_node.id,
            observed_path=observed_path,
            normalized_observed_path=normalized_path,
            filesystem_boundary_type=candidate.filesystem_boundary_type,
            source_root_candidate_path=candidate.source_root_candidate_path,
            is_valid_source_root_candidate=candidate.is_valid_source_root_candidate,
            probe_provider_name=candidate.provider_name,
            probe_provider_version=candidate.provider_version,
            probe_status=candidate.probe_status,
            confidence_tier=candidate.confidence_tier,
            match_status="matched" if plan.endpoint_action == "link_existing_endpoint" else "not_compared",
            safe_to_run=candidate.safe_to_run,
            blockers_json=_safe_json([message.model_dump(mode="json") for message in plan.blockers]),
            warnings_json=_safe_json([message.model_dump(mode="json") for message in plan.warnings]),
            evidence_summary_json=_safe_json(
                {
                    "source_root_candidate_path": candidate.source_root_candidate_path,
                    "filesystem_boundary_type": candidate.filesystem_boundary_type,
                    "probe_status": candidate.probe_status,
                    "confidence_tier": candidate.confidence_tier,
                    "location_id": candidate.location_id,
                    "relative_root": candidate.relative_root,
                    "host_slot": candidate.host_slot,
                    "runtime_slot": candidate.runtime_slot,
                }
            ),
            last_seen_at=now,
            last_success_at=now if candidate.probe_status in {"completed", "completed_with_warnings"} else None,
        )
        self._db.add(observed)
        self._db.flush()
        return observed, True


def _message(code: str, message: str) -> EnrollmentMessage:
    return EnrollmentMessage(code=code, message=message)


def _dedupe_messages(messages: list[EnrollmentMessage]) -> list[EnrollmentMessage]:
    seen: set[str] = set()
    deduped: list[EnrollmentMessage] = []
    for message in messages:
        if message.code in seen:
            continue
        seen.add(message.code)
        deduped.append(message)
    return deduped


def _normalize_alias(alias: str | None) -> _AliasResult:
    if alias is None:
        return _AliasResult(alias=None, alias_normalized=None)
    collapsed = re.sub(r"\s+", " ", alias.strip())
    blockers: list[EnrollmentMessage] = []
    if not collapsed:
        return _AliasResult(alias=None, alias_normalized=None)
    if any(ord(character) < 32 for character in collapsed):
        blockers.append(
            _message(
                "alias_contains_control_character",
                "Endpoint alias contains an unsupported control character.",
            )
        )
    if len(collapsed) > _ALIAS_MAX_LENGTH:
        blockers.append(
            _message(
                "alias_too_long",
                "Endpoint alias must be 255 characters or fewer.",
            )
        )
    return _AliasResult(
        alias=collapsed,
        alias_normalized=collapsed.casefold(),
        blockers=tuple(blockers),
    )


def _access_node_uuid(candidate: SourceEndpointEnrollmentCandidate) -> str:
    return (
        "access-node:"
        + hashlib.sha256(
            _safe_json(
                {
                    "label": candidate.access_node_label,
                    "os_family": candidate.access_node_os_family,
                    "provider_name": candidate.provider_name,
                    "provider_version": candidate.provider_version,
                }
            ).encode("utf-8")
        ).hexdigest()[:48]
    )


def _endpoint_match(endpoint: SourceEndpoint, strength: str, reason: str) -> SourceEndpointEnrollmentMatch:
    return SourceEndpointEnrollmentMatch(
        source_endpoint_id=endpoint.id,
        alias=endpoint.alias,
        source_type=endpoint.source_type,
        match_strength=strength,
        match_reason=reason,
        identity_confidence=endpoint.identity_confidence,
    )


def _prepend_match(
    matches: list[SourceEndpointEnrollmentMatch],
    match: SourceEndpointEnrollmentMatch,
) -> list[SourceEndpointEnrollmentMatch]:
    filtered = [existing for existing in matches if existing.source_endpoint_id != match.source_endpoint_id]
    return [match, *filtered]


def _plan_durable_identity_fields(plan: SourceEndpointEnrollmentPlanResponse) -> dict[str, object]:
    return {
        "durable_identity_status": plan.durable_identity_status,
        "durable_identity_reason": plan.durable_identity_reason,
        "durable_identity_identifier_type": plan.durable_identity_identifier_type,
        "durable_identity_identifier": plan.durable_identity_identifier,
        "durable_identity_evidence": list(plan.durable_identity_evidence),
    }


def _plan_fingerprint(
    *,
    source_profile_id: int,
    candidate: SourceEndpointEnrollmentCandidate,
    alias_normalized: str | None,
    selected_existing_endpoint_id: int | None,
    endpoint_action: str,
    blockers: list[EnrollmentMessage],
    warnings: list[EnrollmentMessage],
    required_confirmations: list[EnrollmentMessage],
) -> str:
    # Warnings can reflect transient read-only command timing. Candidate identity,
    # blockers, and required confirmations are the safety-relevant plan inputs.
    return _stable_hash(
        {
            "source_profile_id": source_profile_id,
            "candidate": {
                "source_type": candidate.source_type,
                "normalized_observed_path": candidate.normalized_observed_path,
                "source_root_candidate_path": candidate.source_root_candidate_path,
                "filesystem_boundary_type": candidate.filesystem_boundary_type,
                "is_valid_source_root_candidate": candidate.is_valid_source_root_candidate,
                "safe_to_run": candidate.safe_to_run,
                "confidence_tier": candidate.confidence_tier,
                "identity_fingerprint_hash": candidate.identity_fingerprint_hash,
                "identity_fingerprint_version": candidate.identity_fingerprint_version,
                "identity_fingerprint_strength": candidate.identity_fingerprint_strength,
                "provider_name": candidate.provider_name,
                "provider_version": candidate.provider_version,
                "access_node_label": candidate.access_node_label,
                "access_node_os_family": candidate.access_node_os_family,
                "access_node_id": candidate.access_node_id,
                "location_id": candidate.location_id,
                "relative_root": candidate.relative_root,
                "host_slot": candidate.host_slot,
                "runtime_slot": candidate.runtime_slot,
                "runtime_root": candidate.runtime_root,
            },
            # Existing endpoint aliases are immutable and are not confirmation
            # input when a profile is linked to an existing endpoint.
            "alias_normalized": alias_normalized if endpoint_action == "create_new_endpoint" else None,
            "selected_existing_endpoint_id": selected_existing_endpoint_id,
            "endpoint_action": endpoint_action,
            "blockers": [message.code for message in blockers],
            "required_confirmations": [message.code for message in required_confirmations],
        }
    )


def _stable_hash(payload: dict[str, Any]) -> str:
    return stable_hash(payload)


def _safe_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
