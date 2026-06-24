"""Pure planning primitives for future iCloud new-count acquisition.

This module intentionally does not launch icloudpd or expose an API mode.  It
turns an ordered, source-scoped known-state evaluation into a deterministic
selection plan so mixed known/new semantics can be tested independently of the
current fixed-window adapter.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import PurePosixPath
from typing import Sequence

from app.services.icloud_acquisition.known_state_service import CandidateKnownState


DEFAULT_CANDIDATE_SCAN_LIMIT = 500
MAX_CANDIDATE_SCAN_LIMIT = 500
MAX_TARGET_NEW_ITEM_COUNT = 500

PLAN_CLASSIFICATION_COMPLETE = "complete"
PLAN_CLASSIFICATION_PARTIAL = "partial"
PLAN_CLASSIFICATION_BLOCKED = "blocked"
PLAN_CLASSIFICATION_TOOLING_LIMITED = "tooling_limited"

STOP_TARGET_NEW_COUNT_REACHED = "target_new_count_reached"
STOP_NO_MORE_CANDIDATES = "no_more_candidates"
STOP_SCAN_LIMIT_REACHED = "scan_limit_reached"
STOP_TOOLING_LIMIT_REACHED = "tooling_limit_reached"
STOP_STAGED_UNKNOWN_PENDING_INTAKE = "staged_unknown_pending_intake"
STOP_IDENTITY_UNAVAILABLE = "identity_unavailable"
STOP_LOGICAL_ITEM_IDENTITY_AMBIGUOUS = "logical_item_identity_ambiguous"

BLOCK_STAGED_UNKNOWN_PENDING_INTAKE = "STAGED_UNKNOWN_PENDING_INTAKE"
BLOCK_IDENTITY_UNAVAILABLE = "IDENTITY_UNAVAILABLE"
BLOCK_LOGICAL_ITEM_IDENTITY_AMBIGUOUS = "LOGICAL_ITEM_IDENTITY_AMBIGUOUS"

STILL_EXTENSIONS = frozenset({".heic", ".heif", ".jpg", ".jpeg", ".png", ".tif", ".tiff"})
MOTION_EXTENSION = ".mov"
APPROVED_MOTION_SUFFIXES = ("_hevc",)


@dataclass(frozen=True)
class PlannedNewCountResource:
    raw_line: str
    normalized_source_relative_path: str | None
    known_state: str
    already_known: bool
    staged_known: bool
    unknown_identity: bool
    selected_for_download: bool = False


@dataclass(frozen=True)
class PlannedNewCountItem:
    logical_item_key: str
    grouping: str
    identity_ambiguous: bool
    already_known: bool
    staged_unknown_pending_intake: bool
    selected_new: bool
    resources: tuple[PlannedNewCountResource, ...]


@dataclass(frozen=True)
class NewCountSelectionPlan:
    classification: str
    stopping_reason: str
    blocking_reasons: tuple[str, ...]
    guidance: str | None
    target_new_item_count: int
    candidate_scan_limit: int
    candidate_scan_item_count: int
    candidate_resource_count: int
    known_skipped_item_count: int
    known_skipped_resource_count: int
    selected_new_item_count: int
    selected_new_resource_count: int
    staged_pending_item_count: int
    staged_pending_resource_count: int
    unknown_identity_resource_count: int
    ambiguous_item_count: int
    remaining_unselected_new_item_count: int
    candidate_source_exhausted: bool
    items: tuple[PlannedNewCountItem, ...]


@dataclass(frozen=True)
class _CandidateEnvelope:
    index: int
    candidate: CandidateKnownState
    normalized_path: str | None
    parent_key: str | None
    stem_key: str | None
    extension: str | None


def _normalize_path(value: str | None) -> str | None:
    normalized = (value or "").strip().replace("\\", "/").lstrip("/")
    return normalized or None


def _candidate_envelopes(candidates: Sequence[CandidateKnownState]) -> list[_CandidateEnvelope]:
    envelopes: list[_CandidateEnvelope] = []
    for index, candidate in enumerate(candidates):
        normalized_path = _normalize_path(candidate.normalized_source_relative_path)
        if normalized_path is None:
            envelopes.append(
                _CandidateEnvelope(
                    index=index,
                    candidate=candidate,
                    normalized_path=None,
                    parent_key=None,
                    stem_key=None,
                    extension=None,
                )
            )
            continue

        path = PurePosixPath(normalized_path)
        parent = "" if str(path.parent) == "." else str(path.parent).casefold()
        envelopes.append(
            _CandidateEnvelope(
                index=index,
                candidate=candidate,
                normalized_path=normalized_path,
                parent_key=parent,
                stem_key=path.stem.casefold(),
                extension=path.suffix.casefold(),
            )
        )
    return envelopes


def _motion_base(stem_key: str) -> tuple[str, str]:
    for suffix in APPROVED_MOTION_SUFFIXES:
        if stem_key.endswith(suffix) and stem_key[: -len(suffix)]:
            return stem_key[: -len(suffix)], "live_photo_motion_suffix"
    return stem_key, "live_photo_simple_basename"


def _group_candidates(candidates: Sequence[CandidateKnownState]) -> list[PlannedNewCountItem]:
    envelopes = _candidate_envelopes(candidates)
    stills_by_key: dict[tuple[str, str], list[_CandidateEnvelope]] = {}
    for envelope in envelopes:
        if (
            envelope.normalized_path is not None
            and envelope.parent_key is not None
            and envelope.stem_key is not None
            and envelope.extension in STILL_EXTENSIONS
        ):
            stills_by_key.setdefault((envelope.parent_key, envelope.stem_key), []).append(envelope)

    group_keys: dict[int, str] = {}
    groupings: dict[str, str] = {}
    ambiguous_groups: set[str] = set()
    for envelope in envelopes:
        default_key = f"resource:{envelope.index}"
        group_key = default_key
        grouping = "single_resource"

        if envelope.normalized_path is None:
            grouping = "identity_unavailable"
        elif (
            envelope.extension == MOTION_EXTENSION
            and envelope.parent_key is not None
            and envelope.stem_key is not None
        ):
            still_base, motion_grouping = _motion_base(envelope.stem_key)
            matching_stills = stills_by_key.get((envelope.parent_key, still_base), [])
            if len(matching_stills) == 1:
                group_key = f"still:{matching_stills[0].index}"
                grouping = motion_grouping
            elif len(matching_stills) > 1:
                grouping = "ambiguous_live_photo_companion"
                ambiguous_groups.add(group_key)

        if envelope.extension in STILL_EXTENSIONS:
            group_key = f"still:{envelope.index}"

        group_keys[envelope.index] = group_key
        existing_grouping = groupings.get(group_key)
        if existing_grouping is None or existing_grouping == "single_resource":
            groupings[group_key] = grouping

    grouped: dict[str, list[_CandidateEnvelope]] = {}
    order: list[str] = []
    for envelope in envelopes:
        group_key = group_keys[envelope.index]
        if group_key not in grouped:
            grouped[group_key] = []
            order.append(group_key)
        grouped[group_key].append(envelope)

    items: list[PlannedNewCountItem] = []
    for group_key in order:
        members = grouped[group_key]
        resources = tuple(
            PlannedNewCountResource(
                raw_line=member.candidate.raw_line,
                normalized_source_relative_path=member.normalized_path,
                known_state=member.candidate.known_state,
                already_known=member.candidate.already_known,
                staged_known=member.candidate.staged_known,
                unknown_identity=member.candidate.unknown_identity or member.normalized_path is None,
            )
            for member in members
        )
        primary_path = next(
            (resource.normalized_source_relative_path for resource in resources if resource.normalized_source_relative_path),
            None,
        )
        items.append(
            PlannedNewCountItem(
                logical_item_key=primary_path or group_key,
                grouping=groupings[group_key],
                identity_ambiguous=group_key in ambiguous_groups,
                already_known=all(resource.already_known for resource in resources),
                staged_unknown_pending_intake=any(
                    resource.staged_known and not resource.already_known for resource in resources
                ),
                selected_new=False,
                resources=resources,
            )
        )
    return items


def _validate_counts(*, target_new_item_count: int, candidate_scan_limit: int) -> None:
    if target_new_item_count < 1 or target_new_item_count > MAX_TARGET_NEW_ITEM_COUNT:
        raise ValueError(
            f"target_new_item_count must be between 1 and {MAX_TARGET_NEW_ITEM_COUNT}."
        )
    if candidate_scan_limit < 1 or candidate_scan_limit > MAX_CANDIDATE_SCAN_LIMIT:
        raise ValueError(
            f"candidate_scan_limit must be between 1 and {MAX_CANDIDATE_SCAN_LIMIT}."
        )
    if candidate_scan_limit < target_new_item_count:
        raise ValueError("candidate_scan_limit must be at least target_new_item_count.")


def _blocked_plan(
    *,
    items: tuple[PlannedNewCountItem, ...],
    target_new_item_count: int,
    candidate_scan_limit: int,
    candidate_source_exhausted: bool,
    blocking_reasons: tuple[str, ...],
    stopping_reason: str,
    guidance: str,
) -> NewCountSelectionPlan:
    resources = tuple(resource for item in items for resource in item.resources)
    return NewCountSelectionPlan(
        classification=PLAN_CLASSIFICATION_BLOCKED,
        stopping_reason=stopping_reason,
        blocking_reasons=blocking_reasons,
        guidance=guidance,
        target_new_item_count=target_new_item_count,
        candidate_scan_limit=candidate_scan_limit,
        candidate_scan_item_count=len(items),
        candidate_resource_count=len(resources),
        known_skipped_item_count=sum(1 for item in items if item.already_known),
        known_skipped_resource_count=sum(1 for resource in resources if resource.already_known),
        selected_new_item_count=0,
        selected_new_resource_count=0,
        staged_pending_item_count=sum(1 for item in items if item.staged_unknown_pending_intake),
        staged_pending_resource_count=sum(
            1 for resource in resources if resource.staged_known and not resource.already_known
        ),
        unknown_identity_resource_count=sum(1 for resource in resources if resource.unknown_identity),
        ambiguous_item_count=sum(1 for item in items if item.identity_ambiguous),
        remaining_unselected_new_item_count=sum(1 for item in items if not item.already_known),
        candidate_source_exhausted=candidate_source_exhausted,
        items=items,
    )


def plan_new_count_selection(
    candidates: Sequence[CandidateKnownState],
    *,
    target_new_item_count: int,
    candidate_scan_limit: int = DEFAULT_CANDIDATE_SCAN_LIMIT,
    candidate_source_exhausted: bool = False,
) -> NewCountSelectionPlan:
    """Plan unknown resources for up to ``target_new_item_count`` logical items.

    Candidates must be ordered newest to oldest and already evaluated against
    one selected Source Profile.  The function performs no I/O and never starts
    acquisition.
    """

    _validate_counts(
        target_new_item_count=target_new_item_count,
        candidate_scan_limit=candidate_scan_limit,
    )
    all_items = _group_candidates(candidates)
    scan_limit_truncated_candidates = len(all_items) > candidate_scan_limit
    scan_limit_was_reached = (
        scan_limit_truncated_candidates
        or (len(all_items) == candidate_scan_limit and not candidate_source_exhausted)
    )
    considered_items = tuple(all_items[:candidate_scan_limit])

    if any(item.staged_unknown_pending_intake for item in considered_items):
        return _blocked_plan(
            items=considered_items,
            target_new_item_count=target_new_item_count,
            candidate_scan_limit=candidate_scan_limit,
            candidate_source_exhausted=candidate_source_exhausted,
            blocking_reasons=(BLOCK_STAGED_UNKNOWN_PENDING_INTAKE,),
            stopping_reason=STOP_STAGED_UNKNOWN_PENDING_INTAKE,
            guidance="Run Source Intake first for staged unknown resources.",
        )

    if any(resource.unknown_identity for item in considered_items for resource in item.resources):
        return _blocked_plan(
            items=considered_items,
            target_new_item_count=target_new_item_count,
            candidate_scan_limit=candidate_scan_limit,
            candidate_source_exhausted=candidate_source_exhausted,
            blocking_reasons=(BLOCK_IDENTITY_UNAVAILABLE,),
            stopping_reason=STOP_IDENTITY_UNAVAILABLE,
            guidance="Candidate identity is incomplete; do not suppress or selectively acquire it.",
        )

    if any(item.identity_ambiguous for item in considered_items):
        return _blocked_plan(
            items=considered_items,
            target_new_item_count=target_new_item_count,
            candidate_scan_limit=candidate_scan_limit,
            candidate_source_exhausted=candidate_source_exhausted,
            blocking_reasons=(BLOCK_LOGICAL_ITEM_IDENTITY_AMBIGUOUS,),
            stopping_reason=STOP_LOGICAL_ITEM_IDENTITY_AMBIGUOUS,
            guidance="Logical item grouping is ambiguous; exact selected acquisition is unsafe.",
        )

    selected_count = 0
    planned_items: list[PlannedNewCountItem] = []
    for item in considered_items:
        if item.already_known or selected_count >= target_new_item_count:
            planned_items.append(item)
            continue

        selected_count += 1
        planned_items.append(
            replace(
                item,
                selected_new=True,
                resources=tuple(
                    replace(resource, selected_for_download=not resource.already_known)
                    for resource in item.resources
                ),
            )
        )

    planned_items_tuple = tuple(planned_items)
    resources = tuple(resource for item in planned_items_tuple for resource in item.resources)
    selected_resource_count = sum(1 for resource in resources if resource.selected_for_download)
    unselected_new_count = sum(
        1 for item in planned_items_tuple if not item.already_known and not item.selected_new
    )

    if selected_count >= target_new_item_count:
        classification = PLAN_CLASSIFICATION_COMPLETE
        stopping_reason = STOP_TARGET_NEW_COUNT_REACHED
    elif scan_limit_was_reached:
        classification = PLAN_CLASSIFICATION_PARTIAL
        stopping_reason = STOP_SCAN_LIMIT_REACHED
    elif candidate_source_exhausted:
        classification = PLAN_CLASSIFICATION_PARTIAL
        stopping_reason = STOP_NO_MORE_CANDIDATES
    else:
        classification = PLAN_CLASSIFICATION_TOOLING_LIMITED
        stopping_reason = STOP_TOOLING_LIMIT_REACHED

    return NewCountSelectionPlan(
        classification=classification,
        stopping_reason=stopping_reason,
        blocking_reasons=(),
        guidance=None,
        target_new_item_count=target_new_item_count,
        candidate_scan_limit=candidate_scan_limit,
        candidate_scan_item_count=len(planned_items_tuple),
        candidate_resource_count=len(resources),
        known_skipped_item_count=sum(1 for item in planned_items_tuple if item.already_known),
        known_skipped_resource_count=sum(1 for resource in resources if resource.already_known),
        selected_new_item_count=selected_count,
        selected_new_resource_count=selected_resource_count,
        staged_pending_item_count=0,
        staged_pending_resource_count=0,
        unknown_identity_resource_count=0,
        ambiguous_item_count=0,
        remaining_unselected_new_item_count=unselected_new_count,
        candidate_source_exhausted=candidate_source_exhausted,
        items=planned_items_tuple,
    )


def build_new_count_plan_summary(
    plan: NewCountSelectionPlan,
    *,
    sample_limit: int = 50,
) -> dict[str, object]:
    """Return a bounded planner-only summary suitable for future reporting."""

    if sample_limit < 0:
        raise ValueError("sample_limit must not be negative.")
    selected_samples = [
        {
            "logical_item_key": item.logical_item_key,
            "grouping": item.grouping,
            "resource_paths": [
                resource.normalized_source_relative_path for resource in item.resources
            ],
            "selected_resource_paths": [
                resource.normalized_source_relative_path
                for resource in item.resources
                if resource.selected_for_download
            ],
        }
        for item in plan.items
        if item.selected_new
    ][:sample_limit]
    return {
        "mode": "new_count_planner_only",
        "planner_only": True,
        "classification": plan.classification,
        "stopping_reason": plan.stopping_reason,
        "blocking_reasons": list(plan.blocking_reasons),
        "guidance": plan.guidance,
        "target_new_item_count": plan.target_new_item_count,
        "candidate_scan_limit": plan.candidate_scan_limit,
        "candidate_scan_item_count": plan.candidate_scan_item_count,
        "candidate_resource_count": plan.candidate_resource_count,
        "known_skipped_item_count": plan.known_skipped_item_count,
        "known_skipped_resource_count": plan.known_skipped_resource_count,
        "selected_new_item_count": plan.selected_new_item_count,
        "selected_new_resource_count": plan.selected_new_resource_count,
        "staged_pending_item_count": plan.staged_pending_item_count,
        "staged_pending_resource_count": plan.staged_pending_resource_count,
        "unknown_identity_resource_count": plan.unknown_identity_resource_count,
        "ambiguous_item_count": plan.ambiguous_item_count,
        "remaining_unselected_new_item_count": plan.remaining_unselected_new_item_count,
        "candidate_source_exhausted": plan.candidate_source_exhausted,
        "selected_item_samples": selected_samples,
        "selected_item_samples_truncated": plan.selected_new_item_count > len(selected_samples),
    }
