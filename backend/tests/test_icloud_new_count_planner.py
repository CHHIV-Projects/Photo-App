from __future__ import annotations

import unittest

from app.services.icloud_acquisition.known_state_service import (
    KNOWN_STATE_STAGED,
    KNOWN_STATE_UNKNOWN,
    KNOWN_STATE_VAULT_VERIFIED,
    CandidateKnownState,
)
from app.services.icloud_acquisition.new_count_planner import (
    BLOCK_IDENTITY_UNAVAILABLE,
    BLOCK_LOGICAL_ITEM_IDENTITY_AMBIGUOUS,
    BLOCK_STAGED_UNKNOWN_PENDING_INTAKE,
    DEFAULT_CANDIDATE_SCAN_LIMIT,
    MAX_CANDIDATE_SCAN_LIMIT,
    MAX_TARGET_NEW_ITEM_COUNT,
    PLAN_CLASSIFICATION_BLOCKED,
    PLAN_CLASSIFICATION_COMPLETE,
    PLAN_CLASSIFICATION_PARTIAL,
    PLAN_CLASSIFICATION_TOOLING_LIMITED,
    STOP_NO_MORE_CANDIDATES,
    STOP_LOGICAL_ITEM_IDENTITY_AMBIGUOUS,
    STOP_SCAN_LIMIT_REACHED,
    STOP_STAGED_UNKNOWN_PENDING_INTAKE,
    STOP_TARGET_NEW_COUNT_REACHED,
    STOP_TOOLING_LIMIT_REACHED,
    ExplicitLogicalItemCandidate,
    ExplicitLogicalResourceCandidate,
    build_new_count_plan_summary,
    plan_explicit_new_count_selection,
    plan_new_count_selection,
)


def _candidate(
    relative_path: str | None,
    *,
    already_known: bool = False,
    staged_known: bool = False,
    unknown_identity: bool = False,
) -> CandidateKnownState:
    known_state = KNOWN_STATE_UNKNOWN
    if already_known:
        known_state = KNOWN_STATE_VAULT_VERIFIED
    elif staged_known:
        known_state = KNOWN_STATE_STAGED
    return CandidateKnownState(
        raw_line=relative_path or "unmapped candidate",
        normalized_source_relative_path=relative_path,
        unknown_identity=unknown_identity,
        staged_known=staged_known,
        ingested_known=already_known,
        vault_verified_known=already_known,
        already_known=already_known,
        known_state=known_state,
    )


def _selected_paths(plan) -> list[str | None]:
    return [
        resource.normalized_source_relative_path
        for item in plan.items
        for resource in item.resources
        if resource.selected_for_download
    ]


