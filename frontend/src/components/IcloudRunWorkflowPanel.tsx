"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import {
  getIcloudHistoricalRoutineStatus,
  getSourceProfileDeferredAssets,
  getSourceProfiles,
  refreshIcloudHistoricalInventory,
  runIcloudHistoricalNextBatch,
} from "@/lib/api";
import type {
  IcloudHistoricalRoutineRefreshResponse,
  IcloudHistoricalRoutineRunResponse,
  IcloudHistoricalRoutineStatus,
  SourceProfileDeferredAssetItem,
  SourceProfileSummary,
} from "@/types/ui-api";

import styles from "./icloud-run-workflow-panel.module.css";

type RunPhase = "idle" | "refreshing" | "running" | "failed";

const INVENTORY_REFRESH_CAP = 10000;

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

function resultTitle(result: IcloudHistoricalRoutineRunResponse): string {
  if (result.status === "stopped_needs_review") {
    return "Import stopped for review";
  }
  if (result.status === "failed") {
    return "iCloud import did not run";
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

export default function IcloudRunWorkflowPanel(): JSX.Element {
  const [profiles, setProfiles] = useState<SourceProfileSummary[]>([]);
  const [selectedSourceId, setSelectedSourceId] = useState<number | null>(null);
  const [status, setStatus] = useState<IcloudHistoricalRoutineStatus | null>(null);
  const [refreshResult, setRefreshResult] = useState<IcloudHistoricalRoutineRefreshResponse | null>(null);
  const [runResult, setRunResult] = useState<IcloudHistoricalRoutineRunResponse | null>(null);
  const [deferredRows, setDeferredRows] = useState<SourceProfileDeferredAssetItem[]>([]);
  const [phase, setPhase] = useState<RunPhase>("idle");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoadingProfiles, setIsLoadingProfiles] = useState(false);
  const [isLoadingDeferred, setIsLoadingDeferred] = useState(false);

  const icloudProfiles = useMemo(() => profiles.filter(isIcloudProfile), [profiles]);
  const selectedProfile = useMemo(
    () => icloudProfiles.find((profile) => profile.source_id === selectedSourceId) ?? null,
    [icloudProfiles, selectedSourceId],
  );
  const isBusy = phase === "refreshing" || phase === "running";
  const hasPreparedCandidates = Boolean(status && status.logical_candidates_ready > 0 && status.prepare_status === "prepared");
  const unavailableReason = !selectedProfile
    ? "Select an active iCloud Source Profile."
    : !hasPreparedCandidates
      ? "Refresh / Prepare Next 1000 before importing."
      : status?.available_inventory === "no"
        ? "No eligible/acquirable iCloud inventory remains."
        : status && status.local_staging_file_count > 0
          ? "Local staging has files from a prior run; review cleanup before continuing."
          : null;
  const canRunBackfill = Boolean(
    selectedSourceId
      && !isBusy
      && hasPreparedCandidates
      && status?.available_inventory === "yes"
      && status.local_staging_file_count === 0,
  );

  const loadProfiles = useCallback(async () => {
    setIsLoadingProfiles(true);
    setError(null);
    try {
      const response = await getSourceProfiles({ status: "active", includeUsername: false });
      const nextProfiles = response.profiles.filter(isIcloudProfile);
      setProfiles(response.profiles);
      setSelectedSourceId((current) => current ?? nextProfiles[0]?.source_id ?? null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load iCloud source profiles.");
    } finally {
      setIsLoadingProfiles(false);
    }
  }, []);

  const refreshStatus = useCallback(async (sourceId: number) => {
    const response = await getIcloudHistoricalRoutineStatus(sourceId);
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
    void loadProfiles();
  }, [loadProfiles]);

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
      const response = await runIcloudHistoricalNextBatch({
        source_id: selectedSourceId,
        internal_batch_size: 100,
      });
      setRunResult(response);
      setMessage(response.operator_message);
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

      <div className={styles.controls}>
        <label className={styles.field}>
          Source Profile
          <select
            value={selectedSourceId ?? ""}
            disabled={isLoadingProfiles || isBusy}
            onChange={(event) => setSelectedSourceId(event.target.value ? Number(event.target.value) : null)}
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

      {status && (
        <div className={styles.metricsGrid}>
          <Metric label="Total Imported from Source" value={status.total_imported_from_source} />
          <Metric label="Last Inventory Refresh" value={toDisplayDate(status.last_inventory_refresh_at)} />
          <Metric label="Available Inventory" value={availabilityLabel(status.available_inventory)} />
          <Metric label="Logical Candidates Ready" value={status.logical_candidates_ready} />
        </div>
      )}

      <div className={styles.actionRow}>
        <button className={styles.secondaryButton} type="button" disabled={!selectedSourceId || isBusy} onClick={handleRefreshInventory}>
          {phase === "refreshing" ? "Preparing..." : "Refresh / Prepare Next 1000"}
        </button>
        <button className={styles.primaryButton} type="button" disabled={!canRunBackfill} onClick={handleRunBackfill}>
          {phase === "running" ? "Importing..." : "Import Next 1000"}
        </button>
        {unavailableReason && <span className={styles.metaLine}>{unavailableReason}</span>}
      </div>

      {message && <p className={styles.success}>{message}</p>}
      {error && <p className={styles.error}>{error}</p>}

      {runResult && (
        <div className={runResult.status === "stopped_needs_review" || runResult.status === "failed" ? styles.warning : styles.summaryBlock}>
          <h4>{resultTitle(runResult)}</h4>
          <div className={styles.metricsGrid}>
            <Metric label="Logical Candidates" value={runResult.logical_candidates} />
            <Metric label="Logical Imported" value={runResult.logical_imported} />
            <Metric label="Files/Resources Imported" value={runResult.files_resources_imported} />
            <Metric label="Local Staging Files Cleaned" value={runResult.local_staging_files_cleaned} />
            <Metric label="New Deferred / Needs Policy" value={runResult.new_deferred_this_run} />
            <Metric label="Execution Failed / Retryable" value={runResult.execution_failed_this_run} />
          </div>
          <p className={styles.metaLine}>{runResult.operator_message}</p>
        </div>
      )}

      <details className={styles.details}>
        <summary>Details</summary>
        <div className={styles.metricsGrid}>
          <Metric label="Source ID" value={selectedSourceId} />
          <Metric label="Prepare Run" value={status?.latest_prepare_run_id} />
          <Metric label="Prepare Status" value={status?.prepare_status} />
          <Metric label="Prepare Expires" value={status?.prepare_expires_at ? toDisplayDate(status.prepare_expires_at) : "Not prepared"} />
          <Metric label="Known Inventory" value={status ? `${status.inventory_total_logical} logical assets` : null} />
          <Metric label="Imported / Accounted" value={status?.backfill_completed_logical} />
          <Metric label="Eligible Remaining" value={status?.eligible_pending_logical} />
          <Metric label="Total Deferred" value={status?.deferred_current_logical} />
          <Metric label="New Deferred This Prepare" value={status?.new_deferred_this_prepare} />
          <Metric label="Source Exhaustion" value={status?.source_exhaustion_state} />
          <Metric label="Provider Records Scanned" value={status?.provider_records_scanned} />
          <Metric label="Scan Depth Used" value={status?.scan_depth_used} />
          <Metric label="Last Import Run" value={status?.last_historical_run_id} />
          <Metric label="Last Cleanup Run" value={status?.last_cleanup_run_id} />
          <Metric label="Staging Files" value={status?.local_staging_file_count} />
          <Metric label=".partial Files" value={status?.partial_file_count} />
          <Metric label="backfill_execute Files" value={status?.backfill_execute_file_count} />
        </div>
        {refreshResult && <p className={styles.metaLine}>{refreshResult.scan_limit_note}</p>}
        {runResult && (
          <div className={styles.tableWrap}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>Chunk</th>
                  <th>Imported</th>
                  <th>Resources</th>
                  <th>Cleaned</th>
                  <th>Run IDs</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {runResult.chunks.map((chunk) => (
                  <tr key={chunk.chunk_index}>
                    <td>{chunk.chunk_index}</td>
                    <td>{chunk.imported_logical_assets}</td>
                    <td>{chunk.imported_resources}</td>
                    <td>{chunk.cleaned_local_staging_files}</td>
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
