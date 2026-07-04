"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import {
  executeIcloudStagingCleanup,
  getIcloudBackfillStatus,
  getIcloudStagingCleanupStatus,
  getSourceProfileDeferredAssets,
  getSourceProfiles,
  previewIcloudBackfillAcquisition,
  runIcloudBackfillAcquisition,
  runIcloudBackfillInventoryScan,
  runIcloudStagingCleanupDryRun,
} from "@/lib/api";
import type {
  IcloudBackfillAcquirePreviewResponse,
  IcloudBackfillAcquireResponse,
  IcloudBackfillInventoryStatus,
  IcloudStagingCleanupRunStatus,
  SourceProfileDeferredAssetItem,
  SourceProfileSummary,
} from "@/types/ui-api";

import styles from "./icloud-run-workflow-panel.module.css";

type WorkflowMode = "new_import" | "historical_backfill";
type RunPhase = "idle" | "previewing" | "acquiring" | "cleanup_dry_run" | "cleanup_execute" | "completed" | "needs_review" | "failed";
type CleanupSafetyReview = {
  safe: boolean;
  reason: string;
  eligibleCount: number;
  verificationFailures: number;
  unexpectedFiles: number;
};

const DEFAULT_NEW_IMPORT_LIMIT = "100";
const DEFAULT_HISTORICAL_LIMIT = "500";
const CANDIDATE_SEARCH_CAP = 1000;
const HARD_ACQUIRE_LIMIT = 10000;
const CLEANUP_CONFIRMATION_PHRASE = "DELETE LOCAL STAGING COPIES";
const CLEANUP_ACTIVE_STATUSES = new Set(["pending", "running", "stop_requested"]);
const CLEANUP_POLL_MS = 1200;

function isIcloudProfile(profile: SourceProfileSummary): boolean {
  return profile.source_type === "cloud_export" && profile.cloud_provider === "icloud";
}

function normalizeRelativePath(value: string | null | undefined): string | null {
  const normalized = (value ?? "").replaceAll("\\", "/").replace(/^\/+/, "").trim();
  return normalized || null;
}

function toDisplayDate(value: string | null): string {
  return value ? new Date(value).toLocaleString() : "-";
}

function parsePositiveInteger(value: string): number | null {
  if (!/^\d+$/.test(value.trim())) {
    return null;
  }
  const parsed = Number(value);
  return Number.isSafeInteger(parsed) && parsed > 0 ? parsed : null;
}

function sortedUnique(values: Array<string | null>): string[] {
  return Array.from(new Set(values.filter((value): value is string => Boolean(value)))).sort();
}

function arraysEqual(left: string[], right: string[]): boolean {
  if (left.length !== right.length) {
    return false;
  }
  return left.every((value, index) => value === right[index]);
}

function reviewCleanupSafety(
  cleanup: IcloudStagingCleanupRunStatus,
  acquiredRelativePaths: string[],
  selectedSourceId: number,
): CleanupSafetyReview {
  const base = {
    eligibleCount: cleanup.eligible_count,
    verificationFailures: cleanup.verification_failed_count,
    unexpectedFiles: 0,
  };
  if (cleanup.source_id !== selectedSourceId) {
    return { ...base, safe: false, reason: "Cleanup dry run source does not match the selected source." };
  }
  if (
    cleanup.skipped_count !== 0 ||
    cleanup.protected_count !== 0 ||
    cleanup.verification_failed_count !== 0 ||
    cleanup.file_missing_count !== 0 ||
    cleanup.delete_failed_count !== 0
  ) {
    return { ...base, safe: false, reason: "Cleanup dry run has non-zero safety counters." };
  }

  const cleanupPaths = sortedUnique(cleanup.eligible_files.map((file) => normalizeRelativePath(file.relative_path)));
  const acquiredPaths = sortedUnique(acquiredRelativePaths.map((path) => normalizeRelativePath(path)));
  const cleanupSet = new Set(cleanupPaths);
  const acquiredSet = new Set(acquiredPaths);
  const unexpectedFiles = cleanupPaths.filter((path) => !acquiredSet.has(path)).length;
  const missingFiles = acquiredPaths.filter((path) => !cleanupSet.has(path)).length;
  if (cleanupPaths.length === 0) {
    return { ...base, unexpectedFiles, safe: false, reason: "Cleanup dry run has no eligible files." };
  }
  if (acquiredPaths.length === 0) {
    return { ...base, unexpectedFiles, safe: false, reason: "Acquisition response did not include acquired resource paths." };
  }
  if (!arraysEqual(cleanupPaths, acquiredPaths)) {
    return {
      ...base,
      unexpectedFiles,
      safe: false,
      reason: `Cleanup candidates do not exactly match imported resources (${unexpectedFiles} unexpected, ${missingFiles} missing).`,
    };
  }
  if (cleanupPaths.some((path) => path.toLowerCase().includes(".partial") || path.toLowerCase().includes("backfill_execute"))) {
    return { ...base, unexpectedFiles, safe: false, reason: "Cleanup candidates include protected partial or execution workspace files." };
  }
  return { ...base, unexpectedFiles: 0, safe: true, reason: "Cleanup candidates exactly match imported resources." };
}