class IcloudNewCountPlannerTests(unittest.TestCase):
    def test_explicit_adapter_group_preserves_live_photo_relationship(self) -> None:
        plan = plan_explicit_new_count_selection(
            [
                ExplicitLogicalItemCandidate(
                    adapter_logical_item_id="remote-item-1",
                    grouping="live_photo_explicit",
                    identity_ambiguous=False,
                    resources=(
                        ExplicitLogicalResourceCandidate(
                            adapter_resource_id="primary_original",
                            known_state=_candidate(
                                "2026/06/24/IMG_2000.HEIC",
                                already_known=True,
                            ),
                        ),
                        ExplicitLogicalResourceCandidate(
                            adapter_resource_id="live_photo_original",
                            known_state=_candidate("2026/06/24/non_matching_name.MOV"),
                        ),
                    ),
                )
            ],
            target_new_item_count=1,
            candidate_scan_limit=1,
        )

        self.assertEqual(plan.classification, PLAN_CLASSIFICATION_COMPLETE)
        self.assertEqual(plan.selected_new_item_count, 1)
        self.assertEqual(plan.selected_new_resource_count, 1)
        self.assertEqual(plan.items[0].adapter_logical_item_id, "remote-item-1")
        self.assertEqual(plan.items[0].grouping, "live_photo_explicit")
        self.assertEqual(_selected_paths(plan), ["2026/06/24/non_matching_name.MOV"])
        self.assertEqual(
            plan.items[0].resources[1].adapter_resource_id,
            "live_photo_original",
        )

    def test_explicit_adapter_duplicate_item_identity_blocks(self) -> None:
        plan = plan_explicit_new_count_selection(
            [
                ExplicitLogicalItemCandidate(
                    adapter_logical_item_id="duplicate-id",
                    grouping="primary_asset_explicit",
                    identity_ambiguous=False,
                    resources=(
                        ExplicitLogicalResourceCandidate(
                            adapter_resource_id="primary_original",
                            known_state=_candidate("2026/06/24/IMG_2001.HEIC"),
                        ),
                    ),
                ),
                ExplicitLogicalItemCandidate(
                    adapter_logical_item_id="duplicate-id",
                    grouping="primary_asset_explicit",
                    identity_ambiguous=False,
                    resources=(
                        ExplicitLogicalResourceCandidate(
                            adapter_resource_id="primary_original",
                            known_state=_candidate("2026/06/23/IMG_2002.HEIC"),
                        ),
                    ),
                ),
            ],
            target_new_item_count=1,
            candidate_scan_limit=2,
        )

        self.assertEqual(plan.classification, PLAN_CLASSIFICATION_BLOCKED)
        self.assertEqual(plan.stopping_reason, STOP_LOGICAL_ITEM_IDENTITY_AMBIGUOUS)
        self.assertEqual(plan.ambiguous_item_count, 2)

    def test_explicit_adapter_unsupported_resource_relationship_blocks(self) -> None:
        plan = plan_explicit_new_count_selection(
            [
                ExplicitLogicalItemCandidate(
                    adapter_logical_item_id="remote-item-with-sidecar",
                    grouping="adapter_explicit_unsupported_sidecar",
                    identity_ambiguous=True,
                    resources=(
                        ExplicitLogicalResourceCandidate(
                            adapter_resource_id="primary_original",
                            known_state=_candidate("2026/06/24/IMG_2003.HEIC"),
                        ),
                    ),
                )
            ],
            target_new_item_count=1,
            candidate_scan_limit=1,
        )

        self.assertEqual(plan.classification, PLAN_CLASSIFICATION_BLOCKED)
        self.assertEqual(plan.stopping_reason, STOP_LOGICAL_ITEM_IDENTITY_AMBIGUOUS)
        self.assertEqual(plan.selected_new_item_count, 0)

    def test_explicit_adapter_can_skip_ambiguous_candidates_when_configured(self) -> None:
        plan = plan_explicit_new_count_selection(
            [
                ExplicitLogicalItemCandidate(
                    adapter_logical_item_id="ambiguous-item",
                    grouping="adapter_explicit_unsupported_sidecar",
                    identity_ambiguous=True,
                    resources=(
                        ExplicitLogicalResourceCandidate(
                            adapter_resource_id="primary_original",
                            known_state=_candidate("2026/06/24/IMG_3001.HEIC"),
                        ),
                    ),
                ),
                ExplicitLogicalItemCandidate(
                    adapter_logical_item_id="safe-item",
                    grouping="primary_asset_explicit",
                    identity_ambiguous=False,
                    resources=(
                        ExplicitLogicalResourceCandidate(
                            adapter_resource_id="primary_original",
                            known_state=_candidate("2026/06/24/IMG_3002.HEIC"),
                        ),
                    ),
                ),
            ],
            target_new_item_count=1,
            candidate_scan_limit=2,
            block_on_ambiguous_identity=False,
        )

        self.assertEqual(plan.classification, PLAN_CLASSIFICATION_COMPLETE)
        self.assertEqual(plan.stopping_reason, STOP_TARGET_NEW_COUNT_REACHED)
        self.assertEqual(plan.selected_new_item_count, 1)
        self.assertEqual(_selected_paths(plan), ["2026/06/24/IMG_3002.HEIC"])

    def test_mixed_window_selects_only_unknown_items_and_continues_past_known(self) -> None:
        plan = plan_new_count_selection(
            [
                _candidate("2026/06/24/KNOWN_1.HEIC", already_known=True),
                _candidate("2026/06/23/NEW_1.HEIC"),
                _candidate("2026/06/22/KNOWN_2.JPG", already_known=True),
                _candidate("2026/06/21/NEW_2.PNG"),
            ],
            target_new_item_count=2,
            candidate_scan_limit=4,
        )

        self.assertEqual(plan.classification, PLAN_CLASSIFICATION_COMPLETE)
        self.assertEqual(plan.stopping_reason, STOP_TARGET_NEW_COUNT_REACHED)
        self.assertEqual(plan.candidate_scan_item_count, 4)
        self.assertEqual(plan.known_skipped_item_count, 2)
        self.assertEqual(plan.known_skipped_resource_count, 2)
        self.assertEqual(plan.selected_new_item_count, 2)
        self.assertEqual(plan.selected_new_resource_count, 2)
        self.assertEqual(
            _selected_paths(plan),
            ["2026/06/23/NEW_1.HEIC", "2026/06/21/NEW_2.PNG"],
        )

    def test_live_photo_counts_as_one_item_and_selects_only_unknown_motion(self) -> None:
        plan = plan_new_count_selection(
            [
                _candidate("2026/06/24/IMG_1000.HEIC", already_known=True),
                _candidate("2026/06/24/IMG_1000_HEVC.MOV"),
            ],
            target_new_item_count=1,
            candidate_scan_limit=1,
        )

        self.assertEqual(plan.candidate_scan_item_count, 1)
        self.assertEqual(plan.candidate_resource_count, 2)
        self.assertEqual(plan.selected_new_item_count, 1)
        self.assertEqual(plan.selected_new_resource_count, 1)
        self.assertEqual(_selected_paths(plan), ["2026/06/24/IMG_1000_HEVC.MOV"])
        self.assertEqual(plan.items[0].grouping, "live_photo_motion_suffix")

    def test_unknown_sidecar_is_independent_from_known_sibling(self) -> None:
        plan = plan_new_count_selection(
            [
                _candidate("2026/06/24/IMG_1001.HEIC", already_known=True),
                _candidate("2026/06/24/IMG_1001.AAE"),
            ],
            target_new_item_count=1,
            candidate_scan_limit=2,
        )

        self.assertEqual(plan.candidate_scan_item_count, 2)
        self.assertEqual(plan.known_skipped_item_count, 1)
        self.assertEqual(plan.selected_new_item_count, 1)
        self.assertEqual(_selected_paths(plan), ["2026/06/24/IMG_1001.AAE"])

    def test_multiple_stills_make_motion_companion_grouping_ambiguous(self) -> None:
        plan = plan_new_count_selection(
            [
                _candidate("2026/06/24/IMG_1001.HEIC"),
                _candidate("2026/06/24/IMG_1001.JPG"),
                _candidate("2026/06/24/IMG_1001.MOV"),
            ],
            target_new_item_count=1,
            candidate_scan_limit=3,
        )

        self.assertEqual(plan.classification, PLAN_CLASSIFICATION_BLOCKED)
        self.assertEqual(plan.stopping_reason, STOP_LOGICAL_ITEM_IDENTITY_AMBIGUOUS)
        self.assertEqual(
            plan.blocking_reasons,
            (BLOCK_LOGICAL_ITEM_IDENTITY_AMBIGUOUS,),
        )
        self.assertEqual(plan.ambiguous_item_count, 1)
        self.assertEqual(plan.selected_new_item_count, 0)

    def test_staged_unknown_blocks_with_source_intake_guidance(self) -> None:
        plan = plan_new_count_selection(
            [_candidate("2026/06/24/IMG_1002.HEIC", staged_known=True)],
            target_new_item_count=1,
            candidate_scan_limit=1,
        )

        self.assertEqual(plan.classification, PLAN_CLASSIFICATION_BLOCKED)
        self.assertEqual(plan.stopping_reason, STOP_STAGED_UNKNOWN_PENDING_INTAKE)
        self.assertEqual(plan.blocking_reasons, (BLOCK_STAGED_UNKNOWN_PENDING_INTAKE,))
        self.assertEqual(plan.staged_pending_item_count, 1)
        self.assertEqual(plan.staged_pending_resource_count, 1)
        self.assertEqual(plan.selected_new_item_count, 0)
        self.assertEqual(plan.guidance, "Run Source Intake first for staged unknown resources.")

    def test_unknown_identity_blocks_instead_of_suppressing_candidate(self) -> None:
        plan = plan_new_count_selection(
            [_candidate(None, unknown_identity=True)],
            target_new_item_count=1,
            candidate_scan_limit=1,
        )

        self.assertEqual(plan.classification, PLAN_CLASSIFICATION_BLOCKED)
        self.assertEqual(plan.blocking_reasons, (BLOCK_IDENTITY_UNAVAILABLE,))
        self.assertEqual(plan.unknown_identity_resource_count, 1)
        self.assertEqual(plan.selected_new_item_count, 0)

    def test_all_known_and_source_exhausted_downloads_zero(self) -> None:
        plan = plan_new_count_selection(
            [
                _candidate("2026/06/24/KNOWN_1.HEIC", already_known=True),
                _candidate("2026/06/23/KNOWN_2.HEIC", already_known=True),
            ],
            target_new_item_count=3,
            candidate_scan_limit=3,
            candidate_source_exhausted=True,
        )

        self.assertEqual(plan.classification, PLAN_CLASSIFICATION_PARTIAL)
        self.assertEqual(plan.stopping_reason, STOP_NO_MORE_CANDIDATES)
        self.assertEqual(plan.selected_new_item_count, 0)
        self.assertEqual(plan.known_skipped_item_count, 2)

    def test_scan_limit_and_tooling_limit_are_distinct(self) -> None:
        scan_limited = plan_new_count_selection(
            [
                _candidate("2026/06/24/KNOWN_1.HEIC", already_known=True),
                _candidate("2026/06/23/KNOWN_2.HEIC", already_known=True),
            ],
            target_new_item_count=1,
            candidate_scan_limit=2,
        )
        tooling_limited = plan_new_count_selection(
            [_candidate("2026/06/24/KNOWN_1.HEIC", already_known=True)],
            target_new_item_count=1,
            candidate_scan_limit=5,
        )

        self.assertEqual(scan_limited.classification, PLAN_CLASSIFICATION_PARTIAL)
        self.assertEqual(scan_limited.stopping_reason, STOP_SCAN_LIMIT_REACHED)
        self.assertEqual(tooling_limited.classification, PLAN_CLASSIFICATION_TOOLING_LIMITED)
        self.assertEqual(tooling_limited.stopping_reason, STOP_TOOLING_LIMIT_REACHED)

    def test_scan_limit_wins_when_exhaustive_input_exceeds_backend_limit(self) -> None:
        plan = plan_new_count_selection(
            [
                _candidate("2026/06/24/KNOWN_1.HEIC", already_known=True),
                _candidate("2026/06/23/KNOWN_2.HEIC", already_known=True),
            ],
            target_new_item_count=1,
            candidate_scan_limit=1,
            candidate_source_exhausted=True,
        )

        self.assertEqual(plan.classification, PLAN_CLASSIFICATION_PARTIAL)
        self.assertEqual(plan.stopping_reason, STOP_SCAN_LIMIT_REACHED)

    def test_bounded_summary_is_explicitly_planner_only(self) -> None:
        plan = plan_new_count_selection(
            [
                _candidate("2026/06/24/NEW_1.HEIC"),
                _candidate("2026/06/23/NEW_2.HEIC"),
            ],
            target_new_item_count=2,
            candidate_scan_limit=2,
        )

        summary = build_new_count_plan_summary(plan, sample_limit=1)

        self.assertEqual(summary["mode"], "new_count_planner_only")
        self.assertTrue(summary["planner_only"])
        self.assertEqual(summary["target_new_item_count"], 2)
        self.assertEqual(summary["candidate_scan_item_count"], 2)
        self.assertEqual(summary["selected_new_item_count"], 2)
        self.assertEqual(summary["selected_new_resource_count"], 2)
        self.assertEqual(summary["stopping_reason"], STOP_TARGET_NEW_COUNT_REACHED)
        self.assertEqual(len(summary["selected_item_samples"]), 1)
        self.assertTrue(summary["selected_item_samples_truncated"])

    def test_invalid_target_and_scan_limits_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            plan_new_count_selection([], target_new_item_count=0)
        with self.assertRaises(ValueError):
            plan_new_count_selection([], target_new_item_count=2, candidate_scan_limit=1)

    def test_planner_limits_align_with_recent_sync_1000_cap(self) -> None:
        self.assertEqual(DEFAULT_CANDIDATE_SCAN_LIMIT, 1000)
        self.assertEqual(MAX_CANDIDATE_SCAN_LIMIT, 1000)
        self.assertEqual(MAX_TARGET_NEW_ITEM_COUNT, 1000)

    def test_grouped_planner_accepts_target_and_scan_limit_1000(self) -> None:
        plan = plan_new_count_selection(
            [_candidate(f"2026/06/24/IMG_{index:04d}.HEIC") for index in range(1000)],
            target_new_item_count=1000,
            candidate_scan_limit=1000,
        )

        self.assertEqual(plan.classification, PLAN_CLASSIFICATION_COMPLETE)
        self.assertEqual(plan.target_new_item_count, 1000)
        self.assertEqual(plan.candidate_scan_limit, 1000)
        self.assertEqual(plan.candidate_scan_item_count, 1000)
        self.assertEqual(plan.selected_new_item_count, 1000)

    def test_explicit_adapter_planner_accepts_target_and_scan_limit_1000(self) -> None:
        plan = plan_explicit_new_count_selection(
            [
                ExplicitLogicalItemCandidate(
                    adapter_logical_item_id=f"remote-item-{index:04d}",
                    grouping="primary_asset_explicit",
                    identity_ambiguous=False,
                    resources=(
                        ExplicitLogicalResourceCandidate(
                            adapter_resource_id="primary_original",
                            known_state=_candidate(f"2026/06/24/IMG_{index:04d}.HEIC"),
                        ),
                    ),
                )
                for index in range(1000)
            ],
            target_new_item_count=1000,
            candidate_scan_limit=1000,
        )

        self.assertEqual(plan.classification, PLAN_CLASSIFICATION_COMPLETE)
        self.assertEqual(plan.target_new_item_count, 1000)
        self.assertEqual(plan.candidate_scan_limit, 1000)
        self.assertEqual(plan.candidate_scan_item_count, 1000)
        self.assertEqual(plan.selected_new_item_count, 1000)

    def test_planner_rejects_limits_above_1000(self) -> None:
        with self.assertRaises(ValueError):
            plan_new_count_selection([], target_new_item_count=1001, candidate_scan_limit=1001)
        with self.assertRaises(ValueError):
            plan_new_count_selection([], target_new_item_count=1, candidate_scan_limit=1001)


if __name__ == "__main__":
    unittest.main()
