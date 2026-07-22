"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import {
  advanceIcloudIntakeImport,
  dispatchRunIngestion,
  getIcloudIntakeImportStatus,
  getSourceProfileDeferredAssets,
  getSourceProfiles,
  refreshIcloudHistoricalInventory,
  resumeIcloudIntakeImport,
  startIcloudIntakeImport,
} from "@/lib/api";
import type {
  IcloudIntakeImportStatus,
  IcloudHistoricalRoutineRefreshResponse,
  SelectedSourceContext,
  SourceProfileDeferredAssetItem,
  SourceProfileSummary,
} from "@/types/ui-api";

import styles from "./icloud-run-workflow-panel.module.css";

type RunPhase = "idle" | "refreshing" | "running" | "failed";

const INVENTORY_REFRESH_CAP = 10000;

interface IcloudRunWorkflowPanelProps {
  selectedSourceId?: number | null;
  selectedSourceLabel?: string | null;
  selectedSourceContext?: SelectedSourceContext | null;
  onActionComplete?: () => void;
}

function isIcloudProfile(profile: SourceProfileSummary): boolean {
  return profile.source_type === "cloud_export" && profile.cloud_provider === "icloud";
}

function toDisplayDate(value: string | null): string {
  return value ? new Date(value).toLocaleString() : "Not yet";
}

function availabilityLabel(value: "yes" | "no" | "unknown" | null | undefined): string {
  if (value === "yes") {
    return "Yes";
  }
  if (value === "no") {
    return "No";
  }
  return "Unknown";
}

function resultTitle(result: IcloudIntakeImportStatus): string {
  if (result.import_status === "created") {
    return "iCloud Intake Ready";
  }
  if (result.import_status === "running") {
    return "iCloud Intake In Progress";
  }
  if (result.import_status === "stopped_needs_review") {
    return "Import stopped for review";
  }
  if (result.import_status === "failed") {
    return "iCloud import did not run";
  }
  if (result.import_status === "resume_available" || result.import_status === "paused_interrupted") {
    return "Import interrupted";
  }
  return "iCloud Intake Complete";
}

function Metric({ label, value }: { label: string; value: string | number | null | undefined }): JSX.Element {
  return (
    <div className={styles.metric}>
      <strong>{label}</strong>
      <span>{value ?? "-"}</span>
    </div>
  );
}