async function pollCleanupStatus(sourceId: number): Promise<IcloudStagingCleanupRunStatus> {
  let latest = (await getIcloudStagingCleanupStatus(sourceId)).current;
  for (let attempt = 0; attempt < 90 && CLEANUP_ACTIVE_STATUSES.has(latest.status); attempt += 1) {
    await new Promise((resolve) => window.setTimeout(resolve, CLEANUP_POLL_MS));
    latest = (await getIcloudStagingCleanupStatus(sourceId)).current;
  }
  return latest;
}

export default function IcloudRunWorkflowPanel(): JSX.Element {
  const [profiles, setProfiles] = useState<SourceProfileSummary[]>([]);
  const [selectedSourceId, setSelectedSourceId] = useState<number | null>(null);
  const [mode, setMode] = useState<WorkflowMode>("historical_backfill");
  const [limitValue, setLimitValue] = useState(DEFAULT_HISTORICAL_LIMIT);
  const [status, setStatus] = useState<IcloudBackfillInventoryStatus | null>(null);
  const [preview, setPreview] = useState<IcloudBackfillAcquirePreviewResponse | null>(null);
  const [previewKey, setPreviewKey] = useState<string | null>(null);
  const [acquireResult, setAcquireResult] = useState<IcloudBackfillAcquireResponse | null>(null);
  const [cleanupResult, setCleanupResult] = useState<IcloudStagingCleanupRunStatus | null>(null);
  const [lastAcquiredResourcePaths, setLastAcquiredResourcePaths] = useState<string[]>([]);
  const [cleanupReview, setCleanupReview] = useState<CleanupSafetyReview | null>(null);
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
  const acquireLimit = parsePositiveInteger(limitValue);
  const currentKey = selectedSourceId != null && acquireLimit != null
    ? `${selectedSourceId}:${acquireLimit}:${CANDIDATE_SEARCH_CAP}:${mode}`
    : null;
  const isBusy = phase === "previewing" || phase === "acquiring" || phase === "cleanup_dry_run" || phase === "cleanup_execute";
  const largeLimitWarning = acquireLimit && acquireLimit > CANDIDATE_SEARCH_CAP
    ? `Partial completion is possible: requested ${acquireLimit}, candidate search cap ${CANDIDATE_SEARCH_CAP}.`
    : null;

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
    const response = await getIcloudBackfillStatus(sourceId);
    setStatus(response.current);
  }, []);

  useEffect(() => {
    void loadProfiles();
  }, [loadProfiles]);

  useEffect(() => {
    if (!selectedSourceId) {
      return;
    }
    setPreview(null);
    setPreviewKey(null);
    setAcquireResult(null);
    setCleanupResult(null);
    setLastAcquiredResourcePaths([]);
    setCleanupReview(null);
    setDeferredRows([]);
    setMessage(null);
    setError(null);
    void refreshStatus(selectedSourceId);
  }, [refreshStatus, selectedSourceId]);

  function handleModeChange(nextMode: WorkflowMode): void {
    setMode(nextMode);
    setLimitValue(nextMode === "new_import" ? DEFAULT_NEW_IMPORT_LIMIT : DEFAULT_HISTORICAL_LIMIT);
    setPreview(null);
    setPreviewKey(null);
  }

  async function handleInventoryScan(): Promise<void> {
    if (!selectedSourceId) {
      return;
    }
    setPhase("previewing");
    setError(null);
    setMessage(null);
    try {
      const response = await runIcloudBackfillInventoryScan({
        source_id: selectedSourceId,
        max_candidates: CANDIDATE_SEARCH_CAP,
      });
      setStatus(response.current);
      setMessage(response.message);
      setPhase("idle");
    } catch (err) {
      setPhase("failed");
      setError(err instanceof Error ? err.message : "Inventory scan failed.");
    }
  }

  async function runPreview(): Promise<IcloudBackfillAcquirePreviewResponse | null> {
    if (!selectedSourceId || !acquireLimit || !currentKey) {
      setError("Enter a positive integer limit.");
      return null;
    }
    if (acquireLimit > HARD_ACQUIRE_LIMIT) {
      setError(`Limit must be ${HARD_ACQUIRE_LIMIT} or lower.`);
      return null;
    }
    setPhase("previewing");
    setError(null);
    setMessage(null);
    try {
      const response = await previewIcloudBackfillAcquisition({
        source_id: selectedSourceId,
        acquire_limit: acquireLimit,
        max_listing_candidates: CANDIDATE_SEARCH_CAP,
        include_items: true,
      });
      setPreview(response);
      setPreviewKey(currentKey);
      setPhase("idle");
      return response;
    } catch (err) {
      setPhase("failed");
      setError(err instanceof Error ? err.message : "Preview failed.");
      return null;
    }
  }

  async function handlePreview(): Promise<void> {
    await runPreview();
  }

  async function handleRun(): Promise<void> {
    if (mode !== "historical_backfill") {
      setError("New Import is coming soon.");
      return;
    }
    if (!selectedSourceId || !acquireLimit || !currentKey) {
      setError("Enter a positive integer limit.");
      return;
    }
    if (acquireLimit > HARD_ACQUIRE_LIMIT) {
      setError(`Limit must be ${HARD_ACQUIRE_LIMIT} or lower.`);
      return;
    }

    setError(null);
    setMessage(null);
    setCleanupResult(null);

    const safePreview = preview && previewKey === currentKey ? preview : await runPreview();
    if (!safePreview) {
      return;
    }
    if (safePreview.unsafe_manifest_count > 0) {
      setPhase("failed");
      setError("Preview found unsafe manifest rows.");
      return;
    }
    if (safePreview.preview_selected_logical_count === 0) {
      setPhase("completed");
      setMessage("No eligible pending iCloud assets were selected.");
      return;
    }

    try {
      setPhase("acquiring");
      const acquisition = await runIcloudBackfillAcquisition({
        source_id: selectedSourceId,
        acquire_limit: acquireLimit,
        max_listing_candidates: CANDIDATE_SEARCH_CAP,
        dry_run: false,
        auto_run_source_intake: true,
        include_items: true,
      });
      setAcquireResult(acquisition);
      const acquiredPaths = sortedUnique(acquisition.acquired_resource_paths.map((path) => normalizeRelativePath(path)));
      setLastAcquiredResourcePaths(acquiredPaths);

      if (!acquisition.source_intake_succeeded || acquisition.failed_terminal_count > 0) {
        setPhase("needs_review");
        setCleanupReview({
          safe: false,
          reason: acquisition.source_intake_succeeded ? "Acquisition reported terminal failures." : "Source Intake did not complete successfully.",
          eligibleCount: 0,
          verificationFailures: 0,
          unexpectedFiles: 0,
        });
        setMessage("Import completed, cleanup needs review.");
        await refreshStatus(selectedSourceId);
        return;
      }

      setPhase("cleanup_dry_run");
      await runIcloudStagingCleanupDryRun(selectedSourceId);
      const cleanupDryRun = await pollCleanupStatus(selectedSourceId);
      setCleanupResult(cleanupDryRun);
      const review = reviewCleanupSafety(cleanupDryRun, acquiredPaths, selectedSourceId);
      setCleanupReview(review);

      if (!review.safe) {
        setPhase("needs_review");
        setMessage("Import completed, cleanup needs review.");
        await refreshStatus(selectedSourceId);
        return;
      }

      if (cleanupDryRun.run_id == null) {
        setPhase("needs_review");
        setMessage("Import completed, cleanup needs review.");
        await refreshStatus(selectedSourceId);
        return;
      }

      setPhase("cleanup_execute");
      await executeIcloudStagingCleanup({
        source_id: selectedSourceId,
        dry_run_run_id: cleanupDryRun.run_id,
        explicit_confirmation: CLEANUP_CONFIRMATION_PHRASE,
      });
      const cleanupExecution = await pollCleanupStatus(selectedSourceId);
      setCleanupResult(cleanupExecution);
      setPhase(cleanupExecution.status === "completed" ? "completed" : "needs_review");
      setCleanupReview(
        cleanupExecution.status === "completed"
          ? null
          : {
              safe: false,
              reason: cleanupExecution.error_message ?? `Cleanup execution ended with status ${cleanupExecution.status}.`,
              eligibleCount: cleanupExecution.eligible_count,
              verificationFailures: cleanupExecution.verification_failed_count,
              unexpectedFiles: 0,
            },
      );
      setMessage(cleanupExecution.status === "completed" ? "Import and guarded cleanup completed." : "Import completed, cleanup needs review.");
      await refreshStatus(selectedSourceId);
    } catch (err) {
      setPhase("failed");
      setError(err instanceof Error ? err.message : "Run failed.");
    }
  }

  async function refreshCleanupReview(): Promise<void> {
    if (!selectedSourceId) {
      return;
    }
    setPhase("cleanup_dry_run");
    setError(null);
    try {
      await runIcloudStagingCleanupDryRun(selectedSourceId);
      const cleanupDryRun = await pollCleanupStatus(selectedSourceId);
      setCleanupResult(cleanupDryRun);
      const review = reviewCleanupSafety(cleanupDryRun, lastAcquiredResourcePaths, selectedSourceId);
      setCleanupReview(review);
      setPhase(review.safe ? "needs_review" : "needs_review");
      setMessage("Import completed, cleanup needs review.");
    } catch (err) {
      setPhase("failed");
      setError(err instanceof Error ? err.message : "Cleanup review refresh failed.");
    }
  }

  async function executeReviewedCleanup(): Promise<void> {
    if (!selectedSourceId || !cleanupResult?.run_id || !cleanupReview?.safe) {
      return;
    }
    setPhase("cleanup_execute");
    setError(null);
    try {
      await executeIcloudStagingCleanup({
        source_id: selectedSourceId,
        dry_run_run_id: cleanupResult.run_id,
        explicit_confirmation: CLEANUP_CONFIRMATION_PHRASE,
      });
      const cleanupExecution = await pollCleanupStatus(selectedSourceId);
      setCleanupResult(cleanupExecution);
      setPhase(cleanupExecution.status === "completed" ? "completed" : "needs_review");
      setCleanupReview(
        cleanupExecution.status === "completed"
          ? null
          : {
              safe: false,
              reason: cleanupExecution.error_message ?? `Cleanup execution ended with status ${cleanupExecution.status}.`,
              eligibleCount: cleanupExecution.eligible_count,
              verificationFailures: cleanupExecution.verification_failed_count,
              unexpectedFiles: 0,
            },
      );
      setMessage(cleanupExecution.status === "completed" ? "Guarded cleanup completed." : "Import completed, cleanup needs review.");
      await refreshStatus(selectedSourceId);
    } catch (err) {
      setPhase("failed");
      setError(err instanceof Error ? err.message : "Guarded cleanup failed.");
    }
  }

  async function handleLoadDeferred(): Promise<void> {
    if (!selectedSourceId) {
      return;
    }
    setIsLoadingDeferred(true);
    setError(null);
    try {
      const response = await getSourceProfileDeferredAssets(selectedSourceId, {
        state: "active_deferred",
        limit: 100,
      });
      setDeferredRows(response.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Deferred assets unavailable.");
    } finally {
      setIsLoadingDeferred(false);
    }
  }

  return (
    <section className={styles.panel}>
      <div className={styles.header}>
        <div>
          <h3 className={styles.title}>iCloud Source Workflow</h3>
          <p className={styles.subtitle}>Choose a source, refresh inventory, preview a bounded historical run, then run with guarded cleanup.</p>
        </div>
        <button type="button" className={styles.secondaryButton} onClick={() => void loadProfiles()} disabled={isLoadingProfiles || isBusy}>
          {isLoadingProfiles ? "Loading..." : "Refresh Sources"}
        </button>
      </div>

      <div className={styles.controls}>
        <label className={styles.field}>
          <span>Source Profile</span>
          <select
            value={selectedSourceId ?? ""}
            onChange={(event) => setSelectedSourceId(event.target.value ? Number(event.target.value) : null)}
            disabled={isBusy}
          >
            {icloudProfiles.length === 0 ? (
              <option value="">No active iCloud profiles</option>
            ) : (
              icloudProfiles.map((profile) => (
                <option key={profile.source_id} value={profile.source_id}>
                  {profile.source_label} (#{profile.source_id})
                </option>
              ))
            )}
          </select>
        </label>

        <div className={styles.segmented} aria-label="iCloud run mode">
          <button
            type="button"
            className={mode === "historical_backfill" ? styles.segmentActive : styles.segment}
            onClick={() => handleModeChange("historical_backfill")}
            disabled={isBusy}
          >
            Continue Historical Backfill
          </button>
          <button
            type="button"
            className={mode === "new_import" ? styles.segmentActive : styles.segment}
            onClick={() => handleModeChange("new_import")}
            disabled
          >
            Import New iCloud Photos (Coming Soon)
          </button>
        </div>

        <label className={styles.field}>
          <span>Limit</span>
          <input
            type="text"
            inputMode="numeric"
            value={limitValue}
            onChange={(event) => {
              setLimitValue(event.target.value);
              setPreview(null);
              setPreviewKey(null);
            }}
            disabled={isBusy || mode === "new_import"}
          />
        </label>
      </div>

      {selectedProfile && (
        <p className={styles.metaLine}>
          {selectedProfile.managed_staging_path ?? selectedProfile.source_root_path ?? "No source path recorded"}
        </p>
      )}

      <div className={styles.actionRow}>
        <button type="button" className={styles.secondaryButton} onClick={() => void handleInventoryScan()} disabled={!selectedSourceId || isBusy}>
          Refresh Inventory
        </button>
        <button type="button" className={styles.secondaryButton} onClick={() => void handlePreview()} disabled={!selectedSourceId || isBusy || mode === "new_import"}>
          Preview
        </button>
        <button type="button" className={styles.primaryButton} onClick={() => void handleRun()} disabled={!selectedSourceId || isBusy || mode === "new_import"}>
          {isBusy ? "Running..." : "Run"}
        </button>
      </div>

      {largeLimitWarning && <p className={styles.warning}>{largeLimitWarning}</p>}
      {message && <p className={styles.success}>{message}</p>}
      {error && <p className={styles.error}>{error}</p>}

      <div className={styles.metricsGrid}>
        <Metric label="Inventory Total" value={status?.inventory_total_count ?? 0} />
        <Metric label="Eligible Pending" value={status?.acquirable_pending_count ?? 0} />
        <Metric label="Backfill Completed" value={status?.backfill_completed_count ?? 0} />
        <Metric label="Deferred Current" value={status?.deferred_current_count ?? 0} />
        <Metric label="Adjusted Deferred" value={status?.deferred_adjusted_resource_count ?? 0} />
        <Metric label="Retryable Failed" value={status?.retryable_failed_count ?? 0} />
      </div>

      {status && (
        <p className={styles.metaLine}>
          Last scan: {toDisplayDate(status.last_inventory_scan_at)} | Candidates: {status.last_scan_candidate_count} | Created: {status.last_scan_created_count} | Updated: {status.last_scan_updated_count}
        </p>
      )}

      {preview && (
        <div className={styles.summaryBlock}>
          <h4>Preview</h4>
          <div className={styles.metricsGrid}>
            <Metric label="Selected Logical" value={preview.preview_selected_logical_count} />
            <Metric label="Selected Resources" value={preview.preview_selected_resource_count} />
            <Metric label="Known Skipped" value={preview.skipped_known_count} />
            <Metric label="Unsupported Skipped" value={preview.skipped_unsupported_count} />
            <Metric label="Ambiguous Skipped" value={preview.skipped_ambiguous_count} />
            <Metric label="Stop Reason" value={preview.stop_reason} />
          </div>
        </div>
      )}

      {acquireResult && (
        <div className={styles.summaryBlock}>
          <h4>Run Summary</h4>
          <div className={styles.metricsGrid}>
            <Metric label="Downloaded Logical" value={acquireResult.downloaded_logical_count} />
            <Metric label="Downloaded Resources" value={acquireResult.downloaded_resource_count} />
            <Metric label="Source Intake" value={acquireResult.source_intake_succeeded ? "Succeeded" : "Review"} />
            <Metric label="Completed" value={acquireResult.backfill_completed_count} />
            <Metric label="Retryable Failed" value={acquireResult.failed_retryable_count} />
            <Metric label="Stop Reason" value={acquireResult.stop_reason} />
          </div>
        </div>
      )}

      {cleanupResult && (
        <div className={styles.summaryBlock}>
          <h4>Cleanup</h4>
          <div className={styles.metricsGrid}>
            <Metric label="Status" value={cleanupResult.status} />
            <Metric label="Eligible" value={cleanupResult.eligible_count} />
            <Metric label="Deleted" value={cleanupResult.deleted_count} />
            <Metric label="Skipped" value={cleanupResult.skipped_count} />
            <Metric label="Protected" value={cleanupResult.protected_count} />
            <Metric label="Verification Failed" value={cleanupResult.verification_failed_count} />
          </div>
        </div>
      )}

      {phase === "needs_review" && cleanupReview && (
        <div className={styles.summaryBlock}>
          <h4>Cleanup Review</h4>
          <p className={cleanupReview.safe ? styles.success : styles.warning}>
            Reason: {cleanupReview.reason}
          </p>
          <div className={styles.metricsGrid}>
            <Metric label="Cleanup Dry-Run ID" value={cleanupResult?.dry_run ? cleanupResult.run_id ?? "-" : "-"} />
            <Metric label="Eligible Files" value={cleanupReview.eligibleCount} />
            <Metric label="Verification Failures" value={cleanupReview.verificationFailures} />
            <Metric label="Unexpected Files" value={cleanupReview.unexpectedFiles} />
          </div>
          <div className={styles.actionRow}>
            <button type="button" className={styles.secondaryButton} onClick={() => void refreshCleanupReview()} disabled={!selectedSourceId || isBusy}>
              Refresh Cleanup Review
            </button>
            <button
              type="button"
              className={styles.primaryButton}
              onClick={() => void executeReviewedCleanup()}
              disabled={!selectedSourceId || isBusy || !cleanupResult?.dry_run || !cleanupReview.safe}
            >
              Execute Guarded Cleanup
            </button>
          </div>
        </div>
      )}

      <details className={styles.details}>
        <summary>Skipped / Deferred Detail</summary>
        <div className={styles.actionRow}>
          <button type="button" className={styles.secondaryButton} onClick={() => void handleLoadDeferred()} disabled={!selectedSourceId || isLoadingDeferred}>
            {isLoadingDeferred ? "Loading..." : "Load Deferred Assets"}
          </button>
        </div>
        {deferredRows.length > 0 && (
          <div className={styles.tableWrap}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>Path</th>
                  <th>Category</th>
                  <th>Reason</th>
                  <th>Resources</th>
                  <th>Live</th>
                  <th>Seen</th>
                </tr>
              </thead>
              <tbody>
                {deferredRows.slice(0, 100).map((row) => (
                  <tr key={row.id}>
                    <td>{row.primary_relative_path ?? row.filename ?? "-"}</td>
                    <td>{row.deferred_category}</td>
                    <td>{row.deferred_reason_code}</td>
                    <td>{row.resource_count}</td>
                    <td>{row.is_live_photo ? "Yes" : "No"}</td>
                    <td>{row.observation_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </details>

      <p className={styles.metaLine}>Phase: {phase} | Candidate search cap: {CANDIDATE_SEARCH_CAP}</p>
    </section>
  );
}

function Metric({ label, value }: { label: string; value: string | number }): JSX.Element {
  return (
    <span className={styles.metric}>
      <strong>{label}</strong>
      <span>{value}</span>
    </span>
  );
}
