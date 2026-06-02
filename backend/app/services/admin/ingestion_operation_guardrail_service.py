from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.icloud_acquisition_run import IcloudAcquisitionRun
from app.models.icloud_staging_cleanup_run import IcloudStagingCleanupRun
from app.models.source_intake_run import SourceIntakeRun
from app.schemas.admin import IcloudReadinessOperationConflicts, IcloudReadinessReason
from app.services.admin.icloud_staging_cleanup_execution_service import RUNNING_STATUSES as CLEANUP_RUNNING_STATUSES
from app.services.admin.source_intake_execution_service import RUNNING_STATUSES as SOURCE_INTAKE_RUNNING_STATUSES
from app.services.icloud_acquisition.execution_service import RUNNING_STATUSES as ACQUISITION_RUNNING_STATUSES


@dataclass(frozen=True)
class IngestionOperationGuardrailSnapshot:
    operation_conflicts: IcloudReadinessOperationConflicts
    active_operation: str | None
    active_source_id: int | None
    blocking_reasons: list[IcloudReadinessReason]

    @property
    def blocked(self) -> bool:
        return bool(self.blocking_reasons)


def _latest_active_acquisition(db_session: Session) -> IcloudAcquisitionRun | None:
    return db_session.scalar(
        select(IcloudAcquisitionRun)
        .where(IcloudAcquisitionRun.status.in_(ACQUISITION_RUNNING_STATUSES))
        .order_by(IcloudAcquisitionRun.id.desc())
        .limit(1)
    )


def _latest_active_source_intake(db_session: Session) -> SourceIntakeRun | None:
    return db_session.scalar(
        select(SourceIntakeRun)
        .where(SourceIntakeRun.status.in_(SOURCE_INTAKE_RUNNING_STATUSES))
        .order_by(SourceIntakeRun.id.desc())
        .limit(1)
    )


def _latest_active_cleanup(db_session: Session) -> IcloudStagingCleanupRun | None:
    return db_session.scalar(
        select(IcloudStagingCleanupRun)
        .where(IcloudStagingCleanupRun.status.in_(tuple(CLEANUP_RUNNING_STATUSES)))
        .order_by(IcloudStagingCleanupRun.id.desc())
        .limit(1)
    )


def _for_source_status(*, source_id: int | None, active_source_id: int | None) -> bool | None:
    if source_id is None:
        return None
    if active_source_id is None:
        return None
    return active_source_id == source_id


def get_ingestion_operation_guardrail_snapshot(
    db_session: Session,
    *,
    source_id: int | None = None,
) -> IngestionOperationGuardrailSnapshot:
    """Return active ingestion-operation conflicts and machine-readable reasons."""
    active_acquisition = _latest_active_acquisition(db_session)
    active_source_intake = _latest_active_source_intake(db_session)
    active_cleanup = _latest_active_cleanup(db_session)

    operation_conflicts = IcloudReadinessOperationConflicts(
        icloud_acquisition_active=active_acquisition is not None,
        source_intake_active=active_source_intake is not None,
        icloud_cleanup_active=active_cleanup is not None,
        source_intake_active_for_this_source=_for_source_status(
            source_id=source_id,
            active_source_id=(None if active_source_intake is None else active_source_intake.ingestion_source_id),
        ),
        icloud_cleanup_active_for_this_source=_for_source_status(
            source_id=source_id,
            active_source_id=(None if active_cleanup is None else active_cleanup.ingestion_source_id),
        ),
    )

    blocking_reasons: list[IcloudReadinessReason] = []
    if operation_conflicts.icloud_acquisition_active:
        blocking_reasons.append(
            IcloudReadinessReason(
                code="ICLOUD_ACQUISITION_ACTIVE",
                message="Another iCloud acquisition run is currently active.",
            )
        )
    if operation_conflicts.source_intake_active:
        blocking_reasons.append(
            IcloudReadinessReason(
                code="SOURCE_INTAKE_ACTIVE",
                message="A Source Intake run is currently active.",
            )
        )
    if operation_conflicts.icloud_cleanup_active:
        blocking_reasons.append(
            IcloudReadinessReason(
                code="ICLOUD_CLEANUP_ACTIVE",
                message="An iCloud staging cleanup run is currently active.",
            )
        )

    active_operation: str | None = None
    active_source_id: int | None = None
    if active_acquisition is not None:
        active_operation = "icloud_acquisition"
    elif active_source_intake is not None:
        active_operation = "source_intake"
        active_source_id = active_source_intake.ingestion_source_id
    elif active_cleanup is not None:
        active_operation = "icloud_cleanup"
        active_source_id = active_cleanup.ingestion_source_id

    return IngestionOperationGuardrailSnapshot(
        operation_conflicts=operation_conflicts,
        active_operation=active_operation,
        active_source_id=active_source_id,
        blocking_reasons=blocking_reasons,
    )