export default function IcloudRunWorkflowPanel({
  selectedSourceId: controlledSourceId = null,
  selectedSourceLabel = null,
  selectedSourceContext = null,
  onActionComplete,
}: IcloudRunWorkflowPanelProps = {}): JSX.Element {
  const [profiles, setProfiles] = useState<SourceProfileSummary[]>([]);
  const [internalSelectedSourceId, setInternalSelectedSourceId] = useState<number | null>(null);
  const [status, setStatus] = useState<IcloudIntakeImportStatus | null>(null);
  const [refreshResult, setRefreshResult] = useState<IcloudHistoricalRoutineRefreshResponse | null>(null);
  const [runResult, setRunResult] = useState<IcloudIntakeImportStatus | null>(null);
  const [deferredRows, setDeferredRows] = useState<SourceProfileDeferredAssetItem[]>([]);
  const [phase, setPhase] = useState<RunPhase>("idle");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoadingProfiles, setIsLoadingProfiles] = useState(false);
  const [isLoadingDeferred, setIsLoadingDeferred] = useState(false);

  const icloudProfiles = useMemo(() => profiles.filter(isIcloudProfile), [profiles]);
  const selectedSourceId = controlledSourceId ?? internalSelectedSourceId;
  const isControlledSource = controlledSourceId != null;
  const selectedProfile = useMemo(
    () => icloudProfiles.find((profile) => profile.source_id === selectedSourceId) ?? null,
    [icloudProfiles, selectedSourceId],
  );
  const selectedDisplayLabel = selectedProfile?.source_label ?? selectedSourceLabel ?? selectedSourceContext?.source_name ?? "Selected iCloud Source";
  const isBusy = phase === "refreshing" || phase === "running";
  const displayedResult = runResult ?? (status?.import_run_id ? status : null);
  const hasPreparedCandidates = Boolean(status && (status.can_start_import || status.can_resume_import || status.can_advance_import || status.logical_candidates_ready > 0));
  const canImportOrResume = Boolean(status && (status.can_start_import || status.can_resume_import || status.can_advance_import));
  const canResumePartialAcquisition = Boolean(
    status?.can_resume_import
      && status.import_stop_reason === "partial_item_failed"
      && status.local_staging_file_count > 0,
  );
  const unavailableReason = !selectedSourceId
    ? "Select an active iCloud Source Profile."
    : !hasPreparedCandidates && !status?.resume_available
      ? "Refresh / Prepare Next 1000 before importing."
      : status?.available_inventory === "no"
        ? "No eligible/acquirable iCloud inventory remains."
        : status && status.local_staging_file_count > 0 && !canResumePartialAcquisition
          ? "Local staging has files from a prior run; review cleanup before continuing."
          : null;
  const canRunBackfill = Boolean(
    selectedSourceId
      && !isBusy
      && canImportOrResume
      && (status?.local_staging_file_count === 0 || canResumePartialAcquisition),
  );

  const loadProfiles = useCallback(async () => {
    setIsLoadingProfiles(true);
    setError(null);
    try {
      const response = await getSourceProfiles({ status: "active", includeUsername: false });
      const nextProfiles = response.profiles.filter(isIcloudProfile);
      setProfiles(response.profiles);
      setInternalSelectedSourceId((current) => current ?? nextProfiles[0]?.source_id ?? null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load iCloud source profiles.");
    } finally {
      setIsLoadingProfiles(false);
    }
  }, []);

  const refreshStatus = useCallback(async (sourceId: number) => {
    const response = await getIcloudIntakeImportStatus(sourceId);
    setStatus(response.current);
  }, []);

  const loadDeferredRows = useCallback(async (sourceId: number) => {
    setIsLoadingDeferred(true);
    try {
      const response = await getSourceProfileDeferredAssets(sourceId, { state: "active_deferred", limit: 100 });
      setDeferredRows(response.items);
    } catch {
      setDeferredRows([]);
    } finally {
      setIsLoadingDeferred(false);
    }
  }, []);

  useEffect(() => {
    if (isControlledSource) {
      return;
    }
    void loadProfiles();
  }, [isControlledSource, loadProfiles]);

  useEffect(() => {
    if (!selectedSourceId) {
      return;
    }
    setRefreshResult(null);
    setRunResult(null);
    setMessage(null);
    setError(null);
    setDeferredRows([]);
    void refreshStatus(selectedSourceId);
    void loadDeferredRows(selectedSourceId);
  }, [loadDeferredRows, refreshStatus, selectedSourceId]);

  async function handleSelectedSourceDispatch(): Promise<void> {
    if (!selectedSourceId) {
      return;
    }
    setPhase("running");
    setError(null);
    setMessage(null);
    setRunResult(null);
    try {
      const response = await dispatchRunIngestion({
        source_profile_id: selectedSourceId,
        selection_fingerprint: selectedSourceContext?.selection_fingerprint ?? null,
        icloud_options: {
          target_logical_items: null,
        },
      });
      setMessage(response.next_action ? `${response.message} ${response.next_action}` : response.message);
      await refreshStatus(selectedSourceId);
      await loadDeferredRows(selectedSourceId);
      onActionComplete?.();
      setPhase("idle");
    } catch (err) {
      setPhase("failed");
      setError(err instanceof Error ? err.message : "iCloud action failed.");
    }
  }

  async function handleRefreshInventory(): Promise<void> {
    if (!selectedSourceId) {
      return;
    }
    setPhase("refreshing");
    setError(null);
    setMessage(null);
    setRunResult(null);
    try {
      const response = await refreshIcloudHistoricalInventory({
        source_id: selectedSourceId,
        max_candidates: INVENTORY_REFRESH_CAP,
      });
      setRefreshResult(response);
      setMessage(response.operator_message);
      await refreshStatus(selectedSourceId);
      await loadDeferredRows(selectedSourceId);
      setPhase("idle");
    } catch (err) {
      setPhase("failed");
      setError(err instanceof Error ? err.message : "Inventory refresh failed.");
    }
  }

  async function handleRunBackfill(): Promise<void> {
    if (!selectedSourceId || !canRunBackfill) {
      return;
    }
    setPhase("running");
    setError(null);
    setMessage(null);
    setRunResult(null);
    try {
      let current = status?.can_resume_import
        ? (await resumeIcloudIntakeImport({ source_id: selectedSourceId, import_run_id: status.import_run_id })).current
        : status?.can_advance_import
          ? status
          : (await startIcloudIntakeImport({
              source_id: selectedSourceId,
              internal_batch_size: 100,
            })).current;

      setStatus(current);
      setRunResult(current);
      setMessage(current.import_operator_message);

      let advances = 0;
      while (current.can_advance_import && advances < 100) {
        const response = await advanceIcloudIntakeImport({
          source_id: selectedSourceId,
          import_run_id: current.import_run_id,
        });
        current = response.current;
        setStatus(current);
        setRunResult(current);
        setMessage(current.import_operator_message);
        advances += 1;
      }
      await refreshStatus(selectedSourceId);
      await loadDeferredRows(selectedSourceId);
      setPhase("idle");
    } catch (err) {
      setPhase("failed");
      setError(err instanceof Error ? err.message : "iCloud import failed.");
    }
  }

  return (
    <section className={styles.panel} aria-label="iCloud intake routine">
      <div className={styles.header}>
        <div>
          <h3 className={styles.title}>iCloud Intake</h3>
          <p className={styles.subtitle}>Prepare and import eligible iCloud assets in guarded batches.</p>
        </div>
      </div>

      {isControlledSource ? (
        <div className={styles.controls}>
          <div className={styles.field}>
            Source Profile
            <strong>{selectedDisplayLabel}</strong>
          </div>
        </div>
      ) : (
        <div className={styles.controls}>
          <label className={styles.field}>
            Source Profile
            <select
              value={selectedSourceId ?? ""}
              disabled={isLoadingProfiles || isBusy}
              onChange={(event) => setInternalSelectedSourceId(event.target.value ? Number(event.target.value) : null)}
            >
              {icloudProfiles.length === 0 && <option value="">No active iCloud profiles</option>}
              {icloudProfiles.map((profile) => (
                <option key={profile.source_id} value={profile.source_id}>
                  {profile.source_label}
                </option>
              ))}
            </select>
          </label>
        </div>
      )}

      {status && (
        <div className={styles.metricsGrid}>
          <Metric label="Total Imported from Source" value={status.total_imported_from_source} />
          <Metric label="Last Inventory Refresh" value={toDisplayDate(status.last_inventory_refresh_at)} />
          <Metric label="Available Inventory" value={availabilityLabel(status.available_inventory)} />
          <Metric label="Logical Candidates Ready" value={status.logical_candidates_ready} />
        </div>
      )}

      <div className={styles.actionRow}>
        {isControlledSource ? (
          <button className={styles.primaryButton} type="button" disabled={!selectedSourceId || isBusy || status?.available_inventory === "no"} onClick={handleSelectedSourceDispatch}>
            {phase === "running" ? "Working..." : status?.can_resume_import ? "Resume Interrupted Import" : status?.can_advance_import ? "Continue Import" : status?.can_start_import ? "Import Next 1000" : "Prepare Next 1000"}
          </button>
        ) : (
          <>
            <button className={styles.secondaryButton} type="button" disabled={!selectedSourceId || isBusy} onClick={handleRefreshInventory}>
              {phase === "refreshing" ? "Preparing..." : "Refresh / Prepare Next 1000"}
            </button>
            <button className={styles.primaryButton} type="button" disabled={!canRunBackfill} onClick={handleRunBackfill}>
              {phase === "running" ? "Importing..." : status?.can_resume_import ? "Resume Interrupted Import" : "Import Next 1000"}
            </button>
          </>
        )}
        {unavailableReason && <span className={styles.metaLine}>{unavailableReason}</span>}
        {canResumePartialAcquisition && <span className={styles.metaLine}>Resume will first discard verified partial-acquisition staging files.</span>}
      </div>

      {message && <p className={styles.success}>{message}</p>}
      {error && <p className={styles.error}>{error}</p>}

      {displayedResult && (
        <div className={displayedResult.import_status === "stopped_needs_review" || displayedResult.import_status === "failed" || displayedResult.resume_available ? styles.warning : styles.summaryBlock}>
          <h4>{resultTitle(displayedResult)}</h4>
          <div className={styles.metricsGrid}>
            <Metric label="Logical Candidates" value={displayedResult.logical_candidates_total} />
            <Metric label="Logical Imported" value={displayedResult.logical_imported} />
            <Metric label="Files/Resources Imported" value={displayedResult.files_resources_imported} />
            <Metric label="Local Staging Files Cleaned" value={displayedResult.local_staging_files_cleaned} />
            <Metric label="New Deferred / Needs Policy" value={displayedResult.new_deferred_this_run} />
            <Metric label="Execution Failed / Retryable" value={displayedResult.execution_failed_retryable_count} />
          </div>
          <p className={styles.metaLine}>{displayedResult.import_operator_message}</p>
        </div>
      )}

      <details className={styles.details}>
        <summary>Details</summary>
        <div className={styles.metricsGrid}>
          <Metric label="Source ID" value={selectedSourceId} />
          <Metric label="Prepare Run" value={status?.latest_prepare_run_id} />
          <Metric label="Prepare Status" value={status?.prepare_status} />
          <Metric label="Prepare Expires" value={status?.prepare_expires_at ? toDisplayDate(status.prepare_expires_at) : "Not prepared"} />
          <Metric label="Import Run" value={status?.import_run_id} />
          <Metric label="Import Status" value={status?.import_status} />
          <Metric label="Chunks" value={status ? `${status.completed_chunk_count} / ${status.total_chunks}` : null} />
          <Metric label="Current Phase" value={status?.current_phase} />
          <Metric label="Remaining Logical" value={status?.remaining_logical_candidates} />
          <Metric label="Report Path" value={status?.report_path} />
          <Metric label="Staging Files" value={status?.local_staging_file_count} />
          <Metric label=".partial Files" value={status?.partial_file_count} />
          <Metric label="backfill_execute Files" value={status?.backfill_execute_file_count} />
        </div>
        {refreshResult && <p className={styles.metaLine}>{refreshResult.scan_limit_note}</p>}
        {displayedResult && (
          <div className={styles.tableWrap}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>Chunk</th>
                  <th>Imported</th>
                  <th>Resources</th>
                  <th>Cleaned</th>
                  <th>Timing</th>
                  <th>Run IDs</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {displayedResult.chunks.map((chunk) => (
                  <tr key={chunk.chunk_index}>
                    <td>{chunk.chunk_index}</td>
                    <td>{chunk.logical_imported}</td>
                    <td>{chunk.files_resources_imported}</td>
                    <td>{chunk.local_staging_files_cleaned}</td>
                    <td>{chunk.chunk_total_seconds != null ? `${chunk.chunk_total_seconds.toFixed(1)}s` : "-"}</td>
                    <td>
                      acquisition {chunk.acquisition_run_id ?? "-"} / batch {chunk.acquisition_batch_id ?? "-"} / intake {chunk.source_intake_run_id ?? "-"} / cleanup {chunk.cleanup_execution_run_id ?? "-"}
                    </td>
                    <td>{chunk.status}{chunk.stop_reason ? `: ${chunk.stop_reason}` : ""}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </details>

      <details className={styles.details}>
        <summary>Deferred / Needs Policy {isLoadingDeferred ? "" : `(${deferredRows.length})`}</summary>
        <div className={styles.tableWrap}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th>Path</th>
                <th>Category</th>
                <th>Reason</th>
                <th>State</th>
                <th>Resources</th>
                <th>Live Photo</th>
                <th>Seen</th>
              </tr>
            </thead>
            <tbody>
              {deferredRows.map((row) => (
                <tr key={row.id}>
                  <td>{row.primary_relative_path ?? row.filename ?? "-"}</td>
                  <td>{row.deferred_category}</td>
                  <td>{row.deferred_reason_code}</td>
                  <td>{row.current_state}</td>
                  <td>{row.resource_count}</td>
                  <td>{row.is_live_photo ? "Yes" : "No"}</td>
                  <td>{toDisplayDate(row.first_seen_at)} / {toDisplayDate(row.last_seen_at)} / {row.observation_count}</td>
                </tr>
              ))}
              {!isLoadingDeferred && deferredRows.length === 0 && (
                <tr>
                  <td colSpan={7}>No active deferred rows.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </details>
    </section>
  );
}
